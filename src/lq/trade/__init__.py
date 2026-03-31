"""trade — 交易管理模板（A5）与执行 runtime。"""

from .contracts import TradeRecord, TradeRunSummary
from .management import TradeManager, TradeManagementState

__all__ = [
    "TradeRecord",
    "TradeRunSummary",
    "TradeManager",
    "TradeManagementState",
]
