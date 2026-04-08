"""MALF 构建 pipeline — 批量生成 MALF 上下文快照，支持分批构建与断点续传。

核心原则（七库全持久化纪律）：
    历史一旦发生就是永恒的瞬间——绝不重算。
    磁盘空间换内存，小批量断点续传。

用法：
    1. 全量构建：run_malf_build(signal_dates=[...], ...) — 首次初始化历史
    2. 日增量：run_malf_build(signal_dates=[today], ...) — 每日收盘后追加
    3. 断点续传：run_malf_build(..., resume=True) — 中断后从上次继续
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
from lq.malf.contracts import (
    MalfContext,
    MALFBuildManifest,
    EXECUTION_CONTEXT_CONTRACT_VERSION,
    build_malf_context_4,
    derive_long_background_2,
    derive_intermediate_role_2,
)
from lq.malf.daily import compute_daily_rhythm
from lq.malf.monthly import classify_monthly_state, compute_monthly_strength
from lq.malf.weekly import classify_weekly_flow, compute_weekly_strength

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DuckDB schema（含日线节奏字段）
# ---------------------------------------------------------------------------

MALF_SCHEMA_SQL = """
-- MALF 上下文快照表（主输出）
CREATE TABLE IF NOT EXISTS malf_context_snapshot (
    code                     VARCHAR NOT NULL,
    signal_date              DATE    NOT NULL,
    -- 执行层主字段
    long_background_2        VARCHAR NOT NULL,
    intermediate_role_2      VARCHAR NOT NULL,
    malf_context_4           VARCHAR NOT NULL,
    -- 计算层诊断
    monthly_state            VARCHAR NOT NULL,
    weekly_flow              VARCHAR NOT NULL,
    monthly_strength         DOUBLE,
    weekly_strength          DOUBLE,
    -- 日线节奏
    is_new_high_today        BOOLEAN DEFAULT FALSE,
    new_high_seq             INTEGER DEFAULT 0,
    days_since_last_new_high INTEGER,
    new_high_count_in_window INTEGER DEFAULT 0,
    -- 生命周期三轴原始排位（排位逻辑待实现）
    amplitude_rank_low       INTEGER,
    amplitude_rank_high      INTEGER,
    amplitude_rank_total     INTEGER,
    duration_rank_low        INTEGER,
    duration_rank_high       INTEGER,
    duration_rank_total      INTEGER,
    new_price_rank_low       INTEGER,
    new_price_rank_high      INTEGER,
    new_price_rank_total     INTEGER,
    -- 总生命区间
    lifecycle_rank_low       INTEGER,
    lifecycle_rank_high      INTEGER,
    lifecycle_rank_total     INTEGER,
    -- 四分位辅助
    amplitude_quartile       VARCHAR,
    duration_quartile        VARCHAR,
    new_price_quartile       VARCHAR,
    lifecycle_quartile       VARCHAR,
    -- 元数据
    run_id                   VARCHAR,
    created_at               TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (code, signal_date)
);

