"""malf — 市场平均寿命框架（Market Average Lifespan Framework）。

三层主轴：
1. monthly_state_8  — 月线八态
2. weekly_flow      — 周线顺逆
3. pas_context      — 日线 PAS 上下文快照
"""

from .contracts import (
    MalfContext,
    MalfContextSnapshot,
    MALFBuildManifest,
    MONTHLY_STATE_8_VALUES,
    WEEKLY_FLOW_RELATION_VALUES,
    CANONICAL_SURFACE_LABELS,
    PAS_TRIGGER_PATTERNS,
    normalize_monthly_state,
    normalize_weekly_flow,
    build_surface_label,
    build_signal_id,
)

__all__ = [
    "MalfContext",
    "MalfContextSnapshot",
    "MALFBuildManifest",
    "MONTHLY_STATE_8_VALUES",
    "WEEKLY_FLOW_RELATION_VALUES",
    "CANONICAL_SURFACE_LABELS",
    "PAS_TRIGGER_PATTERNS",
    "normalize_monthly_state",
    "normalize_weekly_flow",
    "build_surface_label",
    "build_signal_id",
]
