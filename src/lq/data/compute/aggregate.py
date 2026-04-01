"""data.compute.aggregate — 后复权日线 → 周线 / 月线聚合。

聚合规则（冻结）：
  open   — 周/月第一个交易日的 open
  high   — max(high)
  low    — min(low)
  close  — 周/月最后一个交易日的 close
  volume — sum(volume)
  amount — sum(amount)
  trade_date        — 周/月最后一个交易日
  week_start_date   — 周第一个交易日
  month_start_date  — 月第一个交易日
"""

from __future__ import annotations

from datetime import date

import pandas as pd


def _iso_week_key(d: date) -> str:
    """返回 ISO 周键 'YYYY-WW'，用于分组。"""
    iso = d.isocalendar()
    return f"{iso[0]:04d}-{iso[1]:02d}"


def _month_key(d: date) -> str:
    """返回月键 'YYYY-MM'，用于分组。"""
    return f"{d.year:04d}-{d.month:02d}"


def aggregate_to_weekly(daily_adj: pd.DataFrame) -> pd.DataFrame:
    """将后复权日线聚合为周线。

    参数：
        daily_adj — stock_daily_adjusted 的 DataFrame，必须含
                    ['code', 'trade_date', 'open', 'high', 'low', 'close',
                     'volume', 'amount', 'adjust_method']

    返回：
        DataFrame，列与 stock_weekly_adjusted schema 对应。
    """
    if daily_adj.empty:
        return pd.DataFrame()

    df = daily_adj.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df = df.sort_values("trade_date").reset_index(drop=True)

    code = str(df["code"].iloc[0])
    adjust_method = str(df["adjust_method"].iloc[0])

    df["week_key"] = df["trade_date"].apply(_iso_week_key)

    weekly_rows: list[dict] = []
    for wk, grp in df.groupby("week_key", sort=True):
        grp_sorted = grp.sort_values("trade_date")
        weekly_rows.append({
            "code":             code,
            "trade_date":       grp_sorted["trade_date"].iloc[-1],    # 周最后交易日
            "week_start_date":  grp_sorted["trade_date"].iloc[0],     # 周第一交易日
            "adjust_method":    adjust_method,
            "open":             round(float(grp_sorted["open"].iloc[0]), 4),
            "high":             round(float(grp_sorted["high"].max()), 4),
            "low":              round(float(grp_sorted["low"].min()), 4),
            "close":            round(float(grp_sorted["close"].iloc[-1]), 4),
            "volume":           float(grp_sorted["volume"].sum()),
            "amount":           float(grp_sorted["amount"].sum()),
        })

    return pd.DataFrame(weekly_rows)


def aggregate_to_monthly(daily_adj: pd.DataFrame) -> pd.DataFrame:
    """将后复权日线聚合为月线。

    参数：
        daily_adj — stock_daily_adjusted 的 DataFrame，必须含
                    ['code', 'trade_date', 'open', 'high', 'low', 'close',
                     'volume', 'amount', 'adjust_method']

    返回：
        DataFrame，列与 stock_monthly_adjusted schema 对应。
    """
    if daily_adj.empty:
        return pd.DataFrame()

    df = daily_adj.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
    df = df.sort_values("trade_date").reset_index(drop=True)

    code = str(df["code"].iloc[0])
    adjust_method = str(df["adjust_method"].iloc[0])

    df["month_key"] = df["trade_date"].apply(_month_key)

    monthly_rows: list[dict] = []
    for mk, grp in df.groupby("month_key", sort=True):
        grp_sorted = grp.sort_values("trade_date")
        monthly_rows.append({
            "code":              code,
            "trade_date":        grp_sorted["trade_date"].iloc[-1],   # 月最后交易日
            "month_start_date":  grp_sorted["trade_date"].iloc[0],    # 月第一交易日
            "adjust_method":     adjust_method,
            "open":              round(float(grp_sorted["open"].iloc[0]), 4),
            "high":              round(float(grp_sorted["high"].max()), 4),
            "low":               round(float(grp_sorted["low"].min()), 4),
            "close":             round(float(grp_sorted["close"].iloc[-1]), 4),
            "volume":            float(grp_sorted["volume"].sum()),
            "amount":            float(grp_sorted["amount"].sum()),
        })

    return pd.DataFrame(monthly_rows)
