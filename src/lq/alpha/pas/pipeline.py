"""alpha.pas.pipeline — PAS 批量信号扫描管道。

入口函数 run_pas_batch()：
  1. 从 market_base.duckdb 读取候选股后复权日线
  2. 从 malf.duckdb 读取 execution_context_snapshot（获取正式生命周期字段）
  3. 对每只股票运行 run_all_detectors()
  4. 对触发信号执行 cell_gate_check()（准入校验）
  5. 将 trace + signal 写入 research_lab.duckdb
  6. 写 pas_registry_run manifest

写权边界：只写 research_lab.duckdb，不写其他数据库。
"""

from __future__ import annotations

import logging
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
from lq.core.paths import WorkspaceRoots, default_settings
from lq.core.resumable import prepare_resumable_checkpoint, save_resumable_checkpoint

logger = logging.getLogger(__name__)


def _run_id() -> str:
    return f"pas-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


# 最少需要多少个交易日的历史数据才进入探测
_MIN_HISTORY_DAYS = 60

# BPB 拒绝准入，不写正式信号表
_REJECTED_PATTERNS = {PasTriggerPattern.BPB.value}


def _empty_malf_snapshot() -> dict[str, object]:
    """返回缺省 MALF 快照占位。"""
    return {
        "long_background_2": None,
        "intermediate_role_2": None,
        "malf_context_4": "UNKNOWN",
        "amplitude_rank_low": None,
        "amplitude_rank_high": None,
        "amplitude_rank_total": None,
        "duration_rank_low": None,
        "duration_rank_high": None,
        "duration_rank_total": None,
        "new_price_rank_low": None,
        "new_price_rank_high": None,
        "new_price_rank_total": None,
        "lifecycle_rank_low": None,
        "lifecycle_rank_high": None,
        "lifecycle_rank_total": None,
        "amplitude_quartile": None,
        "duration_quartile": None,
        "new_price_quartile": None,
        "lifecycle_quartile": None,
        "monthly_state": "",
        "weekly_flow": "",
    }


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

    # 读取所有候选股的 MALF 快照（正式字段来自 execution_context_snapshot；gate 兼容字段来自 malf_context_snapshot）
    malf_snapshots: dict[str, dict[str, object]] = {}
    try:
        with duckdb.connect(str(malf_db_path), read_only=True) as malf_conn:
            rows = malf_conn.execute(
                "SELECT e.entity_code, e.long_background_2, e.intermediate_role_2, e.malf_context_4, "
                "       e.amplitude_rank_low, e.amplitude_rank_high, e.amplitude_rank_total, "
                "       e.duration_rank_low, e.duration_rank_high, e.duration_rank_total, "
                "       e.new_price_rank_low, e.new_price_rank_high, e.new_price_rank_total, "
                "       e.lifecycle_rank_low, e.lifecycle_rank_high, e.lifecycle_rank_total, "
                "       e.amplitude_quartile, e.duration_quartile, e.new_price_quartile, e.lifecycle_quartile, "
                "       COALESCE(m.monthly_state, ''), COALESCE(m.weekly_flow, '') "
                "FROM execution_context_snapshot e "
                "LEFT JOIN malf_context_snapshot m "
                "  ON m.code = e.entity_code AND m.signal_date = e.calc_date "
                "WHERE e.entity_scope = 'stock' AND e.calc_date = ? AND e.entity_code = ANY(?)",
                [signal_date, list(codes)],
            ).fetchall()
            malf_snapshots = {
                r[0]: {
                    "long_background_2": r[1],
                    "intermediate_role_2": r[2],
                    "malf_context_4": r[3] or "UNKNOWN",
                    "amplitude_rank_low": r[4],
                    "amplitude_rank_high": r[5],
                    "amplitude_rank_total": r[6],
                    "duration_rank_low": r[7],
                    "duration_rank_high": r[8],
                    "duration_rank_total": r[9],
                    "new_price_rank_low": r[10],
                    "new_price_rank_high": r[11],
                    "new_price_rank_total": r[12],
                    "lifecycle_rank_low": r[13],
                    "lifecycle_rank_high": r[14],
                    "lifecycle_rank_total": r[15],
                    "amplitude_quartile": r[16],
                    "duration_quartile": r[17],
                    "new_price_quartile": r[18],
                    "lifecycle_quartile": r[19],
                    "monthly_state": r[20] or "",
                    "weekly_flow": r[21] or "",
                }
                for r in rows
            }
    except Exception:
        pass  # malf 数据不可用时仍运行探测，signal 中正式字段回退到占位

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

                malf_snapshot = malf_snapshots.get(code, _empty_malf_snapshot())
                monthly_state = malf_snapshot["monthly_state"]
                weekly_flow = malf_snapshot["weekly_flow"]

                for trace in traces:
                    if not trace.triggered:
                        continue
                    if trace.pattern in _REJECTED_PATTERNS:
                        continue   # BPB 不写正式信号表

                    # 准入校验（cell gate）
                    if monthly_state and weekly_flow:
                        gate = cell_gate_check(trace.pattern, monthly_state, weekly_flow)
                        if not gate:
                            continue   # 拒绝格不写信号

                    # 构建正式信号
                    sig = _build_signal(trace, code, signal_date, malf_snapshot, df)
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
        active_patterns, len(codes), all_traces, all_signals, malf_snapshots,
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
    malf_snapshot: dict[str, object],
    df: pd.DataFrame,
) -> PasSignal:
    """从 trace 构建 PasSignal（正式信号合同）。"""
    last_row = df[df["trade_date"] == signal_date]
    if not last_row.empty:
        signal_low      = float(last_row["low"].iloc[0])
        entry_ref_price = float(last_row["close"].iloc[0])
    else:
        signal_low      = float(df["low"].iloc[-1])
        entry_ref_price = float(df["close"].iloc[-1])

    return PasSignal(
        signal_id=trace.signal_id,
        code=code,
        signal_date=signal_date,
        pattern=trace.pattern,
        long_background_2=malf_snapshot.get("long_background_2"),
        intermediate_role_2=malf_snapshot.get("intermediate_role_2"),
        malf_context_4=str(malf_snapshot.get("malf_context_4") or "UNKNOWN"),
        amplitude_rank_low=malf_snapshot.get("amplitude_rank_low"),
        amplitude_rank_high=malf_snapshot.get("amplitude_rank_high"),
        amplitude_rank_total=malf_snapshot.get("amplitude_rank_total"),
        duration_rank_low=malf_snapshot.get("duration_rank_low"),
        duration_rank_high=malf_snapshot.get("duration_rank_high"),
        duration_rank_total=malf_snapshot.get("duration_rank_total"),
        new_price_rank_low=malf_snapshot.get("new_price_rank_low"),
        new_price_rank_high=malf_snapshot.get("new_price_rank_high"),
        new_price_rank_total=malf_snapshot.get("new_price_rank_total"),
        lifecycle_rank_low=malf_snapshot.get("lifecycle_rank_low"),
        lifecycle_rank_high=malf_snapshot.get("lifecycle_rank_high"),
        lifecycle_rank_total=malf_snapshot.get("lifecycle_rank_total"),
        amplitude_quartile=malf_snapshot.get("amplitude_quartile"),
        duration_quartile=malf_snapshot.get("duration_quartile"),
        new_price_quartile=malf_snapshot.get("new_price_quartile"),
        lifecycle_quartile=malf_snapshot.get("lifecycle_quartile"),
        monthly_state=str(malf_snapshot.get("monthly_state") or "") or None,
        weekly_flow=str(malf_snapshot.get("weekly_flow") or "") or None,
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
    malf_snapshots: dict[str, dict[str, object]],
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
                    sig.long_background_2,
                    sig.intermediate_role_2,
                    sig.malf_context_4,
                    sig.amplitude_rank_low,
                    sig.amplitude_rank_high,
                    sig.amplitude_rank_total,
                    sig.duration_rank_low,
                    sig.duration_rank_high,
                    sig.duration_rank_total,
                    sig.new_price_rank_low,
                    sig.new_price_rank_high,
                    sig.new_price_rank_total,
                    sig.lifecycle_rank_low,
                    sig.lifecycle_rank_high,
                    sig.lifecycle_rank_total,
                    sig.amplitude_quartile,
                    sig.duration_quartile,
                    sig.new_price_quartile,
                    sig.lifecycle_quartile,
                    sig.strength,
                    sig.signal_low,
                    sig.entry_ref_price,
                    sig.pb_sequence_number,
                    sig.monthly_state,
                    sig.weekly_flow,
                ]
                for sig in signals
            ]
            conn.executemany(
                "INSERT OR REPLACE INTO pas_formal_signal "
                "(signal_id, run_id, code, signal_date, pattern, long_background_2, intermediate_role_2, malf_context_4, "
                " amplitude_rank_low, amplitude_rank_high, amplitude_rank_total, "
                " duration_rank_low, duration_rank_high, duration_rank_total, "
                " new_price_rank_low, new_price_rank_high, new_price_rank_total, "
                " lifecycle_rank_low, lifecycle_rank_high, lifecycle_rank_total, "
                " amplitude_quartile, duration_quartile, new_price_quartile, lifecycle_quartile, "
                " strength, signal_low, entry_ref_price, pb_sequence_number, "
                " monthly_state, weekly_flow) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                signal_rows,
            )


