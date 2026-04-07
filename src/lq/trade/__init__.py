"""trade — 交易管理模板（A5）与执行 runtime。"""

from .contracts import TradeRecord, TradeRunSummary
from .management import TradeManager, TradeManagementState
from .pipeline import (
    TRADE_RUNTIME_SCHEMA_SQL,
    TradeBuildResult,
    bootstrap_trade_storage,
    run_trade_build,
)

__all__ = [
    "TradeRecord",
    "TradeRunSummary",
    "TradeManager",
    "TradeManagementState",
    # pipeline
    "TRADE_RUNTIME_SCHEMA_SQL",
    "TradeBuildResult",
    "bootstrap_trade_storage",
    "run_trade_build",
]
