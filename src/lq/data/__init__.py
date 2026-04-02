"""data — 市场数据采集、清洗、落盘、增量更新。"""

from .bootstrap import (
    RAW_MARKET_SCHEMA_STATEMENTS,
    MARKET_BASE_SCHEMA_STATEMENTS,
    bootstrap_data_storage,
)
from .contracts import (
    BaseBuildManifest,
    DataSourceType,
    IncrementalWindow,
    RawIngestManifest,
)

__all__ = [
    # bootstrap
    "RAW_MARKET_SCHEMA_STATEMENTS",
    "MARKET_BASE_SCHEMA_STATEMENTS",
    "bootstrap_data_storage",
    # contracts
    "BaseBuildManifest",
    "DataSourceType",
    "IncrementalWindow",
    "RawIngestManifest",
]
