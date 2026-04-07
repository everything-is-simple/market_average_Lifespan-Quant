"""alpha.pas.pipeline — PAS 批量信号扫描管道。

入口函数 run_pas_batch()：
  1. 从 market_base.duckdb 读取候选股后复权日线
  2. 从 malf.duckdb 读取 malf_context_snapshot（获取 surface_label）
  3. 对每只股票运行 run_all_detectors()
  4. 对触发信号执行 cell_gate_check()（准入校验）
  5. 将 trace + signal 写入 research_lab.duckdb
  6. 写 pas_registry_run manifest

写权边界：只写 research_lab.duckdb，不写其他数据库。
"""
# 历史兼容说明：
# 本模块当前仍消费 monthly_state / surface_label / 16 格背景。
# 自 016 起，它们只代表旧三层主轴兼容层，不再代表 MALF 生命周期
# 主读数；后续应迁移到四格上下文与生命周期三轴排名合同。

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Sequence
from uuid import uuid4

import duckdb
import pandas as pd

from lq.alpha.pas.bootstrap import bootstrap_research_lab
from lq.alpha.pas.contracts import PasDetectTrace, PasSignal, PasBatchResult
from lq.alpha.pas.detectors import run_all_detectors
from lq.alpha.pas.validation import cell_gate_check
from lq.core.contracts import PasTriggerPattern


def _run_id() -> str:
    return f"pas-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


# 最少需要多少个交易日的历史数据才进入探测
_MIN_HISTORY_DAYS = 60

# BPB 拒绝准入，不写正式信号表
_REJECTED_PATTERNS = {PasTriggerPattern.BPB.value}


def run_pas_batch(
    signal_date: date,
    codes: Sequence[str],
    market_base_path: Path,
    malf_db_path: Path,
    research_lab_path: Path,
    patterns: list[str] | None = None,
    lookback_days: int = 240,
    verbose: bool = False,
) -> PasBatchResult:
    """批量扫描 PAS 信号并写入 research_lab.duckdb。

    参数：
        signal_date        — 信号日（T 日，用于读取 malf 背景和探测器判断）
        codes              — 候选股代码列表
        market_base_path   — market_base.duckdb 路径（只读）
        malf_db_path       — malf.duckdb 路径（只读）
        research_lab_path  — research_lab.duckdb 路径（读写）
        patterns           — 指定 trigger 列表，None = 全部五个
        lookback_days      — 向前读取多少个交易日的日线（用于 detector）
        verbose            — 是否打印进度

    返回：
        PasBatchResult 批量结果摘要
    """
    bootstrap_research_lab(research_lab_path)

    run_id = _run_id()
    active_patterns = patterns or [p.value for p in PasTriggerPattern]

    all_traces: list[PasDetectTrace] = []
    all_signals: list[PasSignal] = []
    pattern_counts: dict[str, int] = {p: 0 for p in active_patterns}

    # 读取所有候选股的 surface_label（来自 malf）
    malf_labels: dict[str, str] = {}
    try:
        with duckdb.connect(str(malf_db_path), read_only=True) as malf_conn:
            rows = malf_conn.execute(
                "SELECT code, surface_label FROM malf_context_snapshot "
                "WHERE signal_date = ? AND code = ANY(?)",
                [signal_date, list(codes)],
            ).fetchall()
            malf_labels = {r[0]: r[1] for r in rows}
    except Exception:
        pass  # malf 数据不可用时仍运行探测，signal 中 surface_label 置为 "UNKNOWN"

    with duckdb.connect(str(market_base_path), read_only=True) as base_conn:
        for i, code in enumerate(codes):
            if verbose and i % 100 == 0:
                print(f"  扫描 {i}/{len(codes)} {code}...")

            try:
                df = _load_daily_for_detector(base_conn, code, signal_date, lookback_days)
                if df is None or len(df) < _MIN_HISTORY_DAYS:
                    continue

                traces = run_all_detectors(code, signal_date, df, patterns=active_patterns)
                all_traces.extend(traces)

                surface_label = malf_labels.get(code, "UNKNOWN")

                for trace in traces:
                    if not trace.triggered:
                        continue
                    if trace.pattern in _REJECTED_PATTERNS:
                        continue   # BPB 不写正式信号表

                    # 准入校验（16 格 cell_gate_check）
                    if surface_label != "UNKNOWN":
                        gate = cell_gate_check(trace.pattern, surface_label)
                        if gate == "rejected":
                            continue   # 拒绝格不写信号

                    # 构建正式信号
                    sig = _build_signal(trace, code, signal_date, surface_label, df)
                    all_signals.append(sig)
                    pattern_counts[trace.pattern] = pattern_counts.get(trace.pattern, 0) + 1

            except Exception as exc:
                if verbose:
                    print(f"    [ERROR] {code}: {exc}")
                continue

    batch_result = PasBatchResult(
        run_id=run_id,
        asof_date=signal_date,
        codes_scanned=len(codes),
        triggered_count=len(all_signals),
        pattern_counts=pattern_counts,
        signals=tuple(all_signals),
    )

    # 写入 research_lab.duckdb
    _write_to_research_lab(
        research_lab_path, run_id, signal_date,
        active_patterns, len(codes), all_traces, all_signals,
    )

    if verbose:
        print(f"  完成：扫描 {len(codes)} 只，触发 {len(all_signals)} 个信号，run_id={run_id}")

    return batch_result


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _load_daily_for_detector(
    base_conn: duckdb.DuckDBPyConnection,
    code: str,
    signal_date: date,
    lookback_days: int,
) -> pd.DataFrame | None:
    """从 market_base 读取用于 detector 的日线数据。"""
    df: pd.DataFrame = base_conn.execute(
        "SELECT trade_date, open, high, low, close, volume, amount "
        "FROM stock_daily_adjusted "
        "WHERE code = ? AND adjust_method = 'backward' AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT ?",
        [code, signal_date, lookback_days],
    ).df()
    if df.empty:
        return None
    return df.sort_values("trade_date").reset_index(drop=True)


