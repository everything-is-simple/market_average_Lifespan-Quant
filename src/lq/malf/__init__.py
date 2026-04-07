"""malf — 趋势生命周期经验统计系统（Market Average Lifespan Framework）。

正式设计方向：
  上下文分类（malf_context_4）→ 生命周期三轴排位（amplitude/duration/new_price）→ 四分位压缩。
  当前代码仅实现计算层（月线八态 / 周线顺逆 / 日线节奏），执行层桥表待实现。
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
    MalfBuildResult,
    bootstrap_malf_storage,
    build_malf_context_for_stock,
    list_stock_codes,
    list_trading_dates,
    run_malf_build,
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
    "MalfBuildResult",
    "bootstrap_malf_storage",
    "build_malf_context_for_stock",
    "list_stock_codes",
    "list_trading_dates",
    "run_malf_build",
]
