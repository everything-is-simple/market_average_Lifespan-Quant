"""system — 主线编排、治理检查、回测入口。"""

from .orchestration import run_daily_signal_scan, SystemRunSummary

__all__ = [
    "run_daily_signal_scan",
    "SystemRunSummary",
]
