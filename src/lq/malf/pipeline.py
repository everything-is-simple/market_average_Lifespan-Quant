"""MALF 构建 pipeline — 批量生成股票 MALF 上下文快照。"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Sequence

import duckdb
import pandas as pd

from lq.malf.contracts import (
    MalfContext,
    MalfContextSnapshot,
    MALFBuildManifest,
    build_surface_label,
)
from lq.malf.daily import compute_daily_rhythm
from lq.malf.monthly import classify_monthly_state, compute_monthly_strength
from lq.malf.weekly import classify_weekly_flow, compute_weekly_strength


# MALF DuckDB schema
MALF_SCHEMA_SQL = """
-- MALF 上下文快照表（主输出合同）
CREATE TABLE IF NOT EXISTS malf_context_snapshot (
    code              VARCHAR NOT NULL,
    signal_date       DATE    NOT NULL,
    monthly_state     VARCHAR NOT NULL,
    weekly_flow       VARCHAR NOT NULL,
    surface_label     VARCHAR NOT NULL,
    monthly_strength  DOUBLE,
    weekly_strength   DOUBLE,
    run_id            VARCHAR,
    created_at        TIMESTAMP DEFAULT current_timestamp,
    PRIMARY KEY (code, signal_date)
);

-- MALF 构建 manifest
CREATE TABLE IF NOT EXISTS malf_build_manifest (
    run_id         VARCHAR PRIMARY KEY,
    status         VARCHAR NOT NULL,
    asof_date      DATE,
    index_count    INTEGER DEFAULT 0,
    stock_count    INTEGER DEFAULT 0,
    created_at     TIMESTAMP DEFAULT current_timestamp
);
"""


def bootstrap_malf_storage(malf_db_path: Path) -> None:
    """初始化 MALF 数据库 schema。"""
    malf_db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(malf_db_path)) as conn:
        conn.execute(MALF_SCHEMA_SQL)


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
        monthly_bars — 该股票月线 DataFrame（至少含 [month_start, close]）
        weekly_bars  — 该股票周线 DataFrame（至少含 [week_start, close]）
        daily_bars   — 可选，该股票日线 DataFrame（至少含 [trade_date, close]）；
                       传入时计算日线节奏（新高日系列），否则使用默认零值

    返回：
        MalfContext 不可变对象
    """
    # 第一层：月线八态
    monthly_state = classify_monthly_state(monthly_bars, signal_date)
    monthly_strength = compute_monthly_strength(monthly_bars, signal_date)

    # 第二层：周线顺逆
    weekly_flow = classify_weekly_flow(weekly_bars, monthly_state, signal_date)
    weekly_strength = compute_weekly_strength(weekly_bars, signal_date)

    # 派生：表面标签
    surface_label = build_surface_label(monthly_state, weekly_flow)

    # 第三层：日线节奏（可选，需要 L2 日线数据）
    rhythm = compute_daily_rhythm(daily_bars, signal_date) if daily_bars is not None else {}

    return MalfContext(
        code=code,
        signal_date=signal_date,
        monthly_state=monthly_state,
        weekly_flow=weekly_flow,
        surface_label=surface_label,
        monthly_strength=monthly_strength,
        weekly_strength=weekly_strength,
        **rhythm,
    )


def run_malf_batch(
    codes: Sequence[str],
    signal_date: date,
    market_base_path: Path,
    malf_db_path: Path,
    include_daily_rhythm: bool = False,
) -> MALFBuildManifest:
    """批量构建所有股票的 MALF 上下文快照并写入数据库。

    参数：
        codes           — 股票代码列表
        signal_date     — 信号日期
        market_base_path — market_base 数据库路径
        malf_db_path    — malf 数据库路径
        include_daily_rhythm — True 时读取 L2 日线数据计算新高日节奏

    返回：
        MALFBuildManifest 构建摘要
    """
    bootstrap_malf_storage(malf_db_path)

    rows: list[dict] = []
    error_count = 0

    with duckdb.connect(str(market_base_path), read_only=True) as base_conn:
        for code in codes:
            try:
                # 读取月线数据（来源：market_base.stock_monthly_adjusted，后复权）
                monthly_df: pd.DataFrame = base_conn.execute(
                    "SELECT month_start_date AS month_start, trade_date, "
                    "       open, high, low, close, volume "
                    "FROM stock_monthly_adjusted "
                    "WHERE code = ? AND adjust_method = 'backward' "
                    "ORDER BY month_start_date",
                    [code],
                ).df()

                # 读取周线数据（来源：market_base.stock_weekly_adjusted，后复权）
                weekly_df: pd.DataFrame = base_conn.execute(
                    "SELECT week_start_date AS week_start, trade_date, "
                    "       open, high, low, close, volume "
                    "FROM stock_weekly_adjusted "
                    "WHERE code = ? AND adjust_method = 'backward' "
                    "ORDER BY week_start_date",
                    [code],
                ).df()

                # 第三层：日线节奏（可选）
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
                        daily_df = None  # 表不存在或查询失败时静默降级

                ctx = build_malf_context_for_stock(code, signal_date, monthly_df, weekly_df, daily_df)
                rows.append({**ctx.as_dict(), "run_id": None})

            except Exception:
                error_count += 1
                continue

    manifest = MALFBuildManifest(
        status="SUCCESS" if error_count == 0 else "PARTIAL",
        asof_date=signal_date,
        stock_count=len(rows),
    )

    if rows:
        with duckdb.connect(str(malf_db_path)) as malf_conn:
            # 写入快照（UPSERT）
            df_out = pd.DataFrame(rows)
            df_out["run_id"] = manifest.run_id
            # 删除当日已有数据后写入（保证幂等）
            malf_conn.execute(
                "DELETE FROM malf_context_snapshot WHERE signal_date = ?",
                [signal_date],
            )
            malf_conn.execute(
                "INSERT INTO malf_context_snapshot SELECT * FROM df_out"
            )
            # 写入 manifest
            malf_conn.execute(
                "INSERT OR REPLACE INTO malf_build_manifest VALUES (?, ?, ?, ?, ?, current_timestamp)",
                [
                    manifest.run_id,
                    manifest.status,
                    manifest.asof_date,
                    manifest.index_count,
                    manifest.stock_count,
                ],
            )

    return manifest


