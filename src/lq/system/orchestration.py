"""系统主线编排 — 每日信号扫描流水线。

主线流：
    data（已更新） → malf → structure(filter) → alpha/pas → position → output

执行语义：signal_date=T，execute_date=T+1，成交价=T+1 开盘价。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import duckdb
import pandas as pd

from lq.core.contracts import PasTriggerPattern, PAS_TRIGGER_STATUS, PasTriggerStatus
from lq.core.paths import WorkspaceRoots, default_settings
from lq.malf.contracts import MalfContext, build_surface_label
from lq.malf.pipeline import build_malf_context_for_stock
from lq.structure.detector import build_structure_snapshot
from lq.filter.adverse import check_adverse_conditions
from lq.alpha.pas.detectors import run_all_detectors
from lq.alpha.pas.contracts import PasSignal
from lq.malf.contracts import build_signal_id
from lq.position.sizing import compute_position_plan, build_exit_plan


@dataclass(frozen=True)
class SystemRunSummary:
    """系统单日扫描摘要。"""

    run_id: str
    signal_date: date
    codes_scanned: int
    codes_filtered_out: int     # 被不利条件过滤掉的股票数
    signals_found: int
    pattern_counts: dict[str, int]
    top_signals: list[dict[str, Any]]   # 按 strength 排序的前 N 个信号
    scan_errors: list[dict[str, Any]] = field(default_factory=list)  # 扫描失败记录

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "signal_date": self.signal_date.isoformat(),
            "codes_scanned": self.codes_scanned,
            "codes_filtered_out": self.codes_filtered_out,
            "signals_found": self.signals_found,
            "pattern_counts": self.pattern_counts,
            "top_signals": self.top_signals,
            "scan_errors": self.scan_errors,
        }


def run_daily_signal_scan(
    signal_date: date,
    codes: list[str],
    workspace: WorkspaceRoots | None = None,
    enabled_patterns: list[str] | None = None,
    top_n: int = 20,
) -> SystemRunSummary:
    """执行单日全市场信号扫描。

    参数：
        signal_date      — T 日（信号产生日）
        codes            — 待扫描的股票代码列表
        workspace        — 工作区路径（默认从环境变量解析）
        enabled_patterns — 启用的 trigger 列表（默认：主线可用 + 条件格）
        top_n            — 输出前 N 个最强信号

    返回：
        SystemRunSummary 系统运行摘要
    """
    ws = workspace or default_settings()
    db_paths = ws.databases

    # 默认启用主线可用和条件格 trigger（拒绝 BPB）
    if enabled_patterns is None:
        enabled_patterns = [
            p.value
            for p, status in PAS_TRIGGER_STATUS.items()
            if status in (PasTriggerStatus.MAINLINE, PasTriggerStatus.CONDITIONAL)
        ]

    run_id = f"scan-{signal_date.isoformat()}-{uuid4().hex[:8]}"
    signals: list[PasSignal] = []
    filtered_out = 0
    scan_errors: list[dict[str, Any]] = []
    pattern_counts: dict[str, int] = {p: 0 for p in enabled_patterns}

    for code in codes:
        try:
            # 读取日线数据
            with duckdb.connect(str(db_paths.market_base), read_only=True) as conn:
                # DESC 拿最近 120 根，再按日期升序还原（保证最后一根是 signal_date）
                daily_df: pd.DataFrame = conn.execute(
                    """SELECT date, adj_open, adj_high, adj_low, adj_close,
                              volume, volume_ma20, ma10, ma20
                       FROM adj_daily_bar
                       WHERE code = ? AND date <= ?
                       ORDER BY date DESC
                       LIMIT 120""",
                    [code, signal_date],
                ).df()
                monthly_df: pd.DataFrame = conn.execute(
                    "SELECT * FROM monthly_bar WHERE code = ? ORDER BY month_start",
                    [code],
                ).df()

                weekly_df: pd.DataFrame = conn.execute(
                    "SELECT * FROM weekly_bar WHERE code = ? ORDER BY week_start",
                    [code],
                ).df()

            # 先检查空，再排序（避免无 date 列时 KeyError）
            if daily_df.empty:
                continue
            daily_df = daily_df.sort_values("date").reset_index(drop=True)

            # 构建 MALF 上下文
            malf_ctx = build_malf_context_for_stock(code, signal_date, monthly_df, weekly_df)

            # 构建结构位快照
            struct_snap = build_structure_snapshot(code, signal_date, daily_df)

            # 不利条件过滤（A4）
            adverse_result = check_adverse_conditions(
                code=code,
                signal_date=signal_date,
                daily_bars=daily_df,
                malf_ctx=malf_ctx,
                nearest_support_price=(
                    struct_snap.nearest_support.price if struct_snap.nearest_support else None
                ),
                nearest_resistance_price=(
                    struct_snap.nearest_resistance.price if struct_snap.nearest_resistance else None
                ),
            )

            if not adverse_result.tradeable:
                filtered_out += 1
                continue

            # PAS 探测（A7 五触发）
            traces = run_all_detectors(code, signal_date, daily_df, patterns=enabled_patterns)

            for trace in traces:
                if not trace.triggered or trace.strength is None:
                    continue

                # 构建正式信号对象
                current_close = float(daily_df["adj_close"].iloc[-1])
                sig = PasSignal(
                    signal_id=trace.signal_id,
                    code=code,
                    signal_date=signal_date,
                    pattern=trace.pattern,
                    surface_label=malf_ctx.surface_label,
                    strength=trace.strength,
                    signal_low=float(daily_df["adj_low"].iloc[-1]),
                    entry_ref_price=current_close,
                    pb_sequence_number=trace.pb_sequence_number,
                )
                signals.append(sig)
                pattern_counts[trace.pattern] = pattern_counts.get(trace.pattern, 0) + 1

        except Exception as exc:
            # 记录失败，不静默吞异常；汇总结果保留错误轨迹
            scan_errors.append({
                "code": code,
                "stage": "scan",
                "error": str(exc),
            })
            continue

    # 按强度排序
    signals.sort(key=lambda s: s.strength, reverse=True)
    top_signals = [s.as_dict() for s in signals[:top_n]]

    return SystemRunSummary(
        run_id=run_id,
        signal_date=signal_date,
        codes_scanned=len(codes),
        codes_filtered_out=filtered_out,
        signals_found=len(signals),
        pattern_counts=pattern_counts,
        top_signals=top_signals,
        scan_errors=scan_errors,
    )
