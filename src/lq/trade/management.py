"""交易管理模板 — 优先级 A5 正式实现。

把"入场后如何演化"组织成正式模板，包含：
    1. 初始止损保护
    2. 第一目标达到后的处理（半仓止盈）
    3. 保护性提损（提损到成本价）
    4. Runner 跟踪止损
    5. 时间止损
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any
from uuid import uuid4

from lq.core.contracts import TradeLifecycleState
from lq.position.contracts import PositionPlan, PositionExitPlan
from lq.trade.contracts import TradeRecord


# ---------------------------------------------------------------------------
# 管理模板参数
# ---------------------------------------------------------------------------

TRAILING_ACTIVATION_R = 1.0       # 盈利超过 1R 后激活跟踪止损
TRAILING_STEP_PCT = 0.06           # 跟踪步距：从最高点回撤 6% 触发
BREAKEVEN_TRIGGER_R = 0.5          # 盈利超过 0.5R 后提损到成本价
MAX_HOLD_DAYS = 20                 # 时间止损天数上限
FAST_FAILURE_DAYS = 3              # 快速失效：入场后 3 日内触发止损视为快速失效


# ---------------------------------------------------------------------------
# 交易管理状态（可变，伴随交易生命周期更新）
# ---------------------------------------------------------------------------

@dataclass
class TradeManagementState:
    """单笔交易的实时管理状态 — 伴随每日 K 线更新。"""

    trade_id: str
    code: str
    signal_date: date        # T 日（信号产生日）
    entry_date: date         # T+1 日（实际入场日，交易日语义）
    entry_price: float
    initial_stop_price: float
    first_target_price: float
    risk_unit: float
    total_lots: int
    active_lots: int              # 当前持仓手数
    signal_pattern: str
    surface_label: str
    pb_sequence_number: int | None

    # 动态状态
    lifecycle_state: str = TradeLifecycleState.PENDING_ENTRY.value
    current_stop_price: float = 0.0     # 当前止损价（可动态提升）
    highest_price_seen: float = 0.0     # 持仓期间见过的最高价
    hold_days: int = 0
    first_target_hit: bool = False
    breakeven_triggered: bool = False

    def __post_init__(self) -> None:
        if self.current_stop_price == 0.0:
            self.current_stop_price = self.initial_stop_price
        if self.highest_price_seen == 0.0:
            self.highest_price_seen = self.entry_price

    @property
    def is_active(self) -> bool:
        return self.lifecycle_state in (
            TradeLifecycleState.ACTIVE_INITIAL_STOP.value,
            TradeLifecycleState.FIRST_TARGET_HIT.value,
            TradeLifecycleState.TRAILING_RUNNER.value,
        )

    @property
    def is_closed(self) -> bool:
        return self.lifecycle_state in (
            TradeLifecycleState.CLOSED_WIN.value,
            TradeLifecycleState.CLOSED_LOSS.value,
            TradeLifecycleState.CLOSED_TIME.value,
        )

    @property
    def current_r_multiple(self) -> float:
        """当前盈利相对于初始 1R 的倍数。"""
        if abs(self.risk_unit) < 1e-9:
            return 0.0
        return (self.highest_price_seen - self.entry_price) / self.risk_unit

    def as_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "code": self.code,
            "entry_date": self.entry_date.isoformat(),
            "lifecycle_state": self.lifecycle_state,
            "current_stop_price": self.current_stop_price,
            "highest_price_seen": self.highest_price_seen,
            "hold_days": self.hold_days,
            "active_lots": self.active_lots,
            "first_target_hit": self.first_target_hit,
            "breakeven_triggered": self.breakeven_triggered,
            "current_r_multiple": self.current_r_multiple,
        }


# ---------------------------------------------------------------------------
# 交易管理器
# ---------------------------------------------------------------------------

@dataclass
class TradeManager:
    """交易管理模板执行器。

    使用方式：
        1. 创建 TradeManager(state)
        2. 每日调用 update(today_high, today_low, today_close) 更新状态
        3. 检查 state.lifecycle_state 判断是否需要执行实际的买卖动作
    """

    state: TradeManagementState
    # 管理事件日志
    events: list[dict[str, Any]] = field(default_factory=list)

    def activate(self, entry_price: float) -> None:
        """确认入场，激活交易管理。"""
        self.state.lifecycle_state = TradeLifecycleState.ACTIVE_INITIAL_STOP.value
        self.state.highest_price_seen = entry_price
        self._log("ACTIVATED", f"入场价={entry_price:.2f}，初始止损={self.state.initial_stop_price:.2f}")

    def update(
        self,
        today_high: float,
        today_low: float,
        today_close: float,
        today_date: date,
    ) -> list[str]:
        """每日更新交易状态，返回触发的动作列表。

        返回的动作字符串用于通知调用方执行具体操作：
            "HIT_INITIAL_STOP"  — 触及初始止损
            "HIT_FIRST_TARGET"  — 触及第一目标（半仓止盈）
            "BREAKEVEN_TRIGGERED" — 提损到成本价
            "TRAILING_STOP_TRIGGERED" — 跟踪止损触发
            "TIME_STOP_TRIGGERED"  — 时间止损触发
        """
        if not self.state.is_active:
            return []

        actions: list[str] = []
        self.state.hold_days += 1

        # 更新见过的最高价
        if today_high > self.state.highest_price_seen:
            self.state.highest_price_seen = today_high

        # ── 步骤1：检查初始止损 ────────────────────────────────────────────
        if (
            not self.state.first_target_hit
            and today_low <= self.state.current_stop_price
        ):
            self.state.lifecycle_state = TradeLifecycleState.CLOSED_LOSS.value
            self.state.active_lots = 0
            actions.append("HIT_INITIAL_STOP")
            self._log(
                "HIT_INITIAL_STOP",
                f"触及止损={self.state.current_stop_price:.2f}，日低={today_low:.2f}",
                today_date,
            )
            return actions

        # ── 步骤2：检查第一目标（半仓止盈）──────────────────────────────────
        if (
            not self.state.first_target_hit
            and today_high >= self.state.first_target_price
        ):
            half_lots = self.state.active_lots // 2
            self.state.active_lots -= half_lots
            self.state.first_target_hit = True
            self.state.lifecycle_state = TradeLifecycleState.FIRST_TARGET_HIT.value
            actions.append("HIT_FIRST_TARGET")
            self._log(
                "PARTIAL_EXIT",
                f"第一目标{self.state.first_target_price:.2f}达成，半仓止盈{half_lots}手",
                today_date,
            )

        # ── 步骤3：提损到成本价（盈利超过 0.5R）─────────────────────────────
        if (
            not self.state.breakeven_triggered
            and self.state.current_r_multiple >= BREAKEVEN_TRIGGER_R
        ):
            self.state.current_stop_price = max(
                self.state.current_stop_price,
                self.state.entry_price,
            )
            self.state.breakeven_triggered = True
            self.state.lifecycle_state = TradeLifecycleState.TRAILING_RUNNER.value
            actions.append("BREAKEVEN_TRIGGERED")
            self._log(
                "STOP_RAISED_TO_BREAKEVEN",
                f"盈利{self.state.current_r_multiple:.2f}R，止损提至成本={self.state.entry_price:.2f}",
                today_date,
            )

        # ── 步骤4：跟踪止损（盈利超过 1R 后激活）────────────────────────────
        if (
            self.state.first_target_hit
            and self.state.current_r_multiple >= TRAILING_ACTIVATION_R
        ):
            trailing_stop = self.state.highest_price_seen * (1.0 - TRAILING_STEP_PCT)
            trailing_stop = max(trailing_stop, self.state.current_stop_price)

            if today_low <= trailing_stop and self.state.active_lots > 0:
                self.state.current_stop_price = trailing_stop
                self.state.lifecycle_state = TradeLifecycleState.CLOSED_WIN.value
                self.state.active_lots = 0
                actions.append("TRAILING_STOP_TRIGGERED")
                self._log(
                    "TRAILING_STOP_TRIGGERED",
                    f"跟踪止损={trailing_stop:.2f}触发，最高={self.state.highest_price_seen:.2f}",
                    today_date,
                )
                return actions
            else:
                # 动态更新跟踪止损位
                self.state.current_stop_price = trailing_stop

        # ── 步骤5：时间止损 ────────────────────────────────────────────────
        if self.state.hold_days >= MAX_HOLD_DAYS and self.state.active_lots > 0:
            self.state.lifecycle_state = TradeLifecycleState.CLOSED_TIME.value
            self.state.active_lots = 0
            actions.append("TIME_STOP_TRIGGERED")
            self._log(
                "TIME_STOP_TRIGGERED",
                f"持仓{self.state.hold_days}日达到时间止损上限",
                today_date,
            )

        return actions

    def _log(self, event_type: str, detail: str, event_date: date | None = None) -> None:
        self.events.append({
            "event_type": event_type,
            "detail": detail,
            "date": event_date.isoformat() if event_date else None,
        })

    def to_trade_record(
        self,
        exit_date: date | None,
        exit_price: float | None,
    ) -> TradeRecord:
        """将当前状态转换为最终交易记录。"""
        exit_reason = None
        if "HIT_INITIAL_STOP" in [e["event_type"] for e in self.events]:
            exit_reason = "INITIAL_STOP"
        elif "TRAILING_STOP_TRIGGERED" in [e["event_type"] for e in self.events]:
            exit_reason = "TRAILING_STOP"
        elif "TIME_STOP_TRIGGERED" in [e["event_type"] for e in self.events]:
            exit_reason = "TIME_STOP"

        pnl_amount = None
        pnl_pct = None
        r_multiple = None
        if exit_price is not None:
            pnl_amount = (exit_price - self.state.entry_price) * self.state.total_lots * 100
            pnl_pct = (exit_price - self.state.entry_price) / self.state.entry_price
            if abs(self.state.risk_unit) > 1e-9:
                r_multiple = (exit_price - self.state.entry_price) / self.state.risk_unit

        return TradeRecord(
            trade_id=self.state.trade_id,
            code=self.state.code,
            signal_date=self.state.signal_date,  # T 日：真实信号产生日
            entry_date=self.state.entry_date,    # T+1 日：真实入场日（交易日语义）
            exit_date=exit_date,
            signal_pattern=self.state.signal_pattern,
            surface_label=self.state.surface_label,
            entry_price=self.state.entry_price,
            exit_price=exit_price,
            lot_count=self.state.total_lots,
            initial_stop_price=self.state.initial_stop_price,
            first_target_price=self.state.first_target_price,
            risk_unit=self.state.risk_unit,
            pnl_amount=round(pnl_amount, 2) if pnl_amount is not None else None,
            pnl_pct=round(pnl_pct, 4) if pnl_pct is not None else None,
            r_multiple=round(r_multiple, 3) if r_multiple is not None else None,
            exit_reason=exit_reason,
            lifecycle_state=self.state.lifecycle_state,
            pb_sequence_number=self.state.pb_sequence_number,
        )
