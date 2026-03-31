"""MALF 日线节奏分析 — 新高日序列计数。

核心思想（立花义正「新高日」观点）：
    一段行情最值钱的部分集中在新高日。
    行情初期新高日密集出现，说明趋势活力充沛。
    行情末端新高越来越难出现，新高日间距持续放大，是趋势衰竭的早期信号。

本模块只做计算，不做触发决策。触发决策属于 alpha/pas 模块。
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd

# 默认判断新高的回看窗口（交易日数）：过去 N 日收盘价最大值
DEFAULT_NEW_HIGH_LOOKBACK: int = 20

# 默认统计新高序列的窗口长度（交易日数）
DEFAULT_WINDOW_DAYS: int = 60


def compute_daily_rhythm(
    daily_bars: pd.DataFrame,
    asof_date: date,
    lookback_days: int = DEFAULT_NEW_HIGH_LOOKBACK,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict:
    """计算日线节奏指标（新高日系列）。

    参数：
        daily_bars   — 包含 ['trade_date', 'close'] 列的日线 DataFrame
                       trade_date 必须为 Python date 类型（或可比较类型）
        asof_date    — 截止日期（含），只计算 <= asof_date 的数据
        lookback_days — 判定新高的回看窗口，当日 close > 过去 N 日所有 close 即为新高日
        window_days  — 统计新高序列的滑动窗口长度

    返回 dict，含以下字段：
        is_new_high_today       : bool  — 当日是否为新高日
        new_high_seq            : int   — 当日是 window_days 内第几个新高日（0 = 非新高日）
        days_since_last_new_high: int | None — 距上一个新高日的交易日间距
                                               None 表示历史内无新高日
        new_high_count_in_window: int   — window_days 内新高日总数量
    """
    if daily_bars is None or daily_bars.empty:
        return _empty_rhythm()

    # 只取 asof_date 及以前的数据，取足够长的历史以支撑 lookback
    df = (
        daily_bars[daily_bars["trade_date"] <= asof_date]
        .copy()
        .sort_values("trade_date")
        .tail(window_days + lookback_days)
        .reset_index(drop=True)
    )

    if len(df) < 2:
        return _empty_rhythm()

    closes = df["close"].values.astype(float)
    n = len(closes)

    # 逐日判断是否创 lookback_days 新高
    is_new_high_arr = np.zeros(n, dtype=bool)
    for i in range(1, n):
        start = max(0, i - lookback_days)
        prior_max = float(np.max(closes[start:i]))
        is_new_high_arr[i] = closes[i] > prior_max

    # 当日是否为新高日
    is_new_high_today = bool(is_new_high_arr[-1])

    # 取 window_days 范围内的新高序列
    window_start_idx = max(0, n - window_days)
    recent_is_new_high = is_new_high_arr[window_start_idx:]
    new_high_count_in_window = int(np.sum(recent_is_new_high))

    # 当日在 window 内是第几个新高（0 表示今日非新高日）
    if is_new_high_today:
        new_high_seq = int(np.sum(recent_is_new_high))
    else:
        new_high_seq = 0

    # 计算距上一个新高日的间距
    all_new_high_indices = np.where(is_new_high_arr)[0]
    days_since_last_new_high: Optional[int]

    if len(all_new_high_indices) == 0:
        # 历史内从未出现新高日
        days_since_last_new_high = None
    elif is_new_high_today:
        # 今日本身是新高日，间距指与上上一个新高日的距离
        if len(all_new_high_indices) >= 2:
            prev_idx = all_new_high_indices[-2]
            days_since_last_new_high = (n - 1) - prev_idx
        else:
            # 历史只有今天这一个新高日，无前序可比
            days_since_last_new_high = None
    else:
        # 今日非新高日，计算距最近一次新高日有多少交易日
        last_idx = all_new_high_indices[-1]
        days_since_last_new_high = (n - 1) - last_idx

    return {
        "is_new_high_today": is_new_high_today,
        "new_high_seq": new_high_seq,
        "days_since_last_new_high": days_since_last_new_high,
        "new_high_count_in_window": new_high_count_in_window,
    }


def _empty_rhythm() -> dict:
    """数据不足时的空结果，确保调用方永远拿到合规结构。"""
    return {
        "is_new_high_today": False,
        "new_high_seq": 0,
        "days_since_last_new_high": None,
        "new_high_count_in_window": 0,
    }
