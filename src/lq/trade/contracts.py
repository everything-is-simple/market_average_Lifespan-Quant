"""trade 模块数据合同。"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from lq.core.contracts import TradeLifecycleState


def _utc_suffix() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class TradeRecord:
    """单笔已完成交易记录（模块间传递的结果合同）。"""

    trade_id: str
    code: str
    signal_date: date
    entry_date: date
    exit_date: date | None
    signal_pattern: str
    malf_context_4: str
    entry_price: float
    exit_price: float | None
    lot_count: int
    initial_stop_price: float
    first_target_price: float
    risk_unit: float
    pnl_amount: float | None      # 盈亏金额
    pnl_pct: float | None         # 盈亏比例
    r_multiple: float | None      # R 倍数（相对于初始风险）
    exit_reason: str | None       # 退出原因
    lifecycle_state: str          # TradeLifecycleState 最终状态
    # 第一 PB 追踪
    pb_sequence_number: int | None = None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["signal_date"] = self.signal_date.isoformat()
        if self.entry_date:
            d["entry_date"] = self.entry_date.isoformat()
        if self.exit_date:
            d["exit_date"] = self.exit_date.isoformat()
        return d


@dataclass(frozen=True)
class TradeRunSummary:
    """trade 运行摘要。"""

    run_id: str
    strategy_name: str
    asof_date: date
    signal_count: int
    trade_count: int
    win_count: int
    loss_count: int
    avg_r_multiple: float | None
    avg_pnl_pct: float | None
    max_drawdown_pct: float | None

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["asof_date"] = self.asof_date.isoformat()
        return d
