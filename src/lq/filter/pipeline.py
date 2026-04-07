"""Filter 构建 pipeline — 批量生成不利条件过滤快照，支持分批构建与断点续传。

核心原则（七库全持久化纪律）：
    历史一旦发生就是永恒的瞬间——绝不重算。
    磁盘空间换内存，小批量断点续传。

依赖链：filter 依赖 malf + structure 已完成构建。
    market_base → malf → structure → filter

用法：
    1. 全量构建：run_filter_build(signal_dates=[...], ...) — 首次初始化历史
    2. 日增量：run_filter_build(signal_dates=[today], ...) — 每日收盘后追加
    3. 断点续传：run_filter_build(..., resume=True) — 中断后从上次继续
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
from lq.filter.adverse import check_adverse_conditions, AdverseConditionResult
from lq.malf.contracts import MalfContext, build_surface_label

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DuckDB schema
# ---------------------------------------------------------------------------

FILTER_SCHEMA_SQL = """
-- 不利条件过滤快照表（主输出）
CREATE TABLE IF NOT EXISTS filter_snapshot (
    code                VARCHAR NOT NULL,
    signal_date         DATE    NOT NULL,
    tradeable           BOOLEAN NOT NULL,
    condition_count     INTEGER DEFAULT 0,
    active_conditions   VARCHAR,
    notes               VARCHAR,
    run_id              VARCHAR,
    created_at          TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (code, signal_date)
);

