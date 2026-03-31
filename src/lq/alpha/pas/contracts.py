"""PAS 模块数据合同。"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from lq.core.contracts import PasTriggerPattern, SurfaceLabel
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
    surface_label: str     # SurfaceLabel 值（来自 MALF 上下文）
    strength: float        # 信号强度 0~1
    signal_low: float      # 信号最低价（用于计算 1R）
    entry_ref_price: float  # 参考入场价（通常是收盘价或次日开盘预估）
    # 第一 PB 追踪（A3 新增）
    pb_sequence_number: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "pattern": self.pattern,
            "surface_label": self.surface_label,
            "strength": self.strength,
            "signal_low": self.signal_low,
            "entry_ref_price": self.entry_ref_price,
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
