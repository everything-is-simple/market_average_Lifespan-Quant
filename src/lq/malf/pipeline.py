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
) -> MalfContext:
    """为单只股票生成当日 MALF 上下文快照。

    参数：
        code         — 股票代码
        signal_date  — 信号日期（T 日）
        monthly_bars — 该股票月线 DataFrame（至少含 [month_start, close]）
        weekly_bars  — 该股票周线 DataFrame（至少含 [week_start, close]）

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

    return MalfContext(
        code=code,
        signal_date=signal_date,
        monthly_state=monthly_state,
        weekly_flow=weekly_flow,
        surface_label=surface_label,
        monthly_strength=monthly_strength,
        weekly_strength=weekly_strength,
    )


def run_malf_batch(
    codes: Sequence[str],
    signal_date: date,
    market_base_path: Path,
    malf_db_path: Path,
) -> MALFBuildManifest:
    """批量构建所有股票的 MALF 上下文快照并写入数据库。

    参数：
        codes           — 股票代码列表
        signal_date     — 信号日期
        market_base_path — market_base 数据库路径
        malf_db_path    — malf 数据库路径

    返回：
        MALFBuildManifest 构建摘要
    """
    bootstrap_malf_storage(malf_db_path)

    rows: list[dict] = []
    error_count = 0

    with duckdb.connect(str(market_base_path), read_only=True) as base_conn:
        for code in codes:
            try:
                # 读取月线数据
                monthly_df: pd.DataFrame = base_conn.execute(
                    "SELECT month_start, open, high, low, close, volume "
                    "FROM monthly_bar WHERE code = ? ORDER BY month_start",
                    [code],
                ).df()

                # 读取周线数据
                weekly_df: pd.DataFrame = base_conn.execute(
                    "SELECT week_start, open, high, low, close, volume "
                    "FROM weekly_bar WHERE code = ? ORDER BY week_start",
                    [code],
                ).df()

                ctx = build_malf_context_for_stock(code, signal_date, monthly_df, weekly_df)
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
