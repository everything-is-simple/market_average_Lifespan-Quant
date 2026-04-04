"""MALF 月线背景分析 — monthly_state_8 状态机。

月线八态判定规则：
    BULL_FORMING     — 宽基指数从历史低点反弹 ≥ 20%，牛市起步阶段
    BULL_PERSISTING  — 牛市主升浪，价格持续创新高
    BULL_EXHAUSTING  — 牛市高位，涨速放缓，顶部信号累积
    BULL_REVERSING   — 牛市明确转折，宽基指数从高点回撤 ≥ 20%
    BEAR_FORMING     — 熊市初期，趋势刚刚向下确认
    BEAR_PERSISTING  — 熊市主跌浪，价格持续创新低
    BEAR_EXHAUSTING  — 熊市末期，跌速放缓，底部信号累积
    BEAR_REVERSING   — 熊市明确转折，进入下一轮 BULL_FORMING
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from lq.malf.contracts import (
    MONTHLY_LONG_BULL_REVERSAL_PCT,
    MONTHLY_LONG_BEAR_REVERSAL_PCT,
    MONTHLY_LONG_BULL_MIN_DURATION_MONTHS,
    MONTHLY_LONG_BEAR_MIN_DURATION_MONTHS,
    MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT,
    MONTHLY_LONG_BEAR_MIN_AMPLITUDE_PCT,
    MONTHLY_LONG_EXHAUSTION_RATIO,
    MONTHLY_LONG_MIN_BAR_COUNT,
)


def _safe_pct_change(new_val: float, old_val: float) -> float:
    """安全计算百分比变化，避免除零。"""
    if abs(old_val) < 1e-9:
        return 0.0
    return (new_val - old_val) / abs(old_val)


def classify_monthly_state(
    monthly_bars: pd.DataFrame,
    asof_date: date,
    lookback_months: int = 36,
) -> str:
    """根据月线 K 线数据判定 monthly_state_8。

    参数：
        monthly_bars  — 包含 [month_start, close, high, low, volume] 的月线 DataFrame；
                        若含 trade_date 列（月最后交易日），则用 trade_date <= asof_date
                        截断（正确语义）；否则回退到 month_start <= asof_date（向后兼容）
        asof_date     — 判断截止日（含当月）
        lookback_months — 回看月数

    返回：
        monthly_state_8 字符串值
    """
    if monthly_bars.empty:
        return "BEAR_FORMING"   # 无数据时默认保守状态

    # 用 trade_date（月末日）截断可避免月中扫描纳入未来收盘；无该列时向后兼容
    # pd.to_datetime() 屏蔽 DuckDB datetime64[us/ns] 与 Python date 的类型差异
    _cutoff_col = "trade_date" if "trade_date" in monthly_bars.columns else "month_start"
    _cutoff_ts = pd.Timestamp(asof_date)
    df = monthly_bars[pd.to_datetime(monthly_bars[_cutoff_col]) <= _cutoff_ts].copy()
    df = df.sort_values("month_start").tail(lookback_months).reset_index(drop=True)

    if len(df) < MONTHLY_LONG_MIN_BAR_COUNT:
        return "BEAR_FORMING"

    closes = df["close"].values.astype(float)
    current_close = closes[-1]
    recent_high = float(np.max(closes[-12:]))  # 近12月高点
    recent_low = float(np.min(closes[-12:]))   # 近12月低点
    all_time_low = float(np.min(closes))

    # 从历史低点反弹幅度（判断 BULL_FORMING）
    rebound_from_low = _safe_pct_change(current_close, all_time_low)

    # 从近12月高点回撤幅度（判断 BULL_REVERSING）
    drawdown_from_high = _safe_pct_change(current_close, recent_high)

    # 近12月总振幅
    amplitude = _safe_pct_change(recent_high, recent_low)

    # 最近6个月均线方向
    if len(closes) >= 6:
        ma6_direction = closes[-1] > closes[-6]
    else:
        ma6_direction = closes[-1] > closes[0]

    # 最近3个月涨速是否放缓（与前3个月比较）
    if len(closes) >= 6:
        recent_gain = _safe_pct_change(closes[-1], closes[-4])
        earlier_gain = _safe_pct_change(closes[-4], closes[-7] if len(closes) >= 7 else closes[0])
        speed_slowing = abs(recent_gain) < abs(earlier_gain) * MONTHLY_LONG_EXHAUSTION_RATIO
    else:
        speed_slowing = False

    # 状态判定逻辑（简化规则，可替换为更精细的状态机）
    if ma6_direction:
        # 上升趋势方向
        if rebound_from_low >= MONTHLY_LONG_BULL_REVERSAL_PCT and amplitude >= MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT / 100:
            if speed_slowing:
                return "BULL_EXHAUSTING"
            return "BULL_PERSISTING"
        elif rebound_from_low >= MONTHLY_LONG_BULL_REVERSAL_PCT:
            # 方向向上 + 反弹幅度达标，但总振幅还不够 → 牛市初期成型阶段
            return "BULL_FORMING"
        else:
            # 方向向上但反弹幅度不足 → 熊市末期开始反弹，BEAR_REVERSING
            return "BEAR_REVERSING"
    else:
        # 下降趋势方向
        if drawdown_from_high <= -MONTHLY_LONG_BEAR_REVERSAL_PCT:
            if speed_slowing:
                return "BEAR_EXHAUSTING"
            return "BEAR_PERSISTING"
        elif drawdown_from_high < 0 and amplitude >= MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT / 100:
            # 方向向下 + 从高点有回落 + 近期振幅达标（说明此前确实有过牛市行情）
            # → 牛市明确转折向下
            return "BULL_REVERSING"
        else:
            return "BEAR_FORMING"


def compute_monthly_strength(
    monthly_bars: pd.DataFrame,
    asof_date: date,
    lookback_months: int = 12,
) -> float:
    """计算月线强度得分 0~1（当前状态在历史分位中的位置）。"""
    if monthly_bars.empty:
        return 0.5

    # pd.to_datetime() 屏蔽 DuckDB datetime64[us/ns] 与 Python date 的类型差异
    _cutoff_col = "trade_date" if "trade_date" in monthly_bars.columns else "month_start"
    _cutoff_ts = pd.Timestamp(asof_date)
    df = monthly_bars[pd.to_datetime(monthly_bars[_cutoff_col]) <= _cutoff_ts].copy()
    df = df.sort_values("month_start").tail(lookback_months + 1).reset_index(drop=True)

    if len(df) < 2:
        return 0.5

    closes = df["close"].values.astype(float)
    current = closes[-1]
    low_n = float(np.min(closes))
    high_n = float(np.max(closes))

    if abs(high_n - low_n) < 1e-9:
        return 0.5

    return float(np.clip((current - low_n) / (high_n - low_n), 0.0, 1.0))
