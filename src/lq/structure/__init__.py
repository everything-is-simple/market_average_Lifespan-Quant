"""structure — 统一结构位合同与突破家族语义。

这是系统新增的核心模块（优先级 A1/A2）。
职责：
1. 识别水平关键位（支撑/阻力/波段高低点）
2. 分类突破事件（有效突破/假突破/测试/回踩确认）
3. 为 alpha/pas 所有 trigger 提供统一结构语言
"""

from .contracts import (
    StructureLevel,
    BreakoutEvent,
    StructureSnapshot,
)
from .detector import (
    find_pivot_highs,
    find_pivot_lows,
    find_horizontal_levels,
    classify_breakout_event,
    build_structure_snapshot,
)
from .pipeline import (
    STRUCTURE_SCHEMA_SQL,
    StructureBuildResult,
    bootstrap_structure_storage,
    run_structure_build,
)

__all__ = [
    "StructureLevel",
    "BreakoutEvent",
    "StructureSnapshot",
    "find_pivot_highs",
    "find_pivot_lows",
    "find_horizontal_levels",
    "classify_breakout_event",
    "build_structure_snapshot",
    # pipeline
    "STRUCTURE_SCHEMA_SQL",
    "StructureBuildResult",
    "bootstrap_structure_storage",
    "run_structure_build",
]
