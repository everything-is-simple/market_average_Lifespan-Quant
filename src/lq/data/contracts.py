"""data 模块数据合同。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class DataSourceType(str, Enum):
    """数据来源类型枚举。

    主线（离线）：
      TDX_LOCAL_DAY  — mootdx 读取通达信本地 .day 文件（原始未复权价）
      TDX_LOCAL_GBBQ — 通达信本地 gbbq 文件（除权除息事件，复权因子来源）

    辅助（在线，仅用于审计/补充）：
      TUSHARE        — tushare HTTP API（adj_factor 审计 / daily_basic / trade_cal）
    """

    TDX_LOCAL_DAY = "tdx_local_day"       # 主线：日线原始价
    TDX_LOCAL_GBBQ = "tdx_local_gbbq"     # 主线：除权除息（复权依据）
    TUSHARE = "tushare"                    # 辅助：复权因子审计 + 基本面数据


def _utc_suffix() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class IncrementalWindow:
    """增量更新时间窗口合同。"""

    window_start: date | None = None
    window_end: date | None = None

    def __post_init__(self) -> None:
        if self.window_start and self.window_end and self.window_start > self.window_end:
            raise ValueError("window_start 不能晚于 window_end。")

    @property
    def is_full_refresh(self) -> bool:
        return self.window_start is None and self.window_end is None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
        }


@dataclass(frozen=True)
class RawIngestManifest:
    """原始数据入库 manifest。"""

    provider_name: str
    dataset_name: str
    status: str
    window: IncrementalWindow = field(default_factory=IncrementalWindow)
    rows_written: int = 0
    run_id: str = field(default_factory=lambda: f"raw-ingest-{_utc_suffix()}-{uuid4().hex[:8]}")

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "provider_name": self.provider_name,
            "dataset_name": self.dataset_name,
            "window_start": self.window.window_start,
            "window_end": self.window.window_end,
            "status": self.status,
            "rows_written": self.rows_written,
        }


@dataclass(frozen=True)
class BaseBuildManifest:
    """基础层构建 manifest（复权价、均线、量比）。"""

    source_name: str
    dataset_name: str
    status: str
    window: IncrementalWindow = field(default_factory=IncrementalWindow)
    rows_written: int = 0
    run_id: str = field(default_factory=lambda: f"base-build-{_utc_suffix()}-{uuid4().hex[:8]}")

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_name": self.source_name,
            "dataset_name": self.dataset_name,
            "window_start": self.window.window_start,
            "window_end": self.window.window_end,
            "status": self.status,
            "rows_written": self.rows_written,
        }
