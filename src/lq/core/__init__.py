"""core — 公共类型、路径合同、跨模块枚举与常量。"""

from .calendar import is_trading_day, next_trading_day
from .checkpoint import JsonCheckpointStore
from .resumable import (
    build_resume_digest,
    parse_optional_date,
    prepare_resumable_checkpoint,
    resolve_default_checkpoint_path,
    save_resumable_checkpoint,
    stable_json_dumps,
)
from .contracts import (
    AdverseConditionType,
    BreakoutType,
    COMMISSION_RATE,
    DEFAULT_CAPITAL_BASE,
    DEFAULT_FIXED_NOTIONAL,
    DEFAULT_LOT_SIZE,
    MARKET_CONTEXT_ENTITY_CODE,
    MonthlyState8,
    PAS_SIGNAL_ACTION,
    PAS_SIGNAL_SIDE,
    PAS_TRIGGER_STATUS,
    PasTriggerPattern,
    PasTriggerStatus,
    PRIMARY_INDEX_CODE,
    STAMP_DUTY_RATE,
    TRANSFER_FEE_RATE,
    SurfaceLabel,
    StructureLevelType,
    TradeLifecycleState,
    VALIDATION_INDEX_CODES,
    WeeklyFlowRelation,
)
from .paths import (
    DatabasePaths,
    WorkspaceRoots,
    default_settings,
    discover_repo_root,
    tdx_root,
    tushare_token_path,
)

__all__ = [
    # calendar
    "is_trading_day",
    "next_trading_day",
    # checkpoint
    "JsonCheckpointStore",
    # resumable
    "build_resume_digest",
    "parse_optional_date",
    "prepare_resumable_checkpoint",
    "resolve_default_checkpoint_path",
    "save_resumable_checkpoint",
    "stable_json_dumps",
    # contracts — 背景层
    "MonthlyState8",
    "WeeklyFlowRelation",
    "SurfaceLabel",
    # contracts — PAS 触发层
    "PasTriggerPattern",
    "PasTriggerStatus",
    "PAS_TRIGGER_STATUS",
    # contracts — 结构位与过滤
    "StructureLevelType",
    "BreakoutType",
    "AdverseConditionType",
    # contracts — 交易管理
    "TradeLifecycleState",
    # contracts — 常量
    "PRIMARY_INDEX_CODE",
    "VALIDATION_INDEX_CODES",
    "MARKET_CONTEXT_ENTITY_CODE",
    "COMMISSION_RATE",
    "STAMP_DUTY_RATE",
    "TRANSFER_FEE_RATE",
    "DEFAULT_CAPITAL_BASE",
    "DEFAULT_FIXED_NOTIONAL",
    "DEFAULT_LOT_SIZE",
    "PAS_SIGNAL_SIDE",
    "PAS_SIGNAL_ACTION",
    # paths
    "DatabasePaths",
    "WorkspaceRoots",
    "default_settings",
    "discover_repo_root",
    "tdx_root",
    "tushare_token_path",
]
