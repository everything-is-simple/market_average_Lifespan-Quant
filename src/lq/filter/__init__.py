"""filter — 不利市场条件过滤器（优先级 A4）。

"不做什么"比"做什么"更值钱。
本模块把"不做"语言冻结为统一过滤合同，供所有 trigger 在进入探测前使用。
"""

from .adverse import (
    AdverseConditionResult,
    check_adverse_conditions,
    is_tradeable,
)
from .pipeline import (
    FILTER_SCHEMA_SQL,
    FilterBuildResult,
    bootstrap_filter_storage,
    run_filter_build,
)

__all__ = [
    "AdverseConditionResult",
    "check_adverse_conditions",
    "is_tradeable",
    # pipeline
    "FILTER_SCHEMA_SQL",
    "FilterBuildResult",
    "bootstrap_filter_storage",
    "run_filter_build",
]
