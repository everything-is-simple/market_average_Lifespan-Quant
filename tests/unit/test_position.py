"""position 模块单元测试 — 1R 头寸规模与退出合同。"""

from __future__ import annotations

from datetime import date

import pytest

from lq.alpha.pas.contracts import PasSignal
from lq.position.sizing import compute_position_plan, build_exit_plan
from lq.position.contracts import PositionPlan, PositionExitPlan


def _make_signal(
    code: str = "000001.SZ",
    signal_date: date = date(2024, 6, 1),
    signal_low: float = 9.5,
    entry_ref_price: float = 10.0,
    pattern: str = "BOF",
    strength: float = 0.75,
) -> PasSignal:
    return PasSignal(
        signal_id=f"PAS_v1_{code}_{signal_date}_{pattern}",
        code=code,
        signal_date=signal_date,
        pattern=pattern,
        surface_label="BULL_MAINSTREAM",
        strength=strength,
        signal_low=signal_low,
        entry_ref_price=entry_ref_price,
    )


class TestComputePositionPlan:
    def test_basic_plan_fields(self):
        sig = _make_signal()
        plan = compute_position_plan(sig, entry_price=10.0)

        assert plan.code == "000001.SZ"
        assert plan.entry_price == 10.0
        assert plan.initial_stop_price < plan.entry_price
        assert plan.first_target_price > plan.entry_price
        assert plan.risk_unit > 0
        assert plan.lot_count >= 1

    def test_1r_relationship(self):
        sig = _make_signal(signal_low=9.5, entry_ref_price=10.0)
        plan = compute_position_plan(sig, entry_price=10.0, stop_buffer_pct=0.005)

        # 1R：first_target = entry + risk_unit
        expected_stop = 9.5 * (1 - 0.005)
        expected_risk = 10.0 - expected_stop
        expected_target = 10.0 + expected_risk

        assert abs(plan.initial_stop_price - expected_stop) < 0.01
        assert abs(plan.risk_unit - expected_risk) < 0.01
        assert abs(plan.first_target_price - expected_target) < 0.01

    def test_lot_count_is_integer(self):
        sig = _make_signal()
        plan = compute_position_plan(sig, entry_price=10.0, fixed_notional=100_000)
        assert isinstance(plan.lot_count, int)
        assert plan.lot_count >= 1

    def test_entry_date_is_t_plus_1(self):
        from datetime import timedelta
        sig = _make_signal(signal_date=date(2024, 6, 3))
        plan = compute_position_plan(sig, entry_price=10.0)
        assert plan.entry_date == date(2024, 6, 3) + timedelta(days=1)

    def test_degenerate_stop_above_entry(self):
        """当止损价高于入场价时，应自动修正。"""
        sig = _make_signal(signal_low=11.0, entry_ref_price=10.0)
        plan = compute_position_plan(sig, entry_price=10.0)
        # 修正后止损应低于入场价
        assert plan.initial_stop_price < plan.entry_price
        assert plan.risk_unit > 0


class TestBuildExitPlan:
    def test_exit_plan_has_two_legs(self):
        sig = _make_signal()
        position_plan = compute_position_plan(sig, entry_price=10.0)
        exit_plan = build_exit_plan(position_plan)

        assert isinstance(exit_plan, PositionExitPlan)
        assert len(exit_plan.legs) == 2

    def test_first_leg_is_partial(self):
        sig = _make_signal()
        position_plan = compute_position_plan(sig, entry_price=10.0)
        exit_plan = build_exit_plan(position_plan)

        first_leg = exit_plan.legs[0]
        assert first_leg.leg_type == "first_target"
        assert first_leg.is_partial is True

    def test_legs_lot_count_sum(self):
        sig = _make_signal()
        position_plan = compute_position_plan(sig, entry_price=10.0)
        exit_plan = build_exit_plan(position_plan)

        total = sum(leg.lot_count for leg in exit_plan.legs)
        assert total == position_plan.lot_count

    def test_trailing_stop_below_entry(self):
        sig = _make_signal()
        position_plan = compute_position_plan(sig, entry_price=10.0)
        exit_plan = build_exit_plan(position_plan)
        # 初始跟踪止损应低于入场价
        assert exit_plan.trailing_stop_trigger < position_plan.entry_price
