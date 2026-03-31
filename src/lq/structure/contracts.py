"""统一结构位合同 — 系统新增核心（优先级 A1）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from lq.core.contracts import StructureLevelType, BreakoutType


@dataclass(frozen=True)
class StructureLevel:
    """单个结构位（关键价格位）— 所有 trigger 共用。"""

    level_type: str      # StructureLevelType 值
    price: float         # 结构位价格
    formed_date: date    # 形成日期
    strength: float      # 强度 0~1
    touch_count: int = 1
    is_tested: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        valid = {t.value for t in StructureLevelType}
        if self.level_type not in valid:
            raise ValueError(f"非法 level_type: {self.level_type}")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"strength 须在 0~1，当前: {self.strength}")

    @property
    def is_support(self) -> bool:
        return self.level_type in (
            StructureLevelType.SUPPORT.value,
            StructureLevelType.PIVOT_LOW.value,
            StructureLevelType.POST_BREAKOUT_SUPPORT.value,
            StructureLevelType.TEST_POINT.value,
        )

    @property
    def is_resistance(self) -> bool:
        return self.level_type in (
            StructureLevelType.RESISTANCE.value,
            StructureLevelType.PIVOT_HIGH.value,
            StructureLevelType.POST_BREAKDOWN_RESISTANCE.value,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "level_type": self.level_type,
            "price": self.price,
            "formed_date": self.formed_date.isoformat(),
            "strength": self.strength,
            "touch_count": self.touch_count,
            "is_tested": self.is_tested,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class BreakoutEvent:
    """突破事件分类结果 — 突破家族语义核心合同（优先级 A2）。

    回答：这次价格穿越结构位，到底算什么？
    """

    event_date: date
    level: StructureLevel
    breakout_type: str       # BreakoutType 值
    penetration_pct: float   # 穿越幅度（正=向上，负=向下）
    recovered: bool          # 是否已收回（假突破的核心判断）
    confirmed: bool          # 是否已被确认（有效突破的核心判断）
    notes: str = ""

    def __post_init__(self) -> None:
        valid = {t.value for t in BreakoutType}
        if self.breakout_type not in valid:
            raise ValueError(f"非法 breakout_type: {self.breakout_type}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_date": self.event_date.isoformat(),
            "level": self.level.as_dict(),
            "breakout_type": self.breakout_type,
            "penetration_pct": self.penetration_pct,
            "recovered": self.recovered,
            "confirmed": self.confirmed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class StructureSnapshot:
    """单只股票当日结构位快照 — 传递给 trigger 和 filter 的合同。"""

    code: str
    signal_date: date
    support_levels: tuple[StructureLevel, ...]    # 当前有效支撑位（由近到远）
    resistance_levels: tuple[StructureLevel, ...]  # 当前有效阻力位（由近到远）
    recent_breakout: BreakoutEvent | None          # 最近发生的突破事件
    nearest_support: StructureLevel | None         # 最近支撑位
    nearest_resistance: StructureLevel | None      # 最近阻力位

    @property
    def has_clear_structure(self) -> bool:
        """是否有清晰的结构（至少有一个支撑位和阻力位）。"""
        return len(self.support_levels) > 0 and len(self.resistance_levels) > 0

    @property
    def available_space_pct(self) -> float | None:
        """当前价格到最近阻力位的空间百分比（无法计算时返回 None）。"""
        if self.nearest_support is None or self.nearest_resistance is None:
            return None
        mid = (self.nearest_support.price + self.nearest_resistance.price) / 2
        if abs(mid) < 1e-9:
            return None
        space = self.nearest_resistance.price - self.nearest_support.price
        return space / mid

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "support_levels": [s.as_dict() for s in self.support_levels],
            "resistance_levels": [r.as_dict() for r in self.resistance_levels],
            "recent_breakout": self.recent_breakout.as_dict() if self.recent_breakout else None,
            "nearest_support": self.nearest_support.as_dict() if self.nearest_support else None,
            "nearest_resistance": self.nearest_resistance.as_dict() if self.nearest_resistance else None,
        }
