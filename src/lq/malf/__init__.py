"""malf — 市场平均寿命框架（Market Average Lifespan Framework）。

三层主轴：
1. monthly_state_8  — 月线八态
2. weekly_flow      — 周线顺逆
3. daily_rhythm     — 日线新高日节奏（立花义正思想）
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
from .daily import compute_daily_rhythm
from .pipeline import (
    MALF_SCHEMA_SQL,
    bootstrap_malf_storage,
    build_malf_context_for_stock,
    run_malf_batch,
    run_malf_batch_incremental,
)

__all__ = [
    # contracts — 核心合同
    "MalfContext",
    "MalfContextSnapshot",
    "MALFBuildManifest",
    # contracts — 常量
    "MONTHLY_STATE_8_VALUES",
    "WEEKLY_FLOW_RELATION_VALUES",
    "CANONICAL_SURFACE_LABELS",
    "PAS_TRIGGER_PATTERNS",
    # contracts — 辅助函数
    "normalize_monthly_state",
    "normalize_weekly_flow",
    "build_surface_label",
    "build_signal_id",
    # daily rhythm
    "compute_daily_rhythm",
    # pipeline
    "MALF_SCHEMA_SQL",
    "bootstrap_malf_storage",
    "build_malf_context_for_stock",
    "run_malf_batch",
    "run_malf_batch_incremental",
]
