"""MALF 模块数据合同与常量定义。

正式执行主轴：malf_context_4 + 生命周期三轴原始排位 + 四分位辅助。
monthly_state_8 / weekly_flow 保留为计算层诊断字段。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from lq.core.contracts import MonthlyState8, WeeklyFlowRelation, MalfContext4, PasTriggerPattern


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

MONTHLY_STATE_8_VALUES = tuple(s.value for s in MonthlyState8)
WEEKLY_FLOW_RELATION_VALUES = tuple(r.value for r in WeeklyFlowRelation)
MALF_CONTEXT_4_VALUES = tuple(s.value for s in MalfContext4)
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
EXECUTION_CONTEXT_CONTRACT_VERSION = "v1"


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


def build_malf_context_4(monthly_state: str, weekly_flow: str) -> str:
    """根据月线状态和周线顺逆返回四格上下文。"""
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


def derive_long_background_2(monthly_state: str) -> str:
    """从月线八态收敛为执行层长期背景（BULL / BEAR）。"""
    return "BULL" if normalize_monthly_state(monthly_state).startswith("BULL") else "BEAR"


def derive_intermediate_role_2(weekly_flow: str) -> str:
    """从周线顺逆映射为执行层中期角色（MAINSTREAM / COUNTERTREND）。"""
    return "MAINSTREAM" if normalize_weekly_flow(weekly_flow) == "with_flow" else "COUNTERTREND"


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
    """单只股票单日的 MALF 上下文快照。

    执行层主轴：malf_context_4 + 生命周期三轴原始排位 + 四分位辅助。
    计算层诊断：monthly_state / weekly_flow / 日线节奏。
    """

    code: str
    signal_date: date

    # ---- 执行层主字段 ----
    long_background_2: str          # BULL / BEAR（月线收敛）
    intermediate_role_2: str        # MAINSTREAM / COUNTERTREND（周线映射）
    malf_context_4: str             # 四格上下文

    # ---- 计算层诊断字段 ----
    monthly_state: str              # MonthlyState8 值（八态诊断）
    weekly_flow: str                # WeeklyFlowRelation 值（with_flow / against_flow）

    # 辅助评分
    monthly_strength: float | None = None
    weekly_strength: float | None = None

    # 日线节奏（新高日系列，立花义正思想）
    is_new_high_today: bool = False
    new_high_seq: int = 0
    days_since_last_new_high: int | None = None
    new_high_count_in_window: int = 0

    # ---- 生命周期三轴原始排位（排位逻辑待实现，当前默认 None） ----
    amplitude_rank_low: int | None = None
    amplitude_rank_high: int | None = None
    amplitude_rank_total: int | None = None
    duration_rank_low: int | None = None
    duration_rank_high: int | None = None
    duration_rank_total: int | None = None
    new_price_rank_low: int | None = None
    new_price_rank_high: int | None = None
    new_price_rank_total: int | None = None

    # ---- 总生命区间（三轴相加） ----
    lifecycle_rank_low: int | None = None
    lifecycle_rank_high: int | None = None
    lifecycle_rank_total: int | None = None

    # ---- 四分位辅助（晚于排位产生） ----
    amplitude_quartile: str | None = None
    duration_quartile: str | None = None
    new_price_quartile: str | None = None
    lifecycle_quartile: str | None = None

    def __post_init__(self) -> None:
        if self.monthly_state not in MONTHLY_STATE_8_VALUES:
            raise ValueError(f"非法 monthly_state: {self.monthly_state}")
        if self.weekly_flow not in WEEKLY_FLOW_RELATION_VALUES:
            raise ValueError(f"非法 weekly_flow: {self.weekly_flow}")
        if self.malf_context_4 not in MALF_CONTEXT_4_VALUES:
            raise ValueError(f"非法 malf_context_4: {self.malf_context_4}")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MalfContextSnapshot:
    """MALF 上下文批量快照构建摘要。"""

    run_id: str
    asof_date: date
    stock_count: int
    context_counts: dict[str, int]  # malf_context_4 -> count
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "asof_date": self.asof_date.isoformat(),
            "stock_count": self.stock_count,
            "context_counts": self.context_counts,
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
