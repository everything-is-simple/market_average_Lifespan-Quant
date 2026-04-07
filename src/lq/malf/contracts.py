"""MALF 模块数据合同与常量定义。"""

# 历史兼容说明：
# 当前 MalfContext 合同仍以 monthly_state_8 / weekly_flow / surface_label
# 三层主轴为核心字段。自 016 起，这套三层主轴不再代表 MALF 正确的
# 生命周期执行合同；后续正式方向应改为消费
# malf_context_4 + lifecycle 三轴原始排位（amplitude/duration/new_high_frequency）。
# 现有 MalfContext 保留只为兼容既有 run 与 pipeline。

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from lq.core.contracts import MonthlyState8, WeeklyFlowRelation, SurfaceLabel, PasTriggerPattern


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MONTHLY_STATE_8_VALUES = tuple(s.value for s in MonthlyState8)
WEEKLY_FLOW_RELATION_VALUES = tuple(r.value for r in WeeklyFlowRelation)
CANONICAL_SURFACE_LABELS = tuple(s.value for s in SurfaceLabel)
PAS_TRIGGER_PATTERNS = tuple(p.value for p in PasTriggerPattern)

# 月线阶段判定阈值（来自 MarketLifespan-Quant 验证数据）
BROAD_BULL_REVERSAL_PCT = 0.20         # 宽基指数从低点反弹 20% 即确认牛市反转
BROAD_BULL_MIN_WEEKS = 6               # 牛市行情最小持续周数
BROAD_BULL_MIN_AMOUNT_RATIO = 0.8      # 最小成交额比
BROAD_BULL_STRONG_GAIN_PCT = 45.0      # 强势牛市涨幅阈值
BROAD_BULL_FAST_GAIN_PCT = 30.0        # 快速牛市涨幅阈值
BROAD_BULL_FAST_AMOUNT_RATIO = 1.6     # 快速牛市量能倍数
BROAD_BULL_FAST_MAX_WEEKS = 52         # 快速牛市最大持续周数
BROAD_BULL_MERGE_MAX_BEAR_DRAW_PCT = 35.0  # 合并回调最大下跌
BROAD_BULL_MERGE_MAX_GAP_WEEKS = 26        # 合并牛段最大间隔周数

MONTHLY_LONG_BULL_REVERSAL_PCT = 0.20
MONTHLY_LONG_BEAR_REVERSAL_PCT = 0.18
MONTHLY_LONG_MIN_BAR_COUNT = 2
MONTHLY_LONG_BULL_MIN_DURATION_MONTHS = 6
MONTHLY_LONG_BEAR_MIN_DURATION_MONTHS = 4
MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT = 25.0
MONTHLY_LONG_BEAR_MIN_AMPLITUDE_PCT = 18.0
MONTHLY_VALIDATION_LOOKBACK_MONTHS = 12
MONTHLY_VALIDATION_STRONG_AMOUNT_RATIO = 1.15
MONTHLY_LONG_EXHAUSTION_RATIO = 0.6

# 向后兼容别名
MONTHLY_LONG_REVERSAL_PCT = MONTHLY_LONG_BULL_REVERSAL_PCT
MONTHLY_LONG_MIN_DURATION_MONTHS = MONTHLY_LONG_BULL_MIN_DURATION_MONTHS
MONTHLY_LONG_MIN_AMPLITUDE_PCT = MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT

# MALF 自更新最小样本数
SELF_HISTORY_MIN_SAMPLE_COUNT = 20

# 市场背景实体
MARKET_CONTEXT_ENTITY_CODE = "CN_WIDE_INDEX_POOL"
PRIMARY_LONG_TREND_INDEX_CODE = "000001.SH"
LONG_TREND_VALIDATION_INDEX_CODES = (
    "000300.SH",
    "399001.SZ",
    "399006.SZ",
    "000688.SH",
)
MIN_LONG_TREND_VALIDATION_PASS_COUNT = 2

# PAS 信号合同版本
PAS_CONTRACT_VERSION = "v1"


# ---------------------------------------------------------------------------
# 规范化辅助函数
# ---------------------------------------------------------------------------

_MONTHLY_STATE_ALIAS: dict[str, str] = {
    "CONFIRMED_BULL": "BULL_PERSISTING",
    "CONFIRMED_BEAR": "BEAR_PERSISTING",
}

