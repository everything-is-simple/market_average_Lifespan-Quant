"""P0-05 补丁测试：BEAR_FORMING_BLOCK 开关行为。

回归防护：
    BEAR_FORMING_BLOCK=False（默认）时，BEAR_FORMING 背景不应被屏蔽。
    BEAR_FORMING_BLOCK=True 时，BEAR_FORMING 背景应被屏蔽。
"""

from __future__ import annotations

from datetime import date

import pytest
from unittest.mock import patch

from lq.filter.adverse import _check_background_not_supporting
from lq.malf.contracts import MalfContext


def _make_malf(monthly: str, weekly: str = "with_flow") -> MalfContext:
    return MalfContext(
        code="000001.SZ",
        signal_date=date(2024, 6, 3),
        monthly_state=monthly,
        weekly_flow=weekly,
        surface_label=f"{monthly}_{weekly}",
    )


class TestBearFormingBlock:
    def test_default_false_bear_forming_is_allowed(self):
        """默认 BEAR_FORMING_BLOCK=False 时，BEAR_FORMING 背景不应触发屏蔽。"""
        ctx = _make_malf("BEAR_FORMING")
        with patch("lq.filter.adverse.BEAR_FORMING_BLOCK", False):
            result = _check_background_not_supporting(ctx)
        assert result is False, "BEAR_FORMING_BLOCK=False 时 BEAR_FORMING 应允许入场"

    def test_true_bear_forming_is_blocked(self):
        """BEAR_FORMING_BLOCK=True 时，BEAR_FORMING 背景应触发屏蔽。"""
        ctx = _make_malf("BEAR_FORMING")
        with patch("lq.filter.adverse.BEAR_FORMING_BLOCK", True):
            result = _check_background_not_supporting(ctx)
        assert result is True, "BEAR_FORMING_BLOCK=True 时 BEAR_FORMING 应屏蔽入场"

    def test_bear_persisting_always_blocked(self):
        """BEAR_PERSISTING 不受 BEAR_FORMING_BLOCK 影响，始终屏蔽。"""
        ctx = _make_malf("BEAR_PERSISTING")
        with patch("lq.filter.adverse.BEAR_PERSISTING_BLOCK", True):
            result = _check_background_not_supporting(ctx)
        assert result is True

    def test_bull_persisting_never_blocked(self):
        """牛市背景不受任何背景开关影响，始终允许。"""
        ctx = _make_malf("BULL_PERSISTING")
        result = _check_background_not_supporting(ctx)
        assert result is False
