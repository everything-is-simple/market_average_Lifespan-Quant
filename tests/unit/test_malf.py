"""malf 模块单元测试。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from lq.malf.contracts import (
    MalfContext,
    normalize_monthly_state,
    normalize_weekly_flow,
    build_malf_context_4,
    build_signal_id,
    MONTHLY_STATE_8_VALUES,
    WEEKLY_FLOW_RELATION_VALUES,
)
from lq.malf.monthly import classify_monthly_state
from lq.malf.weekly import classify_weekly_flow


def _make_monthly_df(closes: list[float], start_year: int = 2021) -> pd.DataFrame:
    rows = []
    for i, c in enumerate(closes):
        rows.append({
            "month_start": date(start_year + i // 12, (i % 12) + 1, 1),
            "open": c * 0.98,
            "high": c * 1.02,
            "low": c * 0.97,
            "close": c,
            "volume": 1_000_000,
        })
    return pd.DataFrame(rows)


def _make_weekly_df(closes: list[float]) -> pd.DataFrame:
    rows = []
    from datetime import timedelta
    start = date(2024, 1, 1)
    for i, c in enumerate(closes):
        rows.append({
            "week_start": start + timedelta(weeks=i),
            "open": c * 0.99,
            "high": c * 1.01,
            "low": c * 0.98,
            "close": c,
            "volume": 500_000,
        })
    return pd.DataFrame(rows)


class TestNormalize:
    def test_normalize_monthly_alias(self):
        assert normalize_monthly_state("CONFIRMED_BULL") == "BULL_PERSISTING"
        assert normalize_monthly_state("CONFIRMED_BEAR") == "BEAR_PERSISTING"
        assert normalize_monthly_state("BULL_FORMING") == "BULL_FORMING"

    def test_normalize_weekly_alias(self):
        assert normalize_weekly_flow("MAINSTREAM") == "with_flow"
        assert normalize_weekly_flow("COUNTERTREND") == "against_flow"
        assert normalize_weekly_flow("with_flow") == "with_flow"


class TestBuildMalfContext4:
    def test_bull_mainstream(self):
        assert build_malf_context_4("BULL_PERSISTING", "with_flow") == "BULL_MAINSTREAM"

    def test_bull_countertrend(self):
        assert build_malf_context_4("BULL_PERSISTING", "against_flow") == "BULL_COUNTERTREND"

    def test_bear_mainstream(self):
        assert build_malf_context_4("BEAR_PERSISTING", "with_flow") == "BEAR_MAINSTREAM"

    def test_bear_countertrend(self):
        assert build_malf_context_4("BEAR_PERSISTING", "against_flow") == "BEAR_COUNTERTREND"


class TestMalfContext:
    def test_valid_context(self):
        ctx = MalfContext(
            code="000001.SZ",
            signal_date=date(2024, 6, 1),
            long_background_2="BULL",
            intermediate_role_2="MAINSTREAM",
            malf_context_4="BULL_MAINSTREAM",
            monthly_state="BULL_PERSISTING",
            weekly_flow="with_flow",
        )
        assert ctx.code == "000001.SZ"
        assert ctx.malf_context_4 == "BULL_MAINSTREAM"

    def test_invalid_monthly_state(self):
        with pytest.raises(ValueError, match="非法 monthly_state"):
            MalfContext(
                code="000001.SZ",
                signal_date=date(2024, 6, 1),
                long_background_2="BULL",
                intermediate_role_2="MAINSTREAM",
                malf_context_4="BULL_MAINSTREAM",
                monthly_state="INVALID_STATE",
                weekly_flow="with_flow",
            )

    def test_as_dict(self):
        ctx = MalfContext(
            code="000001.SZ",
            signal_date=date(2024, 6, 1),
            long_background_2="BULL",
            intermediate_role_2="MAINSTREAM",
            malf_context_4="BULL_MAINSTREAM",
            monthly_state="BULL_PERSISTING",
            weekly_flow="with_flow",
            monthly_strength=0.8,
        )
        d = ctx.as_dict()
        assert d["code"] == "000001.SZ"
        assert d["monthly_strength"] == 0.8


class TestClassifyMonthlyState:
    def test_uptrend_returns_bull(self):
        # 递增序列 → 牛市
        closes = list(range(10, 50, 2))  # 20 个月
        df = _make_monthly_df(closes)
        state = classify_monthly_state(df, date(2022, 8, 1))
        assert state.startswith("BULL")

    def test_downtrend_returns_bear(self):
        # 递减序列 → 熊市
        closes = list(range(50, 10, -2))
        df = _make_monthly_df(closes)
        state = classify_monthly_state(df, date(2022, 8, 1))
        assert state.startswith("BEAR")

    def test_empty_df_returns_default(self):
        df = pd.DataFrame()
        state = classify_monthly_state(df, date(2024, 1, 1))
        assert state == "BEAR_FORMING"


class TestClassifyWeeklyFlow:
    def test_uptrend_weekly_bull_context(self):
        # 上升序列 + 牛市背景 → 顺流
        closes = [10 + i * 0.5 for i in range(10)]
        df = _make_weekly_df(closes)
        flow = classify_weekly_flow(df, "BULL_PERSISTING", date(2024, 3, 1))
        assert flow == "with_flow"

    def test_downtrend_weekly_bull_context(self):
        # 下降序列 + 牛市背景 → 逆流
        closes = [20 - i * 0.5 for i in range(10)]
        df = _make_weekly_df(closes)
        flow = classify_weekly_flow(df, "BULL_PERSISTING", date(2024, 3, 1))
        assert flow == "against_flow"

    def test_empty_df_bull_default(self):
        df = pd.DataFrame()
        flow = classify_weekly_flow(df, "BULL_PERSISTING", date(2024, 1, 1))
        assert flow == "with_flow"
