"""filter 模块单元测试 — 不利市场条件过滤器。"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from lq.core.contracts import AdverseConditionType
from lq.filter.adverse import (
    check_adverse_conditions,
    is_tradeable,
    _check_compression_no_direction,
    _check_structural_chaos,
    _check_insufficient_space,
    _check_background_not_supporting,
)
from lq.malf.contracts import MalfContext


def _make_df(prices: list[float], vol_ratios: list[float] | None = None) -> pd.DataFrame:
    start = date(2024, 1, 2)
    rows = []
    for i, p in enumerate(prices):
        vol = (vol_ratios[i] if vol_ratios else 1.0) * 1_000_000
        rows.append({
            "date": start + timedelta(days=i),
            "adj_open": p * 0.99,
            "adj_high": p * 1.02,
            "adj_low": p * 0.98,
            "adj_close": p,
            "volume": int(vol),
            "volume_ma20": 1_000_000,
        })
    return pd.DataFrame(rows)


def _make_compressed_df(n: int = 30) -> pd.DataFrame:
    """构造"压缩且无方向"的行情数据。

    前 20 日用宽幅振荡（2% 振幅），后 10 日压缩至极小振幅（0.1%），
    价格走平，满足 recent_range < long_range * 0.5 AND flat_slope 两个条件。
    """
    rows = []
    start = date(2024, 1, 2)
    for i in range(n):
        p = 10.0  # 全程价格走平（确保斜率为 0）
        if i < n - 10:
            # 旧的区间：较大振幅（2%）
            high = p * 1.02
            low = p * 0.98
        else:
            # 近期区间：极小振幅（0.1%），触发压缩条件
            high = p * 1.001
            low = p * 0.999
        rows.append({
            "date": start + timedelta(days=i),
            "adj_open": p,
            "adj_high": high,
            "adj_low": low,
            "adj_close": p,
            "volume": 1_000_000,
            "volume_ma20": 1_000_000,
        })
    return pd.DataFrame(rows)


def _make_chaotic_df(n: int = 20) -> pd.DataFrame:
    """构造方向频繁切换的行情数据。"""
    prices = []
    for i in range(n):
        prices.append(10.0 + (1 if i % 2 == 0 else -1) * 0.5)  # 交替涨跌
    return _make_df(prices)


def _make_malf_ctx(monthly_state: str, weekly_flow: str = "with_flow") -> MalfContext:
    return MalfContext(
        code="000001.SZ",
        signal_date=date(2024, 6, 1),
        monthly_state=monthly_state,
        weekly_flow=weekly_flow,
        surface_label="BULL_MAINSTREAM",
    )


class TestCompressionCheck:
    def test_normal_trending_not_compressed(self):
        prices = [10 + i * 0.2 for i in range(30)]  # 正常上涨
        df = _make_df(prices)
        assert _check_compression_no_direction(df) is False

    def test_compressed_flat_detected(self):
        df = _make_compressed_df(30)
        result = _check_compression_no_direction(df)
        # 极小振幅 + 走平 → 压缩
        assert result is True

    def test_insufficient_data_returns_false(self):
        df = _make_df([10.0, 10.1])
        assert _check_compression_no_direction(df) is False


class TestChaosCheck:
    def test_chaotic_signal_detected(self):
        df = _make_chaotic_df(20)
        assert _check_structural_chaos(df) is True

    def test_trending_not_chaotic(self):
        prices = [10 + i * 0.1 for i in range(20)]
        df = _make_df(prices)
        assert _check_structural_chaos(df) is False


class TestSpaceCheck:
    def test_sufficient_space(self):
        # 支撑10，阻力12，当价11 → 空间 18%，超过5%
        assert _check_insufficient_space(10.0, 12.0, 11.0) is False

    def test_insufficient_space(self):
        # 支撑10，阻力10.2，当价10.1 → 空间 2%，不足5%
        assert _check_insufficient_space(10.0, 10.2, 10.1) is True

    def test_none_levels(self):
        assert _check_insufficient_space(None, None, 10.0) is False


class TestBackgroundCheck:
    def test_bear_persisting_blocks(self):
        ctx = _make_malf_ctx("BEAR_PERSISTING")
        assert _check_background_not_supporting(ctx) is True

    def test_bull_persisting_allows(self):
        ctx = _make_malf_ctx("BULL_PERSISTING")
        assert _check_background_not_supporting(ctx) is False

    def test_none_ctx_allows(self):
        assert _check_background_not_supporting(None) is False


class TestCheckAdverseConditions:
    def test_clean_trending_returns_tradeable(self):
        prices = [10 + i * 0.2 for i in range(30)]
        df = _make_df(prices)
        ctx = _make_malf_ctx("BULL_PERSISTING", "with_flow")
        result = check_adverse_conditions(
            code="000001.SZ",
            signal_date=date(2024, 2, 1),
            daily_bars=df,
            malf_ctx=ctx,
        )
        assert result.tradeable is True
        assert len(result.active_conditions) == 0

    def test_bear_persisting_not_tradeable(self):
        prices = [10 + i * 0.1 for i in range(30)]
        df = _make_df(prices)
        ctx = _make_malf_ctx("BEAR_PERSISTING")
        result = check_adverse_conditions(
            code="000001.SZ",
            signal_date=date(2024, 2, 1),
            daily_bars=df,
            malf_ctx=ctx,
        )
        assert result.tradeable is False
        assert AdverseConditionType.BACKGROUND_NOT_SUPPORTING.value in result.active_conditions

    def test_is_tradeable_shortcut(self):
        prices = [10 + i * 0.2 for i in range(30)]
        df = _make_df(prices)
        ctx = _make_malf_ctx("BULL_PERSISTING")
        assert is_tradeable("000001.SZ", date(2024, 2, 1), df, ctx) is True
