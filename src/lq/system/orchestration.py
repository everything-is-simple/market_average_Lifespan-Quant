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
from lq.malf.contracts import MalfContext, build_malf_context_4
from lq.malf.pipeline import build_malf_context_for_stock
from lq.structure.detector import build_structure_snapshot
from lq.filter.adverse import check_adverse_conditions
from lq.alpha.pas.detectors import run_all_detectors
from lq.alpha.pas.contracts import PasSignal
from lq.malf.contracts import build_signal_id
from lq.position.sizing import compute_position_plan, build_exit_plan
from lq.structure.contracts import StructureSnapshot


def _build_structure_summary(snap: StructureSnapshot | None) -> dict[str, Any]:
    """从 StructureSnapshot 提取轻量完整谡，嵌入解释链以支持 replay。"""
    if snap is None:
        return {
            "has_clear_structure": False,
            "nearest_support_price": None,
            "nearest_support_strength": None,
            "nearest_resistance_price": None,
            "nearest_resistance_strength": None,
            "recent_breakout_type": None,
            "recent_breakout_recovered": None,
            "available_space_pct": None,
        }
    return {
        "has_clear_structure": snap.has_clear_structure,
        "nearest_support_price": (
            snap.nearest_support.price if snap.nearest_support else None
        ),
        "nearest_support_strength": (
            snap.nearest_support.strength if snap.nearest_support else None
        ),
        "nearest_resistance_price": (
            snap.nearest_resistance.price if snap.nearest_resistance else None
        ),
        "nearest_resistance_strength": (
            snap.nearest_resistance.strength if snap.nearest_resistance else None
        ),
        "recent_breakout_type": (
            snap.recent_breakout.breakout_type if snap.recent_breakout else None
        ),
        "recent_breakout_recovered": (
            snap.recent_breakout.recovered if snap.recent_breakout else None
        ),
        "available_space_pct": snap.available_space_pct,
    }


@dataclass(frozen=True)
class StockScanTrace:
    """单只股票单次扫描的完整解释链记录（四件套：MALF + 结构 + 过滤 + PAS）。

    用途：回溯某只股票某日为何被过滤、为何触发或未触发信号，
          可通过 run_id + code + signal_date 三元组联查。
    """

    run_id: str
    code: str
    signal_date: date
    # MALF 摘要
    long_background_2: str
    intermediate_role_2: str
    monthly_state: str
    malf_context_4: str
    # 不利条件过滤结果
    tradeable: bool
    adverse_conditions: tuple[str, ...]
    adverse_notes: str
    # 结构位摘要（封装轻量 8 字段，支持 replay）
    structure_summary: dict[str, Any] = field(default_factory=dict)
    # PAS trace 列表（仅 tradeable=True 时填充；否则为空 tuple）
    pas_traces: tuple[dict, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "long_background_2": self.long_background_2,
            "intermediate_role_2": self.intermediate_role_2,
            "monthly_state": self.monthly_state,
            "malf_context_4": self.malf_context_4,
            "tradeable": self.tradeable,
            "adverse_conditions": list(self.adverse_conditions),
            "adverse_notes": self.adverse_notes,
            "structure_summary": self.structure_summary,
            "pas_traces": list(self.pas_traces),
        }


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
    stock_traces: list[dict[str, Any]] = field(default_factory=list)  # 解释链（三件套）

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
            "stock_traces": self.stock_traces,
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
    stock_traces: list[dict[str, Any]] = []
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
                    "SELECT month_start_date AS month_start, trade_date, "
                    "       open, high, low, close, volume "
                    "FROM stock_monthly_adjusted "
                    "WHERE code = ? AND adjust_method = 'backward' "
                    "ORDER BY month_start_date",
                    [code],
                ).df()

                weekly_df: pd.DataFrame = conn.execute(
                    "SELECT week_start_date AS week_start, trade_date, "
                    "       open, high, low, close, volume "
                    "FROM stock_weekly_adjusted "
                    "WHERE code = ? AND adjust_method = 'backward' "
                    "ORDER BY week_start_date",
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
                # 记录解释链（过滤掉的股票：无 PAS trace，但保留结构摘要）
                stock_traces.append(StockScanTrace(
                    run_id=run_id,
                    code=code,
                    signal_date=signal_date,
                    long_background_2=malf_ctx.long_background_2,
                    intermediate_role_2=malf_ctx.intermediate_role_2,
                    monthly_state=malf_ctx.monthly_state,
                    malf_context_4=malf_ctx.malf_context_4,
                    tradeable=False,
                    adverse_conditions=adverse_result.active_conditions,
                    adverse_notes=adverse_result.notes,
                    structure_summary=_build_structure_summary(struct_snap),
                ).as_dict())
                continue

            # PAS 探测（A7 五触发）— 传入 struct_snap 实现结构位上游化
            traces = run_all_detectors(
                code, signal_date, daily_df,
                patterns=enabled_patterns,
                struct_snap=struct_snap,
            )

            # 记录解释链（通过过滤的股票：完整四件套）
            stock_traces.append(StockScanTrace(
                run_id=run_id,
                code=code,
                signal_date=signal_date,
                long_background_2=malf_ctx.long_background_2,
                intermediate_role_2=malf_ctx.intermediate_role_2,
                monthly_state=malf_ctx.monthly_state,
                malf_context_4=malf_ctx.malf_context_4,
                tradeable=True,
                adverse_conditions=adverse_result.active_conditions,
                adverse_notes=adverse_result.notes,
                structure_summary=_build_structure_summary(struct_snap),
                pas_traces=tuple(t.as_dict() for t in traces),
            ).as_dict())

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
                    long_background_2=malf_ctx.long_background_2,
                    intermediate_role_2=malf_ctx.intermediate_role_2,
                    malf_context_4=malf_ctx.malf_context_4,
                    amplitude_rank_low=malf_ctx.amplitude_rank_low,
                    amplitude_rank_high=malf_ctx.amplitude_rank_high,
                    amplitude_rank_total=malf_ctx.amplitude_rank_total,
                    duration_rank_low=malf_ctx.duration_rank_low,
                    duration_rank_high=malf_ctx.duration_rank_high,
                    duration_rank_total=malf_ctx.duration_rank_total,
                    new_price_rank_low=malf_ctx.new_price_rank_low,
                    new_price_rank_high=malf_ctx.new_price_rank_high,
                    new_price_rank_total=malf_ctx.new_price_rank_total,
                    lifecycle_rank_low=malf_ctx.lifecycle_rank_low,
                    lifecycle_rank_high=malf_ctx.lifecycle_rank_high,
                    lifecycle_rank_total=malf_ctx.lifecycle_rank_total,
                    amplitude_quartile=malf_ctx.amplitude_quartile,
                    duration_quartile=malf_ctx.duration_quartile,
                    new_price_quartile=malf_ctx.new_price_quartile,
                    lifecycle_quartile=malf_ctx.lifecycle_quartile,
                    monthly_state=malf_ctx.monthly_state,
                    weekly_flow=malf_ctx.weekly_flow,
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
        stock_traces=stock_traces,
    )
