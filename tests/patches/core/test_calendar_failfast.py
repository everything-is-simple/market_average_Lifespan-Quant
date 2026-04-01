"""P2-02 补丁测试：calendar.py 未覆盖年份 fail fast。

问题根因：
    _is_holiday 对 _KNOWN_HOLIDAYS 中不存在的年份静默返回 []，
    导致未覆盖年份（如 2028+）的所有工作日均被当作交易日，
    节假日会被错误地当成可交易日。

修复方案：
    d.year > _MAX_SUPPORTED_YEAR 时，_is_holiday 抛 ValueError，
    调用者（is_trading_day / next_trading_day）会立即传播异常，
    强制开发者在使用新年份前先扩展日历数据。
"""

from __future__ import annotations

from datetime import date

import pytest

from lq.core.calendar import (
    is_trading_day,
    next_trading_day,
    _MAX_SUPPORTED_YEAR,
)


class TestCalendarFailFast:
    """未覆盖年份应 ValueError fail fast，不静默使用错误数据。"""

    def test_max_supported_year_is_2027(self):
        """_MAX_SUPPORTED_YEAR 应为 2027（当前最后一个有节假日数据的年份）。"""
        assert _MAX_SUPPORTED_YEAR == 2027

    def test_is_trading_day_raises_for_unsupported_year(self):
        """is_trading_day 在超出覆盖年份时应抛 ValueError。"""
        # 2028-01-01 是周六，2028-01-03 是周一（工作日，会触发 _is_holiday 检查）
        with pytest.raises(ValueError, match="交易日历未覆盖"):
            is_trading_day(date(2028, 1, 3))   # 2028-01-03 是周一（工作日）

    def test_next_trading_day_raises_for_unsupported_year(self):
        """next_trading_day 迭代到超出覆盖年份时应抛 ValueError。"""
        # 从 2027-12-31 找下一个交易日会迭代到 2028-01-01（元旦，若未覆盖则 fail fast）
        with pytest.raises(ValueError, match="交易日历未覆盖"):
            next_trading_day(date(2027, 12, 31))

    def test_year_2027_does_not_raise(self):
        """2027 年（最后一个覆盖年份）不应抛异常。"""
        # 2027-01-04 是周一，不是节假日
        result = is_trading_day(date(2027, 1, 4))
        assert isinstance(result, bool)

    def test_year_2026_does_not_raise(self):
        """2026 年正常调用不应抛异常。"""
        result = is_trading_day(date(2026, 3, 16))   # 普通工作日
        assert result is True

    def test_covered_holiday_2027_is_not_trading_day(self):
        """2027 年春节（预估）应被识别为非交易日。"""
        # _KNOWN_HOLIDAYS[2027] 中含 (2, 6) 春节
        result = is_trading_day(date(2027, 2, 6))
        assert result is False

    def test_weekend_in_2028_still_raises_before_holiday_check(self):
        """2028 年周末应在 weekday 检查之前短路，但若是工作日则应抛 ValueError。

        注意：周末在 weekday >= 5 时直接返回 False，不走 _is_holiday，
        所以周六/周日不会 fail fast。只有工作日才触发 fail fast。
        2028-01-01 是周六：01-08 是周六，01-09 是周日，01-10 是周一。
        """
        # 2028-01-08 是周六 → weekday=5 >= 5 → 直接返回 False，不触发 fail fast
        assert is_trading_day(date(2028, 1, 8)) is False
        # 2028-01-10 是周一 → weekday=0 < 5 → 触发 _is_holiday 检查 → fail fast
        with pytest.raises(ValueError, match="交易日历未覆盖"):
            is_trading_day(date(2028, 1, 10))

    def test_error_message_mentions_year(self):
        """错误信息应明确说明哪个年份未被覆盖，方便开发者快速定位。"""
        with pytest.raises(ValueError, match="2028"):
            is_trading_day(date(2028, 6, 1))
