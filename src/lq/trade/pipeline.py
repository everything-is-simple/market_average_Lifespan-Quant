"""trade.pipeline — 交易记录持久化与回测 pipeline。

核心原则（七库全持久化纪律）：
    历史一旦发生就是永恒的瞬间——绝不重算。
    磁盘空间换内存，小批量断点续传。

trade_runtime.duckdb 存储：
    1. trade_record          — 每笔已完成交易的详细记录
    2. trade_run_summary     — 每次回测 run 的汇总统计
    3. trade_build_manifest  — 构建元数据

用法：
    1. 全量回测：run_trade_build(signal_dates=[...], ...) — 首次历史回测
    2. 日增量：run_trade_build(signal_dates=[today], ...) — 每日收盘后追加
    3. 断点续传：run_trade_build(..., resume=True) — 中断后从上次继续

写权边界：只写 trade_runtime.duckdb，不写其他数据库。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Sequence
from uuid import uuid4

import duckdb
import pandas as pd

from lq.core.paths import WorkspaceRoots, default_settings
from lq.core.resumable import prepare_resumable_checkpoint, save_resumable_checkpoint
from lq.trade.contracts import TradeRecord, TradeRunSummary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DuckDB schema
# ---------------------------------------------------------------------------

TRADE_RUNTIME_SCHEMA_SQL = """
-- 交易记录表（主输出，每笔已完成交易）
CREATE TABLE IF NOT EXISTS trade_record (
    trade_id             VARCHAR PRIMARY KEY,
    code                 VARCHAR NOT NULL,
    signal_date          DATE    NOT NULL,
    entry_date           DATE    NOT NULL,
    exit_date            DATE,
    signal_pattern       VARCHAR NOT NULL,
    surface_label        VARCHAR,
    entry_price          DOUBLE  NOT NULL,
    exit_price           DOUBLE,
    lot_count            INTEGER NOT NULL,
    initial_stop_price   DOUBLE  NOT NULL,
    first_target_price   DOUBLE  NOT NULL,
    risk_unit            DOUBLE  NOT NULL,
    pnl_amount           DOUBLE,
    pnl_pct              DOUBLE,
    r_multiple           DOUBLE,
    exit_reason          VARCHAR,
    lifecycle_state      VARCHAR NOT NULL,
    pb_sequence_number   INTEGER,
    run_id               VARCHAR,
    created_at           TIMESTAMP DEFAULT current_timestamp
);

-- 回测 run 汇总表
CREATE TABLE IF NOT EXISTS trade_run_summary (
    run_id               VARCHAR PRIMARY KEY,
    strategy_name        VARCHAR NOT NULL,
    asof_date            DATE,
    signal_count         INTEGER DEFAULT 0,
    trade_count          INTEGER DEFAULT 0,
    win_count            INTEGER DEFAULT 0,
    loss_count           INTEGER DEFAULT 0,
    avg_r_multiple       DOUBLE,
    avg_pnl_pct          DOUBLE,
    max_drawdown_pct     DOUBLE,
    created_at           TIMESTAMP DEFAULT current_timestamp
);