# ---------------------------------------------------------------------------
# 多日期批量构建（断点续传封装）
# ---------------------------------------------------------------------------

@dataclass
class PasBuildResult:
    """PAS 多日期批量构建结果摘要。"""

    run_id: str = field(
        default_factory=lambda: f"pas-build-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    )
    dates_total: int = 0
    dates_completed: int = 0
    dates_skipped: int = 0
    total_signals: int = 0
    total_scanned: int = 0
    errors: int = 0
    status: str = "completed"


def list_stock_codes(market_base_path: Path) -> list[str]:
    """从 market_base 获取所有有日线数据的股票代码。"""
    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT code FROM stock_daily_adjusted ORDER BY code"
        ).fetchall()
    return [r[0] for r in rows]


def run_pas_build(
    *,
    market_base_path: Path,
    malf_db_path: Path,
    research_lab_path: Path,
    signal_dates: Sequence[date],
    codes: Sequence[str] | None = None,
    patterns: list[str] | None = None,
    lookback_days: int = 240,
    resume: bool = False,
    reset_checkpoint: bool = False,
    settings: WorkspaceRoots | None = None,
    verbose: bool = True,
) -> PasBuildResult:
    """PAS 多日期批量构建，支持断点续传。

    对每个 signal_date 调用 run_pas_batch()，逐日推进并保存 checkpoint。

    参数：
        market_base_path  — market_base.duckdb（只读）
        malf_db_path      — malf.duckdb（只读）
        research_lab_path — research_lab.duckdb（读写）
        signal_dates      — 待构建日期列表
        codes             — 股票代码列表（None = 全市场）
        patterns          — 指定 trigger 列表，None = 全部五个
        lookback_days     — 向前读取多少交易日日线
        resume            — 从 checkpoint 续跑
        reset_checkpoint  — 清空旧 checkpoint 重跑
        settings          — WorkspaceRoots（用于 checkpoint 路径）
        verbose           — 打印进度
    """
    if not signal_dates:
        return PasBuildResult(status="empty")

    bootstrap_research_lab(research_lab_path)

    # 解析股票代码
    if codes is None:
        codes = list_stock_codes(market_base_path)
        if verbose:
            print(f"自动获取全市场股票：{len(codes)} 只")
    all_codes = list(codes)

    result = PasBuildResult(dates_total=len(signal_dates))

    # 准备 checkpoint
    if settings is None:
        settings = default_settings()
    fingerprint = {
        "research_lab": str(research_lab_path),
        "dates_range": f"{signal_dates[0]}..{signal_dates[-1]}",
        "codes_count": len(all_codes),
        "patterns": patterns or "all",
    }
    store, state = prepare_resumable_checkpoint(
        checkpoint_path=None,
        settings_root=settings,
        domain="alpha",
        runner_name="build_pas_signals",
        fingerprint=fingerprint,
        resume=resume,
        reset_checkpoint=reset_checkpoint,
    )

    # 恢复已完成日期
    completed_dates: set[str] = set()
    if state is not None:
        completed_dates = set(state.get("completed_dates", []))
        if verbose:
            print(f"从 checkpoint 恢复：已完成 {len(completed_dates)} 个日期")

    # 标记运行中
    save_resumable_checkpoint(store, fingerprint=fingerprint, payload={
        "status": "running",
        "completed_dates": sorted(completed_dates),
        "run_id": result.run_id,
    })

    # 逐日处理
    for idx, sig_date in enumerate(signal_dates):
        date_key = sig_date.isoformat()

        if date_key in completed_dates:
            result.dates_skipped += 1
            continue

        if verbose:
            print(
                f"  [{idx + 1}/{len(signal_dates)}] {date_key}",
                end="", flush=True,
            )

        try:
            batch_result = run_pas_batch(
                signal_date=sig_date,
                codes=all_codes,
                market_base_path=market_base_path,
                malf_db_path=malf_db_path,
                research_lab_path=research_lab_path,
                patterns=patterns,
                lookback_days=lookback_days,
                verbose=False,
            )
            result.total_signals += batch_result.triggered_count
            result.total_scanned += batch_result.codes_scanned
            result.dates_completed += 1
            completed_dates.add(date_key)

            if verbose:
                print(f" → 扫描 {batch_result.codes_scanned}，触发 {batch_result.triggered_count}")

        except Exception as exc:
            result.errors += 1
            logger.warning("PAS 构建失败 %s: %s", date_key, exc)
            if verbose:
                print(f" → 失败: {exc}")

        # 每日保存 checkpoint
        save_resumable_checkpoint(store, fingerprint=fingerprint, payload={
            "status": "running",
            "completed_dates": sorted(completed_dates),
            "run_id": result.run_id,
            "last_date": date_key,
        })

    # 完成状态
    if result.errors > 0 and result.dates_completed == 0:
        result.status = "failed"
    elif result.errors > 0:
        result.status = "partial"

    save_resumable_checkpoint(store, fingerprint=fingerprint, payload={
        "status": "done",
        "completed_dates": sorted(completed_dates),
        "run_id": result.run_id,
    })

    if verbose:
        print(
            f"\n完成：{result.dates_completed} 日完成 / "
            f"{result.dates_skipped} 日跳过 / {result.dates_total} 日总计"
        )
        print(f"扫描 {result.total_scanned}，触发 {result.total_signals} 信号，失败 {result.errors}")

    return result
