"""结构位检测器 — 从日线 K 线序列中识别关键价格位和突破事件。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lq.core.contracts import StructureLevelType, BreakoutType
from lq.structure.contracts import StructureLevel, BreakoutEvent, StructureSnapshot


# ---------------------------------------------------------------------------
# 参数常量
# ---------------------------------------------------------------------------
PIVOT_LOOKBACK = 5        # 波段高低点识别左右各看几根
LEVEL_CLUSTER_PCT = 0.02  # 两个价格位在 2% 以内视为同一区域（合并）
BREAKOUT_CONFIRM_PCT = 0.01   # 有效突破需要收盘超过结构位 1% 以上
FALSE_BREAKOUT_RECOVER_PCT = 0.005  # 假突破：穿越但收回到结构位 0.5% 以内
MIN_SPACE_PCT = 0.05          # 最小交易空间：支撑到阻力至少 5%
LEVEL_MAX_AGE_DAYS = 120      # 结构位有效期（超过 120 日的结构位强度大幅衰减）


# ---------------------------------------------------------------------------
# 波段高低点识别
# ---------------------------------------------------------------------------

def find_pivot_highs(
    df: pd.DataFrame,
    lookback: int = PIVOT_LOOKBACK,
) -> list[tuple[int, float, date]]:
    """识别波段高点列表（index, price, date）。

    条件：左右各 lookback 根 K 线的最高价都低于该点。
    """
    highs = df["adj_high"].values.astype(float)
    dates = df["date"].values
    pivots: list[tuple[int, float, date]] = []

    for i in range(lookback, len(highs) - lookback):
        left = highs[max(0, i - lookback): i]
        right = highs[i + 1: i + lookback + 1]
        if len(left) == 0 or len(right) == 0:
            continue
        if highs[i] >= max(left) and highs[i] > max(right):
            pivots.append((i, float(highs[i]), pd.Timestamp(dates[i]).date()))

    return pivots


def find_pivot_lows(
    df: pd.DataFrame,
    lookback: int = PIVOT_LOOKBACK,
) -> list[tuple[int, float, date]]:
    """识别波段低点列表（index, price, date）。

    条件：左右各 lookback 根 K 线的最低价都高于该点。
    """
    lows = df["adj_low"].values.astype(float)
    dates = df["date"].values
    pivots: list[tuple[int, float, date]] = []

    for i in range(lookback, len(lows) - lookback):
        left = lows[max(0, i - lookback): i]
        right = lows[i + 1: i + lookback + 1]
        if len(left) == 0 or len(right) == 0:
            continue
        if lows[i] <= min(left) and lows[i] < min(right):
            pivots.append((i, float(lows[i]), pd.Timestamp(dates[i]).date()))

    return pivots


# ---------------------------------------------------------------------------
# 水平关键位聚合
# ---------------------------------------------------------------------------

def _merge_nearby_levels(
    raw_prices: list[tuple[float, date, str]],
    cluster_pct: float = LEVEL_CLUSTER_PCT,
) -> list[tuple[float, date, str, int]]:
    """将接近的价格位合并为同一结构位，返回 (price, formed_date, level_type, touch_count)。"""
    if not raw_prices:
        return []

    sorted_prices = sorted(raw_prices, key=lambda x: x[0])
    merged: list[tuple[float, date, str, int]] = []
    cluster: list[tuple[float, date, str]] = [sorted_prices[0]]

    for item in sorted_prices[1:]:
        base_price = cluster[0][0]
        if abs(item[0] - base_price) / max(abs(base_price), 1e-9) <= cluster_pct:
            cluster.append(item)
        else:
            avg_price = sum(c[0] for c in cluster) / len(cluster)
            earliest_date = min(c[1] for c in cluster)
            lvl_type = cluster[0][2]
            merged.append((avg_price, earliest_date, lvl_type, len(cluster)))
            cluster = [item]

    if cluster:
        avg_price = sum(c[0] for c in cluster) / len(cluster)
        earliest_date = min(c[1] for c in cluster)
        lvl_type = cluster[0][2]
        merged.append((avg_price, earliest_date, lvl_type, len(cluster)))

    return merged


def find_horizontal_levels(
    df: pd.DataFrame,
    signal_date: date,
    max_levels: int = 5,
) -> tuple[list[StructureLevel], list[StructureLevel]]:
    """从日线数据中识别当前有效的水平支撑位和阻力位。

    返回：(support_levels, resistance_levels)，按价格距当前收盘由近到远排序。
    """
    if df.empty or len(df) < PIVOT_LOOKBACK * 2 + 1:
        return [], []

    df = df.sort_values("date").reset_index(drop=True)
    current_close = float(df["adj_close"].iloc[-1])

    # 识别波段高低点
    highs = find_pivot_highs(df)
    lows = find_pivot_lows(df)

    # 构建原始价格列表
    raw_supports: list[tuple[float, date, str]] = [
        (price, dt, StructureLevelType.PIVOT_LOW.value) for _, price, dt in lows
    ]
    raw_resistances: list[tuple[float, date, str]] = [
        (price, dt, StructureLevelType.PIVOT_HIGH.value) for _, price, dt in highs
    ]

    # 合并临近价格位
    merged_supports = _merge_nearby_levels(raw_supports)
    merged_resistances = _merge_nearby_levels(raw_resistances)

    def _to_level(entry: tuple[float, date, str, int], signal_date: date) -> StructureLevel:
        price, formed_date, lvl_type, touch_count = entry
        # 越老的结构位强度越低，触及次数越多强度越高
        age_days = (signal_date - formed_date).days
        age_decay = max(0.1, 1.0 - age_days / LEVEL_MAX_AGE_DAYS)
        touch_bonus = min(0.3, (touch_count - 1) * 0.1)
        strength = float(np.clip(0.5 * age_decay + touch_bonus, 0.0, 1.0))
        return StructureLevel(
            level_type=lvl_type,
            price=price,
            formed_date=formed_date,
            strength=strength,
            touch_count=touch_count,
        )

    # 筛选：支撑位在当前价格下方，阻力位在上方
    supports = sorted(
        [
            _to_level(e, signal_date)
            for e in merged_supports
            if e[0] < current_close
        ],
        key=lambda s: s.price,
        reverse=True,  # 由近到远
    )[:max_levels]

    resistances = sorted(
        [
            _to_level(e, signal_date)
            for e in merged_resistances
            if e[0] > current_close
        ],
        key=lambda r: r.price,  # 由近到远
    )[:max_levels]

    return supports, resistances


# ---------------------------------------------------------------------------
# 突破事件分类
# ---------------------------------------------------------------------------

def classify_breakout_event(
    df: pd.DataFrame,
    level: StructureLevel,
    signal_date: date,
    lookback_days: int = 5,
) -> BreakoutEvent | None:
    """分析最近 lookback_days 日内是否发生了针对该结构位的突破事件。

    突破分类规则：
    - 有效突破：收盘超越结构位 ≥ BREAKOUT_CONFIRM_PCT，随后未回头
    - 假突破 (BOF)：日内穿越结构位但收盘收回，或次日迅速收回
    - 测试 (TST)：接触结构位附近（2% 以内）但未穿越，收回
    - 回踩确认 (BPB/CPB)：有效突破后价格回踩但守住结构位
    """
    if df.empty:
        return None

    df = df.sort_values("date").reset_index(drop=True)
    recent = df[df["date"] <= pd.Timestamp(signal_date)].tail(lookback_days)

    if len(recent) < 2:
        return None

    level_price = level.price
    last = recent.iloc[-1]
    last_date = pd.Timestamp(last["date"]).date()

    adj_low = float(last["adj_low"])
    adj_high = float(last["adj_high"])
    adj_close = float(last["adj_close"])

    # 穿越幅度（相对于结构位）
    if level.is_support:
        penetration = (level_price - adj_low) / max(abs(level_price), 1e-9)
        recovered = adj_close > level_price * (1 - FALSE_BREAKOUT_RECOVER_PCT)
    else:
        penetration = (adj_high - level_price) / max(abs(level_price), 1e-9)
        recovered = adj_close < level_price * (1 + FALSE_BREAKOUT_RECOVER_PCT)

    if penetration <= 0:
        return None   # 未触及结构位，无事件

    # 分类
    if recovered and penetration > 0.005:
        btype = BreakoutType.FALSE_BREAKOUT.value
        notes = f"日内穿越 {penetration:.2%} 但收回，BOF 候选"
    elif penetration <= 0.01:
        btype = BreakoutType.TEST.value
        notes = f"轻触结构位 {penetration:.2%}，TST 候选"
    else:
        # 需要看后续是否回踩
        prev_bars = recent.iloc[:-1]
        had_breakout_before = any(
            float(row["adj_close"]) > level_price * (1 + BREAKOUT_CONFIRM_PCT)
            if level.is_resistance
            else float(row["adj_close"]) < level_price * (1 - BREAKOUT_CONFIRM_PCT)
            for _, row in prev_bars.iterrows()
        )
        if had_breakout_before:
            btype = BreakoutType.PULLBACK_CONFIRMATION.value
            notes = "突破后回踩，BPB/CPB 候选"
        else:
            btype = BreakoutType.VALID_BREAKOUT.value
            notes = f"有效突破幅度 {penetration:.2%}"

    return BreakoutEvent(
        event_date=last_date,
        level=level,
        breakout_type=btype,
        penetration_pct=float(penetration),
        recovered=recovered,
        confirmed=(btype == BreakoutType.VALID_BREAKOUT.value),
        notes=notes,
    )


# ---------------------------------------------------------------------------
# 完整结构快照
# ---------------------------------------------------------------------------

def build_structure_snapshot(
    code: str,
    signal_date: date,
    daily_bars: pd.DataFrame,
) -> StructureSnapshot:
    """为单只股票生成当日完整结构位快照。"""
    supports, resistances = find_horizontal_levels(daily_bars, signal_date)

    # 检查最近的突破事件（针对最近支撑位）
    recent_breakout: BreakoutEvent | None = None
    if supports:
        recent_breakout = classify_breakout_event(
            daily_bars, supports[0], signal_date, lookback_days=5
        )

    return StructureSnapshot(
        code=code,
        signal_date=signal_date,
        support_levels=tuple(supports),
        resistance_levels=tuple(resistances),
        recent_breakout=recent_breakout,
        nearest_support=supports[0] if supports else None,
        nearest_resistance=resistances[0] if resistances else None,
    )
