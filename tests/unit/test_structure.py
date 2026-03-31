"""structure 模块单元测试 — 统一结构位合同与突破家族语义。"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from lq.core.contracts import StructureLevelType, BreakoutType
from lq.structure.contracts import StructureLevel, BreakoutEvent, StructureSnapshot
from lq.structure.detector import (
    find_pivot_highs,
    find_pivot_lows,
    find_horizontal_levels,
    classify_breakout_event,
    build_structure_snapshot,
)


def _make_daily_df(prices: list[float], start: date | None = None) -> pd.DataFrame:
    """生成简单的日线测试数据。"""
    if start is None:
        start = date(2024, 1, 2)
    rows = []
    for i, p in enumerate(prices):
        d = start + timedelta(days=i)
        rows.append({
            "date": d,
            "adj_open": p * 0.99,
            "adj_high": p * 1.02,
            "adj_low": p * 0.97,
            "adj_close": p,
            "volume": 1_000_000,
            "volume_ma20": 900_000,
        })
    return pd.DataFrame(rows)


def _make_volatile_df() -> pd.DataFrame:
    """生成包含明显高低点的测试数据。"""
    # 构造：上涨 → 高点 → 下跌 → 低点 → 上涨
    prices = (
        [10, 11, 12, 13, 14, 15, 14, 13, 12]  # 上升后下降（高点在 index 5）
        + [11, 10, 9, 10, 11, 12]  # 下降后上升（低点在 index 11）
        + [13, 14, 15, 16, 17]  # 继续上升
    )
    return _make_daily_df(prices)


class TestStructureLevel:
    def test_valid_support_level(self):
        level = StructureLevel(
            level_type=StructureLevelType.SUPPORT.value,
            price=10.5,
            formed_date=date(2024, 1, 5),
            strength=0.7,
        )
        assert level.is_support is True
        assert level.is_resistance is False

    def test_valid_resistance_level(self):
        level = StructureLevel(
            level_type=StructureLevelType.RESISTANCE.value,
            price=15.0,
            formed_date=date(2024, 1, 5),
            strength=0.6,
        )
        assert level.is_resistance is True
        assert level.is_support is False

    def test_invalid_level_type(self):
        with pytest.raises(ValueError, match="非法 level_type"):
            StructureLevel(
                level_type="INVALID_TYPE",
                price=10.0,
                formed_date=date(2024, 1, 1),
                strength=0.5,
            )

    def test_invalid_strength(self):
        with pytest.raises(ValueError, match="strength 须在 0~1"):
            StructureLevel(
                level_type=StructureLevelType.SUPPORT.value,
                price=10.0,
                formed_date=date(2024, 1, 1),
                strength=1.5,  # 超出范围
            )

    def test_as_dict(self):
        level = StructureLevel(
            level_type=StructureLevelType.PIVOT_LOW.value,
            price=9.8,
            formed_date=date(2024, 2, 1),
            strength=0.8,
            touch_count=3,
        )
        d = level.as_dict()
        assert d["price"] == 9.8
        assert d["touch_count"] == 3
        assert d["formed_date"] == "2024-02-01"


class TestFindPivotPoints:
    def test_find_pivot_highs(self):
        df = _make_volatile_df()
        highs = find_pivot_highs(df, lookback=2)
        # 应该至少找到一个高点
        assert len(highs) > 0
        # 每个高点的价格应大于邻近点
        for idx, price, dt in highs:
            assert isinstance(dt, date)
            assert price > 0

    def test_find_pivot_lows(self):
        df = _make_volatile_df()
        lows = find_pivot_lows(df, lookback=2)
        assert len(lows) > 0
        for idx, price, dt in lows:
            assert isinstance(dt, date)
            assert price > 0

    def test_monotonic_uptrend_no_pivot_low(self):
        # 单调上升 → 没有波段低点（除了边界外）
        df = _make_daily_df(list(range(10, 30)))
        lows = find_pivot_lows(df, lookback=3)
        # 单调上升不应有中间低点
        assert len(lows) == 0


class TestFindHorizontalLevels:
    def test_returns_support_below_close(self):
        df = _make_volatile_df()
        signal_date = df["date"].max()
        supports, resistances = find_horizontal_levels(df, signal_date)
        current_close = float(df["adj_close"].iloc[-1])
        for s in supports:
            assert s.price < current_close * 1.05  # 支撑位应在当前价下方

    def test_returns_resistance_above_close(self):
        df = _make_volatile_df()
        signal_date = df["date"].max()
        supports, resistances = find_horizontal_levels(df, signal_date)
        current_close = float(df["adj_close"].iloc[-1])
        for r in resistances:
            assert r.price > current_close * 0.95  # 阻力位应在当前价上方

    def test_empty_df_returns_empty(self):
        df = pd.DataFrame()
        supports, resistances = find_horizontal_levels(df, date(2024, 1, 1))
        assert supports == []
        assert resistances == []


class TestStructureSnapshot:
    def test_has_clear_structure(self):
        df = _make_volatile_df()
        signal_date = df["date"].max()
        snap = build_structure_snapshot("000001.SZ", signal_date, df)
        assert isinstance(snap, StructureSnapshot)
        assert snap.code == "000001.SZ"

    def test_available_space_calculation(self):
        support = StructureLevel(
            level_type=StructureLevelType.SUPPORT.value,
            price=10.0,
            formed_date=date(2024, 1, 1),
            strength=0.7,
        )
        resistance = StructureLevel(
            level_type=StructureLevelType.RESISTANCE.value,
            price=12.0,
            formed_date=date(2024, 1, 1),
            strength=0.6,
        )
        snap = StructureSnapshot(
            code="TEST",
            signal_date=date(2024, 1, 10),
            support_levels=(support,),
            resistance_levels=(resistance,),
            recent_breakout=None,
            nearest_support=support,
            nearest_resistance=resistance,
        )
        space = snap.available_space_pct
        assert space is not None
        # (12 - 10) / 11 ≈ 18%
        assert abs(space - 2.0 / 11.0) < 0.01
