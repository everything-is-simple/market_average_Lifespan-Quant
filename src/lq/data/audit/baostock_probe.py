"""data.audit.baostock_probe — BaoStock 第二校准源探针。

角色定位（继承父系统 138/139 号卡冻结口径）：
  - BaoStock 是第二校准源 / fallback，不参与主链 L2 构建
  - 仅用于审计：对比 BaoStock adj_factor 与本地计算的 adjustment_factor
  - 差异结果写入 temp 目录，不反写正式五库

探针模式：
  probe_adjustment_factor_diff()  — 对比复权因子差异（主要审计点）
  probe_dividend_diff()           — 对比分红数据差异

五类事件规则（139 号卡）：
  category 1: provisional_dual_source_comparable_with_mild_drift_watch
  category 2: conditional_comparable_with_mild_drift_watch
  category 3: stable_baostock_boundary_use_tushare_fill
  category 5: boundary_fill_with_mild_drift_watch
  category 9: holdout_pending_factor_path_resolution
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


# 139 号卡冻结的五类事件规则表
BAOSTOCK_DUAL_SOURCE_RULES: dict[int, str] = {
    1: "provisional_dual_source_comparable_with_mild_drift_watch",
    2: "conditional_comparable_with_mild_drift_watch",
    3: "stable_baostock_boundary_use_tushare_fill",
    5: "boundary_fill_with_mild_drift_watch",
    9: "holdout_pending_factor_path_resolution",
}

# 允许的复权因子最大差异阈值（比例）
FACTOR_DIFF_THRESHOLD = 0.005   # 0.5%，继承父系统 135 号卡基线


@dataclass
class AdjFactorDiffRow:
    """单只股票单个交易日的复权因子差异记录。"""

    code: str
    trade_date: date
    local_factor: float    # 本地从 gbbq 计算的 adjustment_factor
    baostock_factor: float # BaoStock 返回的 adj_factor
    diff_ratio: float      # abs(local - baostock) / baostock
    exceeds_threshold: bool
    category: int | None   # 对应的 xdxr event category（若可映射）


def probe_adjustment_factor_diff(
    codes: list[str],
    market_base_path: Path,
    baostock_provider,           # BaoStockProvider 实例（来自 providers/baostock.py）
    window_start: date | None = None,
    window_end: date | None = None,
) -> pd.DataFrame:
    """对比本地复权因子与 BaoStock adj_factor 的差异。

    参数：
        codes              — 待审计的股票代码列表
        market_base_path   — market_base.duckdb 路径（读取本地 adjustment_factor）
        baostock_provider  — BaoStockProvider 实例
        window_start       — 审计窗口起始日
        window_end         — 审计窗口终止日

    返回：
        DataFrame，列为 [code, trade_date, local_factor, baostock_factor,
                         diff_ratio, exceeds_threshold]。
        只包含差异 > 0 的行。
    """
    import duckdb

    diff_rows: list[dict] = []

    with duckdb.connect(str(market_base_path), read_only=True) as conn:
        for code in codes:
            # 读取本地计算的 adjustment_factor
            params: list = [code]
            where_extra = ""
            if window_start:
                where_extra += " AND trade_date >= ?"
                params.append(window_start)
            if window_end:
                where_extra += " AND trade_date <= ?"
                params.append(window_end)

            local_df: pd.DataFrame = conn.execute(
                f"SELECT trade_date, adjustment_factor FROM stock_daily_adjusted "
                f"WHERE code = ? AND adjust_method = 'backward'{where_extra} "
                f"ORDER BY trade_date",
                params,
            ).df()

            if local_df.empty:
                continue

            # 从 BaoStock 获取 adj_factor
            try:
                bs_df = baostock_provider.get_adjust_factor(
                    code=code,
                    start_date=str(window_start or local_df["trade_date"].min()),
                    end_date=str(window_end or local_df["trade_date"].max()),
                )
            except Exception:
                continue

            if bs_df is None or bs_df.empty:
                continue

            # 对齐 trade_date 进行 diff
            merged = local_df.merge(
                bs_df[["trade_date", "adj_factor"]].rename(
                    columns={"adj_factor": "baostock_factor"}
                ),
                on="trade_date",
                how="inner",
            )
            if merged.empty:
                continue

            merged["diff_ratio"] = (
                (merged["adjustment_factor"] - merged["baostock_factor"]).abs()
                / merged["baostock_factor"].clip(lower=1e-9)
            )
            # 只保留有差异的行
            diff_only = merged[merged["diff_ratio"] > 1e-6].copy()
            diff_only["code"] = code
            diff_only["exceeds_threshold"] = diff_only["diff_ratio"] > FACTOR_DIFF_THRESHOLD
            diff_only = diff_only.rename(
                columns={"adjustment_factor": "local_factor"}
            )
            diff_rows.append(
                diff_only[
                    ["code", "trade_date", "local_factor", "baostock_factor",
                     "diff_ratio", "exceeds_threshold"]
                ]
            )

    if not diff_rows:
        return pd.DataFrame(
            columns=["code", "trade_date", "local_factor", "baostock_factor",
                     "diff_ratio", "exceeds_threshold"]
        )

    return pd.concat(diff_rows, ignore_index=True)


def summarize_diff_report(diff_df: pd.DataFrame) -> dict:
    """生成差异汇总报告（控制台输出用）。"""
    if diff_df.empty:
        return {
            "total_diff_records": 0,
            "exceeds_threshold_count": 0,
            "codes_with_breach": [],
        }
    breaches = diff_df[diff_df["exceeds_threshold"]]
    return {
        "total_diff_records": len(diff_df),
        "exceeds_threshold_count": len(breaches),
        "codes_with_breach": sorted(breaches["code"].unique().tolist()),
        "max_diff_ratio": float(diff_df["diff_ratio"].max()),
        "p95_diff_ratio": float(diff_df["diff_ratio"].quantile(0.95)),
    }