-- 构建 manifest
CREATE TABLE IF NOT EXISTS filter_build_manifest (
    run_id         VARCHAR PRIMARY KEY,
    status         VARCHAR NOT NULL,
    asof_date      DATE,
    stock_count    INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT current_timestamp
);
"""

# 写入数据库的列名顺序
_SNAPSHOT_COLS = (
    "code", "signal_date", "tradeable",
    "condition_count", "active_conditions", "notes",
    "run_id", "created_at",
)


# ---------------------------------------------------------------------------
# 初始化
# ---------------------------------------------------------------------------

def bootstrap_filter_storage(filter_db_path: Path) -> None:
    """初始化 filter 数据库 schema（幂等）。"""
    filter_db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(filter_db_path)) as conn:
        conn.execute(FILTER_SCHEMA_SQL)


# ---------------------------------------------------------------------------
# 批量构建结果
# ---------------------------------------------------------------------------

@dataclass
class FilterBuildResult:
    """Filter 构建结果摘要。"""

    run_id: str = field(
        default_factory=lambda: f"filter-{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
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
    """从 market_base 获取所有有日线数据的股票代码。"""
    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        rows = conn.execute(
            "SELECT DISTINCT code FROM stock_daily_adjusted ORDER BY code"
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

def run_filter_build(
    *,
    market_base_path: Path,
    malf_db_path: Path,
    structure_db_path: Path,
    filter_db_path: Path,
    signal_dates: Sequence[date],
    codes: Sequence[str] | None = None,
    batch_size: int = 200,
    resume: bool = False,
    reset_checkpoint: bool = False,
    settings: WorkspaceRoots | None = None,
    verbose: bool = True,
) -> FilterBuildResult:
    """Filter 全量/增量构建，支持断点续传。

    依赖：malf.duckdb 和 structure.duckdb 中对应日期的数据须已构建。

    核心流程：
        1. 按日期逐日处理
        2. 每日批量加载 MALF + structure 上下文
        3. 每批完成立即写入 filter.duckdb
        4. 每个日期完成后保存 checkpoint

    参数：
        market_base_path    — market_base.duckdb（只读，日线数据）
        malf_db_path        — malf.duckdb（只读，MALF 上下文）
        structure_db_path   — structure.duckdb（只读，结构位数据）
        filter_db_path      — filter.duckdb（读写）
        signal_dates        — 待构建日期列表
        codes               — 股票代码列表（None = 全市场）
        batch_size          — 每批股票数（控制内存，默认 200）
        resume              — 从 checkpoint 续跑
        reset_checkpoint    — 清空旧 checkpoint 重跑
        settings            — WorkspaceRoots（用于 checkpoint 路径）
        verbose             — 打印进度
    """
    if not signal_dates:
        return FilterBuildResult(status="empty")

    bootstrap_filter_storage(filter_db_path)

    # 解析股票代码
    if codes is None:
        codes = list_stock_codes(market_base_path)
        if verbose:
            print(f"自动获取全市场股票：{len(codes)} 只")
    all_codes = list(codes)

    result = FilterBuildResult(dates_total=len(signal_dates))

    # 准备 checkpoint
    if settings is None:
        settings = default_settings()
    fingerprint = {
        "filter_db": str(filter_db_path),
        "dates_range": f"{signal_dates[0]}..{signal_dates[-1]}",
        "codes_count": len(all_codes),
    }
    store, state = prepare_resumable_checkpoint(
        checkpoint_path=None,
        settings_root=settings,
        domain="filter",
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

    save_resumable_checkpoint(store, fingerprint=fingerprint, payload={
        "status": "running",
        "completed_dates": sorted(completed_dates),
        "run_id": result.run_id,
    })

    # 打开三个只读数据库连接
    with (
        duckdb.connect(str(market_base_path), read_only=True) as base_conn,
        duckdb.connect(str(malf_db_path), read_only=True) as malf_conn,
        duckdb.connect(str(structure_db_path), read_only=True) as struct_conn,
    ):
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

            # 批量预加载当日的 MALF 和 structure 上下文
            malf_dict = _load_malf_for_date(malf_conn, sig_date)
            struct_dict = _load_structure_for_date(struct_conn, sig_date)

            date_rows = 0
            date_errors = 0

            for b_start in range(0, len(all_codes), batch_size):
                batch_codes = all_codes[b_start:b_start + batch_size]
                rows = _compute_batch(
                    base_conn, batch_codes, sig_date,
                    malf_dict, struct_dict,
                )
                if rows:
                    _flush_batch(filter_db_path, rows, result.run_id)
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
    _write_manifest(filter_db_path, result, signal_dates[-1])

    if verbose:
        print(
            f"\n完成：{result.dates_completed} 日完成 / "
            f"{result.dates_skipped} 日跳过 / {result.dates_total} 日总计"
        )
        print(f"写入 {result.rows_written} 行，失败 {result.errors}")

    return result


# ---------------------------------------------------------------------------
# 内部辅助：预加载上游数据
# ---------------------------------------------------------------------------

def _load_malf_for_date(
    malf_conn: duckdb.DuckDBPyConnection,
    signal_date: date,
) -> dict[str, MalfContext]:
    """批量加载当日所有股票的 MALF 上下文（O(1) 查询/日）。"""
    try:
        df = malf_conn.execute(
            "SELECT code, monthly_state, weekly_flow, surface_label "
            "FROM malf_context_snapshot WHERE signal_date = ?",
            [signal_date],
        ).df()
    except Exception:
        return {}

    result: dict[str, MalfContext] = {}
    for _, row in df.iterrows():
        try:
            result[row["code"]] = MalfContext(
                code=row["code"],
                signal_date=signal_date,
                monthly_state=row["monthly_state"],
                weekly_flow=row["weekly_flow"],
                surface_label=row["surface_label"],
            )
        except Exception:
            continue
    return result


def _load_structure_for_date(
    struct_conn: duckdb.DuckDBPyConnection,
    signal_date: date,
) -> dict[str, tuple[float | None, float | None]]:
    """批量加载当日所有股票的结构位价格（O(1) 查询/日）。

    返回 {code: (nearest_support_price, nearest_resistance_price)}。
    """
    try:
        df = struct_conn.execute(
            "SELECT code, nearest_support_price, nearest_resistance_price "
            "FROM structure_snapshot WHERE signal_date = ?",
            [signal_date],
        ).df()
    except Exception:
        return {}

    result: dict[str, tuple[float | None, float | None]] = {}
    for _, row in df.iterrows():
        sup = row["nearest_support_price"]
        res = row["nearest_resistance_price"]
        # DuckDB NULL → pandas NaN → Python None
        sup = None if pd.isna(sup) else float(sup)
        res = None if pd.isna(res) else float(res)
        result[row["code"]] = (sup, res)
    return result


# ---------------------------------------------------------------------------
# 内部辅助：计算与写入
# ---------------------------------------------------------------------------

def _compute_batch(
    base_conn: duckdb.DuckDBPyConnection,
    codes: list[str],
    signal_date: date,
    malf_dict: dict[str, MalfContext],
    struct_dict: dict[str, tuple[float | None, float | None]],
) -> list[dict[str, Any]]:
    """为一批股票在指定日期计算不利条件过滤结果。"""
    results: list[dict[str, Any]] = []
    for code in codes:
        try:
            daily_df = base_conn.execute(
                "SELECT trade_date AS date, "
                "       open AS adj_open, high AS adj_high, "
                "       low AS adj_low, close AS adj_close, "
                "       volume AS adj_volume "
                "FROM stock_daily_adjusted "
                "WHERE code = ? AND adjust_method = 'backward' "
                "  AND trade_date <= ? "
                "ORDER BY trade_date",
                [code, signal_date],
            ).df()

            if daily_df.empty:
                continue

            malf_ctx = malf_dict.get(code)
            sup_price, res_price = struct_dict.get(code, (None, None))

            adverse = check_adverse_conditions(
                code=code,
                signal_date=signal_date,
                daily_bars=daily_df,
                malf_ctx=malf_ctx,
                nearest_support_price=sup_price,
                nearest_resistance_price=res_price,
            )
            results.append(_result_to_row(adverse))
        except Exception as exc:
            logger.debug("Filter 计算失败 %s@%s: %s", code, signal_date, exc)
    return results


def _result_to_row(result: AdverseConditionResult) -> dict[str, Any]:
    """AdverseConditionResult → 数据库行。"""
    return {
        "code": result.code,
        "signal_date": result.signal_date,
        "tradeable": result.tradeable,
        "condition_count": len(result.active_conditions),
        "active_conditions": (
            ";".join(result.active_conditions) if result.active_conditions else None
        ),
        "notes": result.notes or None,
    }


def _flush_batch(
    filter_db_path: Path,
    rows: list[dict],
    run_id: str,
) -> None:
    """写入一批过滤快照（先删后插，幂等）。"""
    _batch_df = pd.DataFrame(rows)
    _batch_df["run_id"] = run_id
    _batch_df["created_at"] = datetime.utcnow()

    sig_date = _batch_df["signal_date"].iloc[0]
    batch_codes = _batch_df["code"].unique().tolist()

    col_list = ", ".join(_SNAPSHOT_COLS)
    with duckdb.connect(str(filter_db_path)) as conn:
        conn.execute(
            "DELETE FROM filter_snapshot "
            "WHERE signal_date = ? AND code = ANY(?)",
            [sig_date, batch_codes],
        )
        conn.execute(
            f"INSERT INTO filter_snapshot ({col_list}) "
            f"SELECT {col_list} FROM _batch_df"
        )


def _write_manifest(
    filter_db_path: Path,
    result: FilterBuildResult,
    asof_date: date,
) -> None:
    """写入构建 manifest 记录。"""
    with duckdb.connect(str(filter_db_path)) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO filter_build_manifest "
            "VALUES (?, ?, ?, ?, current_timestamp)",
            [result.run_id, result.status, asof_date, result.rows_written],
        )
