"""1R 头寸规模计算。"""

from __future__ import annotations

import math
from datetime import date
from uuid import uuid4

from lq.core.calendar import next_trading_day
from lq.core.contracts import (
    DEFAULT_CAPITAL_BASE,
    DEFAULT_FIXED_NOTIONAL,
    DEFAULT_LOT_SIZE,
)
from lq.alpha.pas.contracts import PasSignal
from lq.position.contracts import ExitLeg, PositionPlan, PositionExitPlan


# 默认参数
STOP_BUFFER_PCT = 0.005    # 止损价低于信号低点的缓冲（0.5%）
RUNNER_TRAILING_PCT = 0.08  # 跟踪止损：从持仓最高点回撤 8% 触发
TIME_STOP_DAYS = 20        # 时间止损天数


def compute_position_plan(
    signal: PasSignal,
    entry_price: float,
    fixed_notional: float = DEFAULT_FIXED_NOTIONAL,
    lot_size: int = DEFAULT_LOT_SIZE,
    stop_buffer_pct: float = STOP_BUFFER_PCT,
) -> PositionPlan:
    """根据 PAS 信号计算 1R 头寸规划。

    入场语义：T+1 开盘，entry_price 为 T+1 开盘预估价（通常传入前日收盘或预计开盘价）。
    """
    # 初始止损：信号低点再向下 stop_buffer
    initial_stop = signal.signal_low * (1.0 - stop_buffer_pct)

    # 1R 风险单位
    risk_unit = entry_price - initial_stop
    if risk_unit <= 0:
        # 止损价高于或等于入场价，强制使用 0.5% 的最小风险
        risk_unit = entry_price * 0.005
        initial_stop = entry_price - risk_unit

    # 第一目标：入场 + 1R
    first_target = entry_price + risk_unit

    # 整手约束：按固定名义金额计算
    lot_count = max(1, math.floor(fixed_notional / (entry_price * lot_size))) * 1
    notional = lot_count * lot_size * entry_price

    # T+1 交易日语义：跳过周末与法定节假日
    entry_date = next_trading_day(signal.signal_date)

    return PositionPlan(
        code=signal.code,
        signal_date=signal.signal_date,
        entry_date=entry_date,
        signal_pattern=signal.pattern,
        signal_low=signal.signal_low,
        entry_price=entry_price,
        initial_stop_price=round(initial_stop, 2),
        first_target_price=round(first_target, 2),
        risk_unit=round(risk_unit, 4),
        lot_count=lot_count,
        notional=round(notional, 2),
    )


def build_exit_plan(
    plan: PositionPlan,
    trailing_pct: float = RUNNER_TRAILING_PCT,
    time_stop_days: int = TIME_STOP_DAYS,
) -> PositionExitPlan:
    """根据头寸规划生成完整退出计划。

    退出结构：
        腿1 (first_target)：半仓在第一目标止盈
        腿2 (runner)：剩余半仓跟踪止损
    """
    half_lots = max(1, plan.lot_count // 2)
    runner_lots = plan.lot_count - half_lots

    legs = (
        ExitLeg(
            leg_id=f"leg1-{uuid4().hex[:6]}",
            leg_type="first_target",
            exit_price=plan.first_target_price,
            lot_count=half_lots,
            is_partial=True,
        ),
        ExitLeg(
            leg_id=f"leg2-{uuid4().hex[:6]}",
            leg_type="runner",
            exit_price=plan.first_target_price,  # 初始目标，跟踪后会动态更新
            lot_count=runner_lots,
            is_partial=False,
        ),
    )

    # 跟踪止损触发价：从当前入场价 * (1 + trailing_pct)（会随价格上移）
    trailing_trigger = plan.entry_price * (1.0 - trailing_pct)

    return PositionExitPlan(
        plan_id=f"exitplan-{uuid4().hex[:8]}",
        code=plan.code,
        signal_date=plan.signal_date,
        entry_plan=plan,
        legs=legs,
        trailing_stop_trigger=round(trailing_trigger, 2),
        time_stop_days=time_stop_days,
    )