-- 构建 manifest
CREATE TABLE IF NOT EXISTS malf_build_manifest (
    run_id         VARCHAR PRIMARY KEY,
    status         VARCHAR NOT NULL,
    asof_date      DATE,
    index_count    INTEGER DEFAULT 0,
    stock_count    INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS execution_context_snapshot (
    entity_scope            VARCHAR NOT NULL,
    entity_code             VARCHAR NOT NULL,
    calc_date               DATE    NOT NULL,
    run_id                  VARCHAR,
    long_background_2       VARCHAR NOT NULL,
    intermediate_role_2     VARCHAR NOT NULL,
    malf_context_4          VARCHAR NOT NULL,
    active_wave_id          VARCHAR,
    historical_sample_count INTEGER,
    amplitude_rank_low      INTEGER,
    amplitude_rank_high     INTEGER,
    amplitude_rank_total    INTEGER,
    duration_rank_low       INTEGER,
    duration_rank_high      INTEGER,
    duration_rank_total     INTEGER,
    new_price_rank_low      INTEGER,
    new_price_rank_high      INTEGER,
    new_price_rank_total    INTEGER,
    lifecycle_rank_low      INTEGER,
    lifecycle_rank_high      INTEGER,
    lifecycle_rank_total    INTEGER,
    amplitude_quartile      VARCHAR,
    duration_quartile       VARCHAR,
    new_price_quartile      VARCHAR,
    lifecycle_quartile      VARCHAR,
    ranking_asof_date       DATE,
    contract_version        VARCHAR NOT NULL,
    created_at              TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (entity_scope, entity_code, calc_date)
);
"""

# 已有数据库的 migration（补齐新字段）
_MIGRATION_STMTS = [
    # 执行层主字段
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS long_background_2 VARCHAR DEFAULT 'UNKNOWN'",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS intermediate_role_2 VARCHAR DEFAULT 'UNKNOWN'",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS malf_context_4 VARCHAR DEFAULT 'UNKNOWN'",
    # 日线节奏
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS is_new_high_today BOOLEAN DEFAULT FALSE",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_high_seq INTEGER DEFAULT 0",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS days_since_last_new_high INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_high_count_in_window INTEGER DEFAULT 0",
    # 生命周期排位
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS amplitude_rank_low INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS amplitude_rank_high INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS amplitude_rank_total INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS duration_rank_low INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS duration_rank_high INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS duration_rank_total INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_price_rank_low INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_price_rank_high INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_price_rank_total INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS lifecycle_rank_low INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS lifecycle_rank_high INTEGER",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS lifecycle_rank_total INTEGER",
    # 四分位
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS amplitude_quartile VARCHAR",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS duration_quartile VARCHAR",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS new_price_quartile VARCHAR",
    "ALTER TABLE malf_context_snapshot ADD COLUMN IF NOT EXISTS lifecycle_quartile VARCHAR",
]

# 写入数据库的列名顺序（与 _context_to_row + run_id + created_at 对齐）
_SNAPSHOT_COLS = (
    "code", "signal_date",
    "long_background_2", "intermediate_role_2", "malf_context_4",
    "monthly_state", "weekly_flow",
    "monthly_strength", "weekly_strength",
    "is_new_high_today", "new_high_seq", "days_since_last_new_high",
    "new_high_count_in_window",
    "amplitude_rank_low", "amplitude_rank_high", "amplitude_rank_total",
    "duration_rank_low", "duration_rank_high", "duration_rank_total",
    "new_price_rank_low", "new_price_rank_high", "new_price_rank_total",
    "lifecycle_rank_low", "lifecycle_rank_high", "lifecycle_rank_total",
    "amplitude_quartile", "duration_quartile", "new_price_quartile", "lifecycle_quartile",
    "run_id", "created_at",
)

_EXECUTION_CONTEXT_COLS = (
    "entity_scope", "entity_code", "calc_date", "run_id",
    "long_background_2", "intermediate_role_2", "malf_context_4",
    "active_wave_id", "historical_sample_count",
    "amplitude_rank_low", "amplitude_rank_high", "amplitude_rank_total",
    "duration_rank_low", "duration_rank_high", "duration_rank_total",
    "new_price_rank_low", "new_price_rank_high", "new_price_rank_total",
    "lifecycle_rank_low", "lifecycle_rank_high", "lifecycle_rank_total",
    "amplitude_quartile", "duration_quartile", "new_price_quartile", "lifecycle_quartile",
    "ranking_asof_date", "contract_version", "created_at",
)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

def bootstrap_malf_storage(malf_db_path: Path) -> None:
    """初始化 MALF 数据库 schema（幂等，含迁移）。"""
    malf_db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(malf_db_path)) as conn:
        conn.execute(MALF_SCHEMA_SQL)
        for stmt in _MIGRATION_STMTS:
            try:
                conn.execute(stmt)
            except Exception:
                pass  # 列已存在，忽略


# ---------------------------------------------------------------------------
# 单股票计算（供 orchestration.py 直接调用）
# ---------------------------------------------------------------------------

def build_malf_context_for_stock(
    code: str,
    signal_date: date,
    monthly_bars: pd.DataFrame,
    weekly_bars: pd.DataFrame,
    daily_bars: pd.DataFrame | None = None,
) -> MalfContext:
    """为单只股票生成当日 MALF 上下文快照。

    参数：
        code         — 股票代码
        signal_date  — 信号日期（T 日）
        monthly_bars — 月线 DataFrame（至少含 [month_start, close]）
        weekly_bars  — 周线 DataFrame（至少含 [week_start, close]）
        daily_bars   — 可选日线 DataFrame（至少含 [trade_date, close]）
    """
    # 计算层：月线八态
    monthly_state = classify_monthly_state(monthly_bars, signal_date)
    monthly_strength = compute_monthly_strength(monthly_bars, signal_date)

    # 计算层：周线顺逆
    weekly_flow = classify_weekly_flow(weekly_bars, monthly_state, signal_date)
    weekly_strength = compute_weekly_strength(weekly_bars, signal_date)

    # 执行层：四格上下文
    long_bg = derive_long_background_2(monthly_state)
    inter_role = derive_intermediate_role_2(weekly_flow)
    ctx4 = build_malf_context_4(monthly_state, weekly_flow)

    # 日线节奏（可选，需要 L2 日线数据）
    rhythm = compute_daily_rhythm(daily_bars, signal_date) if daily_bars is not None else {}

    return MalfContext(
        code=code,
        signal_date=signal_date,
        long_background_2=long_bg,
        intermediate_role_2=inter_role,
        malf_context_4=ctx4,
        monthly_state=monthly_state,
        weekly_flow=weekly_flow,
        monthly_strength=monthly_strength,
        weekly_strength=weekly_strength,
        **rhythm,
    )


# ---------------------------------------------------------------------------
# 批量构建结果
# ---------------------------------------------------------------------------

@dataclass
class MalfBuildResult:
    """MALF 构建结果摘要。"""

    run_id: str = field(
        default_factory=lambda: f"malf-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    )
    dates_total: int = 0
    dates_completed: int = 0
    dates_skipped: int = 0
    rows_written: int = 0
    errors: int = 0
    status: str = "completed"


# ---------------------------------------------------------------------------
# 辅助查询
# ---------------------------------------------------------------------------

def list_stock_codes(market_base_path: Path) -> list[str]:
    """从 market_base 获取所有有月线数据的股票代码。"""
    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT code FROM stock_monthly_adjusted ORDER BY code"
        ).fetchall()
    return [r[0] for r in rows]


def list_trading_dates(
    market_base_path: Path,
    start: date,
    end: date,
) -> list[date]:
    """从 market_base 获取指定范围内有日线数据的交易日。"""
    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT trade_date FROM stock_daily_adjusted "
            "WHERE trade_date >= ? AND trade_date <= ? "
            "ORDER BY trade_date",
            [start, end],
        ).fetchall()
    return [r[0] for r in rows]


# ---------------------------------------------------------------------------
# 核心构建函数
# ---------------------------------------------------------------------------

def run_malf_build(
    *,
    market_base_path: Path,
    malf_db_path: Path,
    signal_dates: Sequence[date],
    codes: Sequence[str] | None = None,
    batch_size: int = 200,
    include_daily_rhythm: bool = True,
    resume: bool = False,
    reset_checkpoint: bool = False,
    settings: WorkspaceRoots | None = None,
    verbose: bool = True,
) -> MalfBuildResult:
    """MALF 全量/增量构建，支持断点续传。

    核心流程：
        1. 按日期逐日处理
        2. 每日内按 batch_size 分批处理股票
        3. 每批完成立即写入 malf.duckdb
        4. 每个日期完成后保存 checkpoint
        5. resume=True 时从最后完成的日期继续

    参数：
        market_base_path    — market_base.duckdb（只读）
        malf_db_path        — malf.duckdb（读写）
        signal_dates        — 待构建日期列表
        codes               — 股票代码列表（None = 全市场）
        batch_size          — 每批股票数（控制内存，默认 200）
        include_daily_rhythm — 计算日线新价结构
        resume              — 从 checkpoint 续跑
        reset_checkpoint    — 清空旧 checkpoint 重跑
        settings            — WorkspaceRoots（用于 checkpoint 路径）
        verbose             — 打印进度
    """
    if not signal_dates:
        return MalfBuildResult(status="empty")

    bootstrap_malf_storage(malf_db_path)

    # 解析股票代码
    if codes is None:
        codes = list_stock_codes(market_base_path)
        if verbose:
            print(f"自动获取全市场股票：{len(codes)} 只")
    all_codes = list(codes)

    result = MalfBuildResult(dates_total=len(signal_dates))

    # 准备 checkpoint
    if settings is None:
        settings = default_settings()
    fingerprint = {
        "malf_db": str(malf_db_path),
        "dates_range": f"{signal_dates[0]}..{signal_dates[-1]}",
        "codes_count": len(all_codes),
        "include_daily_rhythm": include_daily_rhythm,
    }
    store, state = prepare_resumable_checkpoint(
        checkpoint_path=None,
        settings_root=settings,
        domain="malf",
        runner_name="build_snapshot",
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
    with duckdb.connect(str(market_base_path), read_only=True) as base_conn:
        for idx, sig_date in enumerate(signal_dates):
            date_key = sig_date.isoformat()

            # 跳过已完成日期
            if date_key in completed_dates:
                result.dates_skipped += 1
                continue

            if verbose:
                print(
                    f"  [{idx + 1}/{len(signal_dates)}] {date_key}",
                    end="", flush=True,
                )

            date_rows = 0
            date_errors = 0

            # 分批处理
            for b_start in range(0, len(all_codes), batch_size):
                batch_codes = all_codes[b_start:b_start + batch_size]
                rows = _compute_batch(
                    base_conn, batch_codes, sig_date, include_daily_rhythm,
                )
                if rows:
                    _flush_batch(malf_db_path, rows, result.run_id)
                    date_rows += len(rows)
                date_errors += len(batch_codes) - len(rows)

            result.rows_written += date_rows
            result.errors += date_errors
            result.dates_completed += 1
            completed_dates.add(date_key)

            if verbose:
                msg = f" → {date_rows} 行"
                if date_errors:
                    msg += f"（失败 {date_errors}）"
                print(msg)

            # 每个日期完成后保存 checkpoint
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
    _write_manifest(malf_db_path, result, signal_dates[-1])

    if verbose:
        print(
            f"\n完成：{result.dates_completed} 日完成 / "
            f"{result.dates_skipped} 日跳过 / {result.dates_total} 日总计"
        )
        print(f"写入 {result.rows_written} 行，失败 {result.errors}")

    return result


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _compute_batch(
    base_conn: duckdb.DuckDBPyConnection,
    codes: list[str],
    signal_date: date,
    include_daily_rhythm: bool,
) -> list[dict[str, Any]]:
    """为一批股票在指定日期计算 MALF 快照。"""
    results: list[dict[str, Any]] = []
    for code in codes:
        try:
            monthly_df = base_conn.execute(
                "SELECT month_start_date AS month_start, trade_date, "
                "       open, high, low, close, volume "
                "FROM stock_monthly_adjusted "
                "WHERE code = ? AND adjust_method = 'backward' "
                "ORDER BY month_start_date",
                [code],
            ).df()

            weekly_df = base_conn.execute(
                "SELECT week_start_date AS week_start, trade_date, "
                "       open, high, low, close, volume "
                "FROM stock_weekly_adjusted "
                "WHERE code = ? AND adjust_method = 'backward' "
                "ORDER BY week_start_date",
                [code],
            ).df()

            daily_df = None
            if include_daily_rhythm:
                try:
                    daily_df = base_conn.execute(
                        "SELECT trade_date, close "
                        "FROM stock_daily_adjusted "
                        "WHERE code = ? AND adjust_method = 'backward' "
                        "ORDER BY trade_date",
                        [code],
                    ).df()
                except Exception:
                    pass  # 静默降级

            ctx = build_malf_context_for_stock(
                code, signal_date, monthly_df, weekly_df, daily_df,
            )
            results.append(_context_to_row(ctx))
        except Exception as exc:
            logger.debug("MALF 计算失败 %s@%s: %s", code, signal_date, exc)
    return results


def _context_to_row(ctx: MalfContext) -> dict[str, Any]:
    """MalfContext → 数据库行（保持原生 Python 类型，不转 ISO 字符串）。"""
    return {
        "code": ctx.code,
        "signal_date": ctx.signal_date,
        "long_background_2": ctx.long_background_2,
        "intermediate_role_2": ctx.intermediate_role_2,
        "malf_context_4": ctx.malf_context_4,
        "monthly_state": ctx.monthly_state,
        "weekly_flow": ctx.weekly_flow,
        "monthly_strength": ctx.monthly_strength,
        "weekly_strength": ctx.weekly_strength,
        "is_new_high_today": ctx.is_new_high_today,
        "new_high_seq": ctx.new_high_seq,
        "days_since_last_new_high": ctx.days_since_last_new_high,
        "new_high_count_in_window": ctx.new_high_count_in_window,
        "amplitude_rank_low": ctx.amplitude_rank_low,
        "amplitude_rank_high": ctx.amplitude_rank_high,
        "amplitude_rank_total": ctx.amplitude_rank_total,
        "duration_rank_low": ctx.duration_rank_low,
        "duration_rank_high": ctx.duration_rank_high,
        "duration_rank_total": ctx.duration_rank_total,
        "new_price_rank_low": ctx.new_price_rank_low,
        "new_price_rank_high": ctx.new_price_rank_high,
        "new_price_rank_total": ctx.new_price_rank_total,
        "lifecycle_rank_low": ctx.lifecycle_rank_low,
        "lifecycle_rank_high": ctx.lifecycle_rank_high,
        "lifecycle_rank_total": ctx.lifecycle_rank_total,
        "amplitude_quartile": ctx.amplitude_quartile,
        "duration_quartile": ctx.duration_quartile,
        "new_price_quartile": ctx.new_price_quartile,
        "lifecycle_quartile": ctx.lifecycle_quartile,
    }


def _build_execution_context_df(batch_df: pd.DataFrame) -> pd.DataFrame:
    exec_df = pd.DataFrame({
        "entity_scope": "stock",
        "entity_code": batch_df["code"],
        "calc_date": batch_df["signal_date"],
        "run_id": batch_df["run_id"],
        "long_background_2": batch_df["long_background_2"],
        "intermediate_role_2": batch_df["intermediate_role_2"],
        "malf_context_4": batch_df["malf_context_4"],
        "active_wave_id": None,
        "historical_sample_count": None,
        "amplitude_rank_low": batch_df["amplitude_rank_low"],
        "amplitude_rank_high": batch_df["amplitude_rank_high"],
        "amplitude_rank_total": batch_df["amplitude_rank_total"],
        "duration_rank_low": batch_df["duration_rank_low"],
        "duration_rank_high": batch_df["duration_rank_high"],
        "duration_rank_total": batch_df["duration_rank_total"],
        "new_price_rank_low": batch_df["new_price_rank_low"],
        "new_price_rank_high": batch_df["new_price_rank_high"],
        "new_price_rank_total": batch_df["new_price_rank_total"],
        "lifecycle_rank_low": batch_df["lifecycle_rank_low"],
        "lifecycle_rank_high": batch_df["lifecycle_rank_high"],
        "lifecycle_rank_total": batch_df["lifecycle_rank_total"],
        "amplitude_quartile": batch_df["amplitude_quartile"],
        "duration_quartile": batch_df["duration_quartile"],
        "new_price_quartile": batch_df["new_price_quartile"],
        "lifecycle_quartile": batch_df["lifecycle_quartile"],
        "ranking_asof_date": batch_df["signal_date"],
        "contract_version": EXECUTION_CONTEXT_CONTRACT_VERSION,
        "created_at": batch_df["created_at"],
    })
    return exec_df


def _flush_batch(malf_db_path: Path, rows: list[dict], run_id: str) -> None:
    """写入一批 MALF 快照（先删后插，幂等）。"""
    _batch_df = pd.DataFrame(rows)
    _batch_df["run_id"] = run_id
    _batch_df["created_at"] = datetime.utcnow()
    _execution_context_df = _build_execution_context_df(_batch_df)

    sig_date = _batch_df["signal_date"].iloc[0]
    batch_codes = _batch_df["code"].unique().tolist()

    col_list = ", ".join(_SNAPSHOT_COLS)
    exec_col_list = ", ".join(_EXECUTION_CONTEXT_COLS)
    with duckdb.connect(str(malf_db_path)) as conn:
        conn.execute(
            "DELETE FROM malf_context_snapshot "
            "WHERE signal_date = ? AND code = ANY(?)",
            [sig_date, batch_codes],
        )
        conn.execute(
            "DELETE FROM execution_context_snapshot "
            "WHERE calc_date = ? AND entity_scope = 'stock' AND entity_code = ANY(?)",
            [sig_date, batch_codes],
        )
        conn.execute(
            f"INSERT INTO malf_context_snapshot ({col_list}) "
            f"SELECT {col_list} FROM _batch_df"
        )
        conn.execute(
            f"INSERT INTO execution_context_snapshot ({exec_col_list}) "
            f"SELECT {exec_col_list} FROM _execution_context_df"
        )


def _write_manifest(
    malf_db_path: Path,
    result: MalfBuildResult,
    asof_date: date,
) -> None:
    """写入构建 manifest 记录。"""
    with duckdb.connect(str(malf_db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO malf_build_manifest "
            "VALUES (?, ?, ?, ?, ?, current_timestamp)",
            [result.run_id, result.status, asof_date, 0, result.rows_written],
        )
