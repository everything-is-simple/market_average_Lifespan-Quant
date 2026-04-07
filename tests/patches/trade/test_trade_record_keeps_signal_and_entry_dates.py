"""P0-04 补丁测试：TradeRecord 保留真实 signal_date 与 entry_date，禁止混用。

回归防护：
    signal_date（T 日）与 entry_date（T+1 交易日）必须在 TradeRecord 中分开存储，
    且 signal_date != entry_date（周五信号 → 周一入场）。
"""

from __future__ import annotations

from datetime import date

import pytest

from lq.core.contracts import TradeLifecycleState
from lq.trade.management import TradeManager, TradeManagementState


def _make_manager_with_friday_signal() -> TradeManager:
    """构造一个周五信号（T=2024-05-31）、周一入场（T+1=2024-06-03）的交易管理器。"""
    state = TradeManagementState(
        trade_id="patch-trade-001",
        code="000001.SZ",
        signal_date=date(2024, 5, 31),   # T 日（周五）
        entry_date=date(2024, 6, 3),     # T+1 交易日（周一）
        entry_price=10.0,
        initial_stop_price=9.5,
        first_target_price=10.5,
        risk_unit=0.5,
        total_lots=10,
        active_lots=10,
        signal_pattern="BOF",
        malf_context_4="BULL_MAINSTREAM",
        pb_sequence_number=None,
    )
    mgr = TradeManager(state=state)
    mgr.activate(entry_price=10.0)
    return mgr


class TestTradeRecordDates:
    def test_signal_date_and_entry_date_are_different(self):
        """signal_date（T 日）与 entry_date（T+1）不应相同。"""
        mgr = _make_manager_with_friday_signal()
        mgr.update(9.8, 9.4, 9.5, date(2024, 6, 3))

        record = mgr.to_trade_record(exit_date=date(2024, 6, 3), exit_price=9.5)
        assert record.signal_date != record.entry_date, (
            f"signal_date({record.signal_date}) 不应等于 entry_date({record.entry_date})"
        )

    def test_signal_date_is_friday(self):
        """signal_date 必须是 T 日（周五）。"""
        mgr = _make_manager_with_friday_signal()
        mgr.update(9.8, 9.4, 9.5, date(2024, 6, 3))
        record = mgr.to_trade_record(exit_date=date(2024, 6, 3), exit_price=9.5)
        assert record.signal_date == date(2024, 5, 31)
        assert record.signal_date.weekday() == 4  # 周五

    def test_entry_date_is_monday(self):
        """entry_date 必须是 T+1 交易日（周一）。"""
        mgr = _make_manager_with_friday_signal()
        mgr.update(9.8, 9.4, 9.5, date(2024, 6, 3))
        record = mgr.to_trade_record(exit_date=date(2024, 6, 3), exit_price=9.5)
        assert record.entry_date == date(2024, 6, 3)
        assert record.entry_date.weekday() == 0  # 周一

    def test_signal_date_not_entry_date_proxy(self):
        """signal_date 不能是 entry_date 的代理（之前的 bug：两者写成同一个值）。"""
        mgr = _make_manager_with_friday_signal()
        mgr.update(10.2, 10.0, 10.1, date(2024, 6, 3))
        record = mgr.to_trade_record(exit_date=None, exit_price=None)
        # 确保 signal_date 来自 state.signal_date，而不是 state.entry_date
        assert record.signal_date == date(2024, 5, 31)
        assert record.entry_date == date(2024, 6, 3)