def _build_signal(
    trace: PasDetectTrace,
    code: str,
    signal_date: date,
    surface_label: str,
    df: pd.DataFrame,
) -> PasSignal:
    """从 trace 构建 PasSignal（正式信号合同）。"""
    # 取信号日当日收盘价作为 entry_ref_price，最低价作为 signal_low
    last_row = df[df["trade_date"] == signal_date]
    if not last_row.empty:
        signal_low      = float(last_row["low"].iloc[0])
        entry_ref_price = float(last_row["close"].iloc[0])
    else:
        # 无当日数据时取最后一行
        signal_low      = float(df["low"].iloc[-1])
        entry_ref_price = float(df["close"].iloc[-1])

    return PasSignal(
        signal_id=trace.signal_id,
        code=code,
        signal_date=signal_date,
        pattern=trace.pattern,
        surface_label=surface_label,
        strength=trace.strength or 0.0,
        signal_low=round(signal_low, 4),
        entry_ref_price=round(entry_ref_price, 4),
        pb_sequence_number=trace.pb_sequence_number,
    )


def _write_to_research_lab(
    research_lab_path: Path,
    run_id: str,
    signal_date: date,
    patterns: list[str],
    candidate_count: int,
    traces: list[PasDetectTrace],
    signals: list[PasSignal],
) -> None:
    """将 traces 和 signals 写入 research_lab.duckdb（幂等：先删后插）。"""
    with duckdb.connect(str(research_lab_path)) as conn:
        # 写 pas_registry_run（幂等）
        conn.execute(
            "INSERT OR REPLACE INTO pas_registry_run "
            "(run_id, trigger_pattern, window_start, window_end, "
            " candidate_count, signal_count, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                ",".join(patterns),
                signal_date,
                signal_date,
                candidate_count,
                len(signals),
                "completed",
            ],
        )

        # 删除同日期的旧 trace（幂等）
        conn.execute(
            "DELETE FROM pas_selected_trace WHERE signal_date = ?",
            [signal_date],
        )
        # 插入 traces
        if traces:
            trace_rows = [
                [
                    trace.signal_id + f"-{run_id[:8]}",  # 唯一 trace_id
                    run_id,
                    trace.signal_id,
                    trace.signal_id.split("_")[0] if "_" in trace.signal_id else "",
                    signal_date,
                    trace.pattern,
                    trace.triggered,
                    trace.strength,
                    trace.skip_reason,
                    trace.detect_reason,
                    trace.history_days,
                    trace.min_history_days,
                    trace.pb_sequence_number,
                ]
                for trace in traces
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO pas_selected_trace "
                "(trace_id, run_id, signal_id, code, signal_date, pattern, triggered, "
                " strength, skip_reason, detect_reason, history_days, "
                " min_history_days, pb_sequence_number) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                trace_rows,
            )

        # 删除同日期的旧正式信号（幂等）
        conn.execute(
            "DELETE FROM pas_formal_signal WHERE signal_date = ?",
            [signal_date],
        )
        # 插入正式信号
        if signals:
            signal_rows = [
                [
                    sig.signal_id,
                    run_id,
                    sig.code,
                    sig.signal_date,
                    sig.pattern,
                    sig.surface_label,
                    sig.strength,
                    sig.signal_low,
                    sig.entry_ref_price,
                    sig.pb_sequence_number,
                    None,  # monthly_state（可后续从 malf 补充）
                    None,  # weekly_flow
                ]
                for sig in signals
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO pas_formal_signal "
                "(signal_id, run_id, code, signal_date, pattern, surface_label, "
                " strength, signal_low, entry_ref_price, pb_sequence_number, "
                " monthly_state, weekly_flow) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                signal_rows,
            )
