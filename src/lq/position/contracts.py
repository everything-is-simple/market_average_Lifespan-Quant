"""position 模块数据合同。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from lq.core.contracts import DEFAULT_LOT_SIZE


@dataclass(frozen=True)
class PositionPlan:
    """单笔交易的头寸规划合同（入场前计算）。

    1R 合同：
        risk_unit = entry_price - initial_stop_price
        first_target = entry_price + risk_unit  (1R 止盈)
        lot_size = floor(fixed_notional / (entry_price * lot_size_unit))
    """

    code: str
    signal_date: date
    entry_date: date          # T+1 执行日
    signal_pattern: str       # PasTriggerPattern 值
    signal_low: float         # 信号 K 线最低价（用于初始止损参考）
    entry_price: float        # T+1 开盘预估入场价
    initial_stop_price: float  # 初始止损价（通常低于 signal_low 一定幅度）
    first_target_price: float  # 第一目标价（entry + 1R）
    risk_unit: float           # 1R = entry - stop
    lot_count: int             # 实际手数（整手约束）
    notional: float            # 实际名义金额

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "entry_date": self.entry_date.isoformat(),
            "signal_pattern": self.signal_pattern,
            "signal_low": self.signal_low,
            "entry_price": self.entry_price,
            "initial_stop_price": self.initial_stop_price,
            "first_target_price": self.first_target_price,
            "risk_unit": self.risk_unit,
            "lot_count": self.lot_count,
            "notional": self.notional,
        }


@dataclass(frozen=True)
class ExitLeg:
    """单腿退出计划。"""

    leg_id: str
    leg_type: str          # "first_target" | "runner" | "stop"
    exit_price: float
    lot_count: int
    is_partial: bool       # True = 部分退出（半仓止盈）

    def as_dict(self) -> dict[str, Any]:
        return {
            "leg_id": self.leg_id,
            "leg_type": self.leg_type,
            "exit_price": self.exit_price,
            "lot_count": self.lot_count,
            "is_partial": self.is_partial,
        }


@dataclass(frozen=True)
class PositionExitPlan:
    """完整退出计划（含所有腿）。"""

    plan_id: str
    code: str
    signal_date: date
    entry_plan: PositionPlan
    legs: tuple[ExitLeg, ...]
    trailing_stop_trigger: float    # 跟踪止损触发价
    time_stop_days: int = 20        # 时间止损天数上限

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "entry_plan": self.entry_plan.as_dict(),
            "legs": [leg.as_dict() for leg in self.legs],
            "trailing_stop_trigger": self.trailing_stop_trigger,
            "time_stop_days": self.time_stop_days,
        }
