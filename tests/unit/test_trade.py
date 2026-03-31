"""trade 模块单元测试 — 交易管理模板（A5）。"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from lq.core.contracts import TradeLifecycleState
from lq.trade.management import TradeManager, TradeManagementState, BREAKEVEN_TRIGGER_R, MAX_HOLD_DAYS


def _make_state(
    entry_price: float = 10.0,
    initial_stop: float = 9.5,
    first_target: float = 10.5,
    risk_unit: float = 0.5,
    total_lots: int = 10,
) -> TradeManagementState:
    return TradeManagementState(
        trade_id="test-trade-001",
        code="000001.SZ",
        entry_date=date(2024, 6, 3),
        entry_price=entry_price,
        initial_stop_price=initial_stop,
        first_target_price=first_target,
        risk_unit=risk_unit,
        total_lots=total_lots,
        active_lots=total_lots,
        signal_pattern="BOF",
        surface_label="BULL_MAINSTREAM",
        pb_sequence_number=1,
    )


class TestTradeManagerActivation:
    def test_activate_sets_active_state(self):
        state = _make_state()
        mgr = TradeManager(state=state)
        mgr.activate(entry_price=10.0)
        assert state.lifecycle_state == TradeLifecycleState.ACTIVE_INITIAL_STOP.value
        assert state.highest_price_seen == 10.0

    def test_initial_stop_set_correctly(self):
        state = _make_state(entry_price=10.0, initial_stop=9.5)
        mgr = TradeManager(state=state)
        mgr.activate(10.0)
        assert state.current_stop_price == 9.5


class TestInitialStop:
    def test_hit_initial_stop(self):
        state = _make_state(entry_price=10.0, initial_stop=9.5)
        mgr = TradeManager(state=state)
        mgr.activate(10.0)

        actions = mgr.update(
            today_high=10.1,
            today_low=9.4,   # 触及止损 9.5
            today_close=9.6,
            today_date=date(2024, 6, 4),
        )

        assert "HIT_INITIAL_STOP" in actions
        assert state.lifecycle_state == TradeLifecycleState.CLOSED_LOSS.value
        assert state.active_lots == 0

    def test_no_stop_triggered(self):
        state = _make_state(entry_price=10.0, initial_stop=9.5)
        mgr = TradeManager(state=state)
        mgr.activate(10.0)

        actions = mgr.update(
            today_high=10.2,
            today_low=9.8,   # 未触及止损
            today_close=10.1,
            today_date=date(2024, 6, 4),
        )

        assert "HIT_INITIAL_STOP" not in actions
        assert state.is_active


class TestFirstTarget:
    def test_hit_first_target(self):
        state = _make_state(
            entry_price=10.0,
            initial_stop=9.5,
            first_target=10.5,
            total_lots=10,
        )
        mgr = TradeManager(state=state)
        mgr.activate(10.0)

        # today_low=10.1 确保 breakeven 提损到 10.0 后跟踪止损不在同一根 K 线触发
        actions = mgr.update(
            today_high=10.5,   # 刚好触及 first_target=10.5
            today_low=10.1,
            today_close=10.4,
            today_date=date(2024, 6, 5),
        )

        assert "HIT_FIRST_TARGET" in actions
        assert state.first_target_hit is True
        assert state.active_lots == 5   # 半仓止盈后剩5手


class TestBreakeven:
    def test_breakeven_triggered_after_0_5r(self):
        # 设计：价格上涨 0.5R（未达到第一目标 1R），触发提损到成本价
        state = _make_state(
            entry_price=10.0,
            initial_stop=9.5,
            first_target=10.5,
            risk_unit=0.5,
            total_lots=10,
        )
        mgr = TradeManager(state=state)
        mgr.activate(10.0)

        # 价格涨到 10.25（0.5R），未触及第一目标 10.5
        actions = mgr.update(
            today_high=10.25,
            today_low=10.1,
            today_close=10.2,
            today_date=date(2024, 6, 4),
        )

        assert "BREAKEVEN_TRIGGERED" in actions
        assert state.current_stop_price >= state.entry_price


class TestTimeStop:
    def test_time_stop_after_max_days(self):
        state = _make_state(total_lots=10)
        mgr = TradeManager(state=state)
        mgr.activate(10.0)

        # 先触发第一目标（today_low=10.1 避免同 K 线触发跟踪止损）
        mgr.update(10.5, 10.1, 10.4, date(2024, 6, 5))
        assert state.first_target_hit is True
        assert state.active_lots == 5

        # 模拟超过最大持仓天数（hold_days=19，update 后变 20）
        state.hold_days = MAX_HOLD_DAYS - 1
        # today_low=10.05 避免跟踪止损（trailing_stop=10.0）在同一根 K 线触发
        actions = mgr.update(10.1, 10.05, 10.08, date(2024, 6, 30))

        assert "TIME_STOP_TRIGGERED" in actions
        assert state.lifecycle_state == TradeLifecycleState.CLOSED_TIME.value


class TestToTradeRecord:
    def test_produces_valid_record(self):
        state = _make_state(entry_price=10.0, initial_stop=9.5)
        mgr = TradeManager(state=state)
        mgr.activate(10.0)
        # 触发止损
        mgr.update(9.8, 9.4, 9.5, date(2024, 6, 4))

        record = mgr.to_trade_record(
            exit_date=date(2024, 6, 4),
            exit_price=9.5,
        )

        assert record.code == "000001.SZ"
        assert record.exit_price == 9.5
        assert record.exit_reason == "INITIAL_STOP"
        assert record.pnl_amount is not None
        assert record.r_multiple is not None
        assert record.r_multiple < 0   # 亏损