-- 构建 manifest
CREATE TABLE IF NOT EXISTS trade_build_manifest (
    run_id         VARCHAR PRIMARY KEY,
    status         VARCHAR NOT NULL,
    asof_date      DATE,
    record_count   INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT current_timestamp
);
"""

_RECORD_COLS = (
    "trade_id", "code", "signal_date", "entry_date", "exit_date",
    "signal_pattern", "surface_label",
    "entry_price", "exit_price", "lot_count",
    "initial_stop_price", "first_target_price", "risk_unit",
    "pnl_amount", "pnl_pct", "r_multiple",
    "exit_reason", "lifecycle_state", "pb_sequence_number",
    "run_id", "created_at",
)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

def bootstrap_trade_storage(trade_db_path: Path) -> None:
    """初始化 trade_runtime.duckdb schema（幂等）。"""
    trade_db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(trade_db_path)) as conn:
        conn.execute(TRADE_RUNTIME_SCHEMA_SQL)


# ---------------------------------------------------------------------------
# 构建结果
# ---------------------------------------------------------------------------

@dataclass
class TradeBuildResult:
    """交易回测构建结果摘要。"""

    run_id: str = field(
        default_factory=lambda: f"trade-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    )
    dates_total: int = 0
    dates_completed: int = 0
    dates_skipped: int = 0
    records_written: int = 0
    signals_processed: int = 0
    errors: int = 0
    status: str = "completed"


# ---------------------------------------------------------------------------
# 核心构建函数
# ---------------------------------------------------------------------------

def run_trade_build(
    *,
    market_base_path: Path,
    malf_db_path: Path,
    research_lab_path: Path,
    trade_db_path: Path,
    signal_dates: Sequence[date],
    codes: Sequence[str] | None = None,
    strategy_name: str = "pas_default",
    resume: bool = False,
    reset_checkpoint: bool = False,
    settings: WorkspaceRoots | None = None,
    verbose: bool = True,
) -> TradeBuildResult:
    """交易回测全量/增量构建，支持断点续传。

    核心流程：
        1. 按日期逐日处理
        2. 每日从 research_lab 读取当日 PAS 信号
        3. 对每个信号：计算头寸 → TradeManager 模拟 → 生成 TradeRecord
        4. 写入 trade_runtime.duckdb
        5. 每个日期完成后保存 checkpoint

    参数：
        market_base_path  — market_base.duckdb（只读，读日线做 trade 模拟）
        malf_db_path      — malf.duckdb（只读）
        research_lab_path — research_lab.duckdb（只读，读 PAS 信号）
        trade_db_path     — trade_runtime.duckdb（读写）
        signal_dates      — 待处理日期列表
        codes             — 股票代码过滤（None = 不过滤）
        strategy_name     — 策略名称标识
        resume            — 从 checkpoint 续跑
        reset_checkpoint  — 清空旧 checkpoint 重跑
        settings          — WorkspaceRoots（用于 checkpoint 路径）
        verbose           — 打印进度
    """
    if not signal_dates:
        return TradeBuildResult(status="empty")

    bootstrap_trade_storage(trade_db_path)

    result = TradeBuildResult(dates_total=len(signal_dates))

    # 准备 checkpoint
    if settings is None:
        settings = default_settings()
    fingerprint = {
        "trade_db": str(trade_db_path),
        "dates_range": f"{signal_dates[0]}..{signal_dates[-1]}",
        "strategy": strategy_name,
    }
    store, state = prepare_resumable_checkpoint(
        checkpoint_path=None,
        settings_root=settings,
        domain="trade",
        runner_name="build_backtest",
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
            # 读取当日 PAS 信号
            signals = _load_signals_for_date(
                research_lab_path, sig_date, codes,
            )
            result.signals_processed += len(signals)

            if not signals:
                result.dates_completed += 1
                completed_dates.add(date_key)
                if verbose:
                    print(" → 无信号")
                continue

            # 对每个信号执行回测模拟
            records = _simulate_trades(
                market_base_path, signals, sig_date, result.run_id,
            )

            # 写入数据库
            if records:
                _flush_records(trade_db_path, records, result.run_id)
                result.records_written += len(records)

            result.dates_completed += 1
            completed_dates.add(date_key)

            if verbose:
                print(f" → {len(signals)} 信号，{len(records)} 交易记录")

        except Exception as exc:
            result.errors += 1
            logger.warning("Trade 构建失败 %s: %s", date_key, exc)
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
    _write_manifest(trade_db_path, result, signal_dates[-1])

    if verbose:
        print(
            f"\n完成：{result.dates_completed} 日完成 / "
            f"{result.dates_skipped} 日跳过 / {result.dates_total} 日总计"
        )
        print(
            f"处理 {result.signals_processed} 信号，"
            f"写入 {result.records_written} 交易记录，"
            f"失败 {result.errors}"
        )

    return result


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _load_signals_for_date(
    research_lab_path: Path,
    signal_date: date,
    codes: Sequence[str] | None,
) -> list[dict[str, Any]]:
    """从 research_lab 读取指定日期的 PAS 正式信号。"""
    with duckdb.connect(str(research_lab_path), read_only=True) as conn:
        if codes:
            rows = conn.execute(
                "SELECT signal_id, code, signal_date, pattern, surface_label, "
                "       strength, signal_low, entry_ref_price, pb_sequence_number "
                "FROM pas_formal_signal "
                "WHERE signal_date = ? AND code = ANY(?)",
                [signal_date, list(codes)],
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT signal_id, code, signal_date, pattern, surface_label, "
                "       strength, signal_low, entry_ref_price, pb_sequence_number "
                "FROM pas_formal_signal "
                "WHERE signal_date = ?",
                [signal_date],
            ).fetchall()
    cols = [
        "signal_id", "code", "signal_date", "pattern", "surface_label",
        "strength", "signal_low", "entry_ref_price", "pb_sequence_number",
    ]
    return [dict(zip(cols, r)) for r in rows]


def _simulate_trades(
    market_base_path: Path,
    signals: list[dict[str, Any]],
    signal_date: date,
    run_id: str,
) -> list[dict[str, Any]]:
    """对一批 PAS 信号执行交易模拟，返回 TradeRecord 行。

    简化模拟逻辑：
    - 以 T+1 开盘价入场
    - 运行 TradeManager.update() 直到交易关闭或超过 MAX_HOLD_DAYS
    - 生成 TradeRecord
    """
    from lq.core.calendar import next_trading_day
    from lq.position.sizing import compute_position_plan
    from lq.alpha.pas.contracts import PasSignal
    from lq.trade.management import TradeManager, TradeManagementState

    records: list[dict[str, Any]] = []

    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        for sig_dict in signals:
            try:
                code = sig_dict["code"]
                entry_date = next_trading_day(signal_date)

                # 读取入场日及后续日线（用于模拟）
                future_df = conn.execute(
                    "SELECT trade_date, open, high, low, close "
                    "FROM stock_daily_adjusted "
                    "WHERE code = ? AND adjust_method = 'backward' "
                    "  AND trade_date >= ? "
                    "ORDER BY trade_date LIMIT 30",
                    [code, entry_date],
                ).df()

                if future_df.empty:
                    continue

                # 入场价 = T+1 开盘价
                entry_price = float(future_df.iloc[0]["open"])
                if entry_price <= 0:
                    continue

                # 构建 PasSignal 并计算头寸
                pas_signal = PasSignal(
                    signal_id=sig_dict["signal_id"],
                    code=code,
                    signal_date=signal_date,
                    pattern=sig_dict["pattern"],
                    surface_label=sig_dict.get("surface_label", "UNKNOWN"),
                    strength=sig_dict.get("strength", 0.5),
                    signal_low=sig_dict["signal_low"],
                    entry_ref_price=sig_dict["entry_ref_price"],
                    pb_sequence_number=sig_dict.get("pb_sequence_number"),
                )
                plan = compute_position_plan(pas_signal, entry_price)

                # 初始化 TradeManager
                state = TradeManagementState(
                    trade_id=f"t-{sig_dict['signal_id'][:16]}",
                    code=code,
                    signal_date=signal_date,
                    entry_date=entry_date,
                    entry_price=entry_price,
                    initial_stop_price=plan.initial_stop_price,
                    first_target_price=plan.first_target_price,
                    risk_unit=plan.risk_unit,
                    total_lots=plan.lot_count,
                    active_lots=plan.lot_count,
                    signal_pattern=sig_dict["pattern"],
                    surface_label=sig_dict.get("surface_label", "UNKNOWN"),
                    pb_sequence_number=sig_dict.get("pb_sequence_number"),
                )
                mgr = TradeManager(state=state)
                mgr.activate(entry_price)

                # 逐日模拟（跳过入场日当天，从第二行开始）
                exit_date = None
                exit_price = None
                for _, row in future_df.iloc[1:].iterrows():
                    td = pd.Timestamp(row["trade_date"]).date()
                    mgr.update(
                        float(row["high"]),
                        float(row["low"]),
                        float(row["close"]),
                        td,
                    )
                    if state.is_closed:
                        exit_date = td
                        exit_price = float(row["close"])
                        break

                # 未关闭时以最后一行收盘价记录
                if not state.is_closed and len(future_df) > 1:
                    last = future_df.iloc[-1]
                    exit_date = pd.Timestamp(last["trade_date"]).date()
                    exit_price = float(last["close"])

                record = mgr.to_trade_record(exit_date, exit_price)
                records.append(_record_to_row(record))

            except Exception as exc:
                logger.debug("Trade 模拟失败 %s: %s", sig_dict.get("code"), exc)

    return records


def _record_to_row(rec: TradeRecord) -> dict[str, Any]:
    """TradeRecord → 数据库行。"""
    return {
        "trade_id": rec.trade_id,
        "code": rec.code,
        "signal_date": rec.signal_date,
        "entry_date": rec.entry_date,
        "exit_date": rec.exit_date,
        "signal_pattern": rec.signal_pattern,
        "surface_label": rec.surface_label,
        "entry_price": rec.entry_price,
        "exit_price": rec.exit_price,
        "lot_count": rec.lot_count,
        "initial_stop_price": rec.initial_stop_price,
        "first_target_price": rec.first_target_price,
        "risk_unit": rec.risk_unit,
        "pnl_amount": rec.pnl_amount,
        "pnl_pct": rec.pnl_pct,
        "r_multiple": rec.r_multiple,
        "exit_reason": rec.exit_reason,
        "lifecycle_state": rec.lifecycle_state,
        "pb_sequence_number": rec.pb_sequence_number,
    }


def _flush_records(
    trade_db_path: Path,
    rows: list[dict[str, Any]],
    run_id: str,
) -> None:
    """写入一批交易记录（先删后插，幂等）。"""
    _batch_df = pd.DataFrame(rows)
    _batch_df["run_id"] = run_id
    _batch_df["created_at"] = datetime.utcnow()

    trade_ids = _batch_df["trade_id"].unique().tolist()

    col_list = ", ".join(_RECORD_COLS)
    with duckdb.connect(str(trade_db_path)) as conn:
        conn.execute(
            "DELETE FROM trade_record WHERE trade_id = ANY(?)",
            [trade_ids],
        )
        conn.execute(
            f"INSERT INTO trade_record ({col_list}) "
            f"SELECT {col_list} FROM _batch_df"
        )


def _write_manifest(
    trade_db_path: Path,
    result: TradeBuildResult,
    asof_date: date,
) -> None:
    """写入构建 manifest 记录。"""
    with duckdb.connect(str(trade_db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO trade_build_manifest "
            "VALUES (?, ?, ?, ?, current_timestamp)",
            [result.run_id, result.status, asof_date, result.records_written],
        )
