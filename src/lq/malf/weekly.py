"""MALF 周线背景分析 — weekly_flow_relation_to_monthly。

周线顺逆判定规则：
    with_flow     — 周线运动方向与月线主趋势一致（顺流）
    against_flow  — 周线运动方向与月线主趋势相反（逆流/回调）
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd


# 周线顺逆判定参数
WEEKLY_MA_PERIOD = 5         # 用于判断周线方向的均线周期（周数）
WEEKLY_SLOPE_THRESHOLD = 0.0 # 斜率阈值（正为向上，负为向下）


def classify_weekly_flow(
    weekly_bars: pd.DataFrame,
    monthly_state: str,
    asof_date: date,
    lookback_weeks: int = 8,
) -> str:
    """根据周线数据与月线状态判定周线顺逆关系。

    参数：
        weekly_bars   — 包含 [week_start, close, high, low] 的周线 DataFrame
        monthly_state — 当前月线八态字符串
        asof_date     — 判断截止日（含当周）
        lookback_weeks — 回看周数

    返回：
        "with_flow" 或 "against_flow"
    """
    if weekly_bars.empty:
        # 无数据时根据月线状态给默认值
        return "with_flow" if monthly_state.startswith("BULL") else "against_flow"

    df = weekly_bars[weekly_bars["week_start"] <= asof_date].copy()
    df = df.sort_values("week_start").tail(lookback_weeks).reset_index(drop=True)

    if len(df) < 2:
        return "with_flow" if monthly_state.startswith("BULL") else "against_flow"

    closes = df["close"].values.astype(float)

    # 近 WEEKLY_MA_PERIOD 周的均线斜率（线性回归）
    n = min(WEEKLY_MA_PERIOD, len(closes))
    recent = closes[-n:]
    x = np.arange(n, dtype=float)
    if n > 1:
        slope = float(np.polyfit(x, recent, 1)[0])
    else:
        slope = 0.0

    is_bull_monthly = monthly_state.startswith("BULL")

    # 牛市背景下：向上为顺流，向下为逆流
    # 熊市背景下：向下为顺流，向上为逆流
    if is_bull_monthly:
        return "with_flow" if slope > WEEKLY_SLOPE_THRESHOLD else "against_flow"
    else:
        return "with_flow" if slope <= WEEKLY_SLOPE_THRESHOLD else "against_flow"


def compute_weekly_strength(
    weekly_bars: pd.DataFrame,
    asof_date: date,
    lookback_weeks: int = 8,
) -> float:
    """计算周线强度得分 0~1（当前收盘在近期区间的分位）。"""
    if weekly_bars.empty:
        return 0.5

    df = weekly_bars[weekly_bars["week_start"] <= asof_date].copy()
    df = df.sort_values("week_start").tail(lookback_weeks).reset_index(drop=True)

    if len(df) < 2:
        return 0.5

    closes = df["close"].values.astype(float)
    low_n = float(np.min(closes))
    high_n = float(np.max(closes))

    if abs(high_n - low_n) < 1e-9:
        return 0.5

    return float(np.clip((closes[-1] - low_n) / (high_n - low_n), 0.0, 1.0))