def run_malf_batch_incremental(
    codes: Sequence[str],
    signal_dates: Sequence[date],
    market_base_path: Path,
    malf_db_path: Path,
    skip_existing: bool = True,
    include_daily_rhythm: bool = False,
) -> MALFBuildManifest:
    """增量构建 MALF 上下文快照：只处理尚未计算的 (code, signal_date) 组合。

    参数：
        codes            — 股票代码列表
        signal_dates     — 需要计算的日期序列（支持多日批量）
        market_base_path — market_base 数据库路径（只读）
        malf_db_path     — malf 数据库路径（读写）
        skip_existing    — True 时跳过已有快照（幂等），False 时强制覆盖
        include_daily_rhythm — True 时读取 L2 日线数据计算新高日节奏

    返回：
        MALFBuildManifest 构建摘要（以最后一个 signal_date 为 asof_date）
    """
    bootstrap_malf_storage(malf_db_path)

    # 加载已有快照集合（code, date）
    existing: set[tuple[str, date]] = set()
    if skip_existing:
        with duckdb.connect(str(malf_db_path), read_only=True) as malf_conn:
            rows = malf_conn.execute(
                "SELECT code, signal_date FROM malf_context_snapshot "
                "WHERE signal_date = ANY(?)",
                [list(signal_dates)],
            ).fetchall()
            existing = {(r[0], r[1]) for r in rows}

    rows_out: list[dict] = []
    error_count = 0

    with duckdb.connect(str(market_base_path), read_only=True) as base_conn:
        for signal_date in signal_dates:
            for code in codes:
                if skip_existing and (code, signal_date) in existing:
                    continue   # 已有快照，跳过

                try:
                    monthly_df: pd.DataFrame = base_conn.execute(
                        "SELECT month_start_date AS month_start, trade_date, "
                        "       open, high, low, close, volume "
                        "FROM stock_monthly_adjusted "
                        "WHERE code = ? AND adjust_method = 'backward' "
                        "ORDER BY month_start_date",
                        [code],
                    ).df()

                    weekly_df: pd.DataFrame = base_conn.execute(
                        "SELECT week_start_date AS week_start, trade_date, "
                        "       open, high, low, close, volume "
                        "FROM stock_weekly_adjusted "
                        "WHERE code = ? AND adjust_method = 'backward' "
                        "ORDER BY week_start_date",
                        [code],
                    ).df()

                    # 第三层：日线节奏（可选）
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
                            daily_df = None  # 表不存在或查询失败时静默降级

                    ctx = build_malf_context_for_stock(code, signal_date, monthly_df, weekly_df, daily_df)
                    rows_out.append({**ctx.as_dict(), "run_id": None})
                except Exception:
                    error_count += 1
                    continue

    last_date = signal_dates[-1] if signal_dates else date.today()
    manifest = MALFBuildManifest(
        status="SUCCESS" if error_count == 0 else "PARTIAL",
        asof_date=last_date,
        stock_count=len(rows_out),
    )

    if rows_out:
        with duckdb.connect(str(malf_db_path)) as malf_conn:
            df_out = pd.DataFrame(rows_out)
            df_out["run_id"] = manifest.run_id
            # 增量写入：不清空全表，只 DELETE 本批次涉及的 (code, date) 后重插
            malf_conn.execute(
                "DELETE FROM malf_context_snapshot "
                "WHERE signal_date = ANY(?) AND code = ANY(?)",
                [list(signal_dates), list(codes)],
            )
            malf_conn.execute(
                "INSERT INTO malf_context_snapshot SELECT * FROM df_out"
            )
            malf_conn.execute(
                "INSERT OR REPLACE INTO malf_build_manifest "
                "VALUES (?, ?, ?, ?, ?, current_timestamp)",
                [
                    manifest.run_id,
                    manifest.status,
                    manifest.asof_date,
                    manifest.index_count,
                    manifest.stock_count,
                ],
            )

    return manifest
