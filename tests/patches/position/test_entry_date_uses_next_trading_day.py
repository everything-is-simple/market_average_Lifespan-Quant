"""P0-03 补丁测试：entry_date 使用交易日语义，不使用自然日 +1。

回归防护：
    周五信号 → entry_date 必须是下周一（不能是周六）。
    节假日前信号 → entry_date 必须跳过假期。
"""

from __future__ import annotations

from datetime import date

import pytest

from lq.core.calendar import next_trading_day, is_trading_day


class TestNextTradingDay:
    def test_friday_signal_gives_monday_entry(self):
        """周五（2024-05-31）信号 → 入场日必须是下周一（2024-06-03）。"""
        friday = date(2024, 5, 31)
        assert friday.weekday() == 4, "确认测试日期是周五"
        entry = next_trading_day(friday)
        assert entry == date(2024, 6, 3), f"周五信号应入场于下周一，得到 {entry}"

    def test_monday_signal_gives_tuesday_entry(self):
        """周一信号 → 入场日是周二。"""
        monday = date(2024, 6, 3)
        entry = next_trading_day(monday)
        assert entry == date(2024, 6, 4)

    def test_saturday_is_not_trading_day(self):
        saturday = date(2024, 6, 1)
        assert is_trading_day(saturday) is False

    def test_sunday_is_not_trading_day(self):
        sunday = date(2024, 6, 2)
        assert is_trading_day(sunday) is False

    def test_normal_weekday_is_trading_day(self):
        wednesday = date(2024, 6, 5)
        assert is_trading_day(wednesday) is True

    def test_spring_festival_2025_skipped(self):
        """2025 年春节前最后交易日（1月27日）信号 → 入场日跳过长假，返回 2025-02-05。"""
        last_before_festival = date(2025, 1, 27)
        entry = next_trading_day(last_before_festival)
        # 2025 春节假期：1-28 ~ 2-4，节后第一交易日 2-5
        assert entry == date(2025, 2, 5), f"应跳过春节假期，得到 {entry}"

    def test_no_natural_day_plus_one(self):
        """周五信号不能返回周六（自然日 +1 的错误行为）。"""
        friday = date(2024, 5, 31)
        bad_entry = date(2024, 6, 1)  # 周六，自然日 +1 的错误结果
        entry = next_trading_day(friday)
        assert entry != bad_entry, "entry_date 不能是周六"
