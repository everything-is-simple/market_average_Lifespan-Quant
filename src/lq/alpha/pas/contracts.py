"""PAS 模块数据合同。"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from lq.core.contracts import PasTriggerPattern, MalfContext4
from lq.malf.contracts import build_signal_id, PAS_CONTRACT_VERSION


def _utc_suffix() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class PasDetectTrace:
    """单次 PAS 探测的完整 trace，不管是否触发。"""

    signal_id: str
    pattern: str          # PasTriggerPattern 值
    triggered: bool
    strength: float | None   # 触发时 0~1，未触发时 None
    skip_reason: str | None  # 跳过原因（数据不足等）
    detect_reason: str | None  # 触发或未触发的具体原因
    history_days: int
    min_history_days: int
    # 第一 PB 追踪（A3 新增）
    pb_sequence_number: int | None = None  # 本次 PB 是当前走势的第几个 PB

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "pattern": self.pattern,
            "triggered": self.triggered,
            "strength": self.strength,
            "skip_reason": self.skip_reason,
            "detect_reason": self.detect_reason,
            "history_days": self.history_days,
            "min_history_days": self.min_history_days,
            "pb_sequence_number": self.pb_sequence_number,
        }


@dataclass(frozen=True)
class PasSignal:
    """PAS 正式触发信号 — 模块间传递的结果合同。"""

    signal_id: str
    code: str
    signal_date: date
    pattern: str           # PasTriggerPattern 值
    malf_context_4: str     # MalfContext4 值（来自 MALF 上下文）
    strength: float        # 信号强度 0~1
    signal_low: float      # 信号最低价（用于计算 1R）
    entry_ref_price: float  # 参考入场价（通常是收盘价或次日开盘预估）
    long_background_2: str | None = None
    intermediate_role_2: str | None = None
    amplitude_rank_low: int | None = None
    amplitude_rank_high: int | None = None
    amplitude_rank_total: int | None = None
    duration_rank_low: int | None = None
    duration_rank_high: int | None = None
    duration_rank_total: int | None = None
    new_price_rank_low: int | None = None
    new_price_rank_high: int | None = None
    new_price_rank_total: int | None = None
    lifecycle_rank_low: int | None = None
    lifecycle_rank_high: int | None = None
    lifecycle_rank_total: int | None = None
    amplitude_quartile: str | None = None
    duration_quartile: str | None = None
    new_price_quartile: str | None = None
    lifecycle_quartile: str | None = None
    monthly_state: str | None = None
    weekly_flow: str | None = None
    # 第一 PB 追踪（A3 新增）
    pb_sequence_number: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "pattern": self.pattern,
            "malf_context_4": self.malf_context_4,
            "strength": self.strength,
            "signal_low": self.signal_low,
            "entry_ref_price": self.entry_ref_price,
            "long_background_2": self.long_background_2,
            "intermediate_role_2": self.intermediate_role_2,
            "amplitude_rank_low": self.amplitude_rank_low,
            "amplitude_rank_high": self.amplitude_rank_high,
            "amplitude_rank_total": self.amplitude_rank_total,
            "duration_rank_low": self.duration_rank_low,
            "duration_rank_high": self.duration_rank_high,
            "duration_rank_total": self.duration_rank_total,
            "new_price_rank_low": self.new_price_rank_low,
            "new_price_rank_high": self.new_price_rank_high,
            "new_price_rank_total": self.new_price_rank_total,
            "lifecycle_rank_low": self.lifecycle_rank_low,
            "lifecycle_rank_high": self.lifecycle_rank_high,
            "lifecycle_rank_total": self.lifecycle_rank_total,
            "amplitude_quartile": self.amplitude_quartile,
            "duration_quartile": self.duration_quartile,
            "new_price_quartile": self.new_price_quartile,
            "lifecycle_quartile": self.lifecycle_quartile,
            "monthly_state": self.monthly_state,
            "weekly_flow": self.weekly_flow,
            "pb_sequence_number": self.pb_sequence_number,
        }


@dataclass(frozen=True)
class PasBatchResult:
    """PAS 批量探测结果摘要。"""

    run_id: str
    asof_date: date
    codes_scanned: int
    triggered_count: int
    pattern_counts: dict[str, int]
    signals: tuple[PasSignal, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "asof_date": self.asof_date.isoformat(),
            "codes_scanned": self.codes_scanned,
            "triggered_count": self.triggered_count,
            "pattern_counts": self.pattern_counts,
        }