_WEEKLY_FLOW_ALIAS: dict[str, str] = {
    "MAINSTREAM": "with_flow",
    "COUNTERTREND": "against_flow",
}


def normalize_monthly_state(raw: str) -> str:
    """将历史别名规范化为当前口径。"""
    return _MONTHLY_STATE_ALIAS.get(raw, raw)


def normalize_weekly_flow(raw: str) -> str:
    """将历史别名规范化为当前口径。"""
    return _WEEKLY_FLOW_ALIAS.get(raw, raw)


def build_surface_label(monthly_state: str, weekly_flow: str) -> str:
    """根据月线状态和周线顺逆返回表面标签。"""
    normalized_monthly = normalize_monthly_state(monthly_state)
    normalized_weekly = normalize_weekly_flow(weekly_flow)
    is_bull = normalized_monthly.startswith("BULL")
    is_with = normalized_weekly == "with_flow"
    if is_bull and is_with:
        return "BULL_MAINSTREAM"
    if is_bull and not is_with:
        return "BULL_COUNTERTREND"
    if not is_bull and is_with:
        return "BEAR_MAINSTREAM"
    return "BEAR_COUNTERTREND"


def build_signal_id(
    code: str,
    signal_date: date,
    pattern: str,
    version: str = PAS_CONTRACT_VERSION,
) -> str:
    """构建唯一 PAS 信号 ID。"""
    return f"PAS_{version}_{code}_{signal_date.isoformat()}_{pattern}"


def _utc_suffix() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# MALF 上下文数据类
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MalfContext:
    """单只股票单日的 MALF 三层主轴快照。

    这是模块间传递的核心结果合同，不传内部中间特征。
    """

    code: str
    signal_date: date

    # 第一层：月线八态
    monthly_state: str   # MonthlyState8 值

    # 第二层：周线顺逆
    weekly_flow: str     # WeeklyFlowRelation 值

    # 派生：表面标签（16 格框架中的格子定位）
    surface_label: str   # SurfaceLabel 值

    # 附加评分字段（可选）
    monthly_strength: float | None = None    # 月线强度 0~1
    weekly_strength: float | None = None     # 周线强度 0~1

    # 第三层：日线节奏（新高日系列，立花义正思想）
    # 需要 L2 日线数据；pipeline 集成前默认为空
    is_new_high_today: bool = False          # 当日是否为新高日
    new_high_seq: int = 0                    # window 内第几个新高日（0 = 非新高日）
    days_since_last_new_high: int | None = None  # 距上一个新高日的交易日间距
    new_high_count_in_window: int = 0        # window 内新高日总数量

    def __post_init__(self) -> None:
        # 运行期防御：确保枚举值合法
        if self.monthly_state not in MONTHLY_STATE_8_VALUES:
            raise ValueError(f"非法 monthly_state: {self.monthly_state}")
        if self.weekly_flow not in WEEKLY_FLOW_RELATION_VALUES:
            raise ValueError(f"非法 weekly_flow: {self.weekly_flow}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "monthly_state": self.monthly_state,
            "weekly_flow": self.weekly_flow,
            "surface_label": self.surface_label,
            "monthly_strength": self.monthly_strength,
            "weekly_strength": self.weekly_strength,
            "is_new_high_today": self.is_new_high_today,
            "new_high_seq": self.new_high_seq,
            "days_since_last_new_high": self.days_since_last_new_high,
            "new_high_count_in_window": self.new_high_count_in_window,
        }


@dataclass(frozen=True)
class MalfContextSnapshot:
    """MALF 上下文批量快照构建摘要。"""

    run_id: str
    asof_date: date
    stock_count: int
    surface_counts: dict[str, int]  # surface_label -> count
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "asof_date": self.asof_date.isoformat(),
            "stock_count": self.stock_count,
            "surface_counts": self.surface_counts,
            "status": self.status,
        }


@dataclass(frozen=True)
class MALFBuildManifest:
    """MALF 完整构建 manifest。"""

    status: str
    asof_date: date
    index_count: int = 0
    stock_count: int = 0
    run_id: str = field(
        default_factory=lambda: f"malf-build-{_utc_suffix()}-{uuid4().hex[:8]}"
    )

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "asof_date": self.asof_date.isoformat(),
            "index_count": self.index_count,
            "stock_count": self.stock_count,
        }
