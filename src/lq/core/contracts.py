"""核心跨模块合同：枚举、常量、基础类型定义。"""

from __future__ import annotations

from enum import Enum


# ---------------------------------------------------------------------------
# 市场背景层枚举
# ---------------------------------------------------------------------------

class MonthlyState8(str, Enum):
    """月线八态状态机 — MALF 第一层主轴。"""
    BULL_FORMING = "BULL_FORMING"
    BULL_PERSISTING = "BULL_PERSISTING"
    BULL_EXHAUSTING = "BULL_EXHAUSTING"
    BULL_REVERSING = "BULL_REVERSING"
    BEAR_FORMING = "BEAR_FORMING"
    BEAR_PERSISTING = "BEAR_PERSISTING"
    BEAR_EXHAUSTING = "BEAR_EXHAUSTING"
    BEAR_REVERSING = "BEAR_REVERSING"

    @property
    def is_bull(self) -> bool:
        return self.value.startswith("BULL")

    @property
    def is_bear(self) -> bool:
        return self.value.startswith("BEAR")

    @property
    def is_trending(self) -> bool:
        """持续或形成阶段才算趋势主体。"""
        return self in (
            MonthlyState8.BULL_FORMING,
            MonthlyState8.BULL_PERSISTING,
            MonthlyState8.BEAR_FORMING,
            MonthlyState8.BEAR_PERSISTING,
        )


class WeeklyFlowRelation(str, Enum):
    """周线与月线的顺逆关系 — MALF 第二层主轴。"""
    WITH_FLOW = "with_flow"
    AGAINST_FLOW = "against_flow"


class SurfaceLabel(str, Enum):
    """16 格验证框架的四个表面标签。"""
    BULL_MAINSTREAM = "BULL_MAINSTREAM"
    BULL_COUNTERTREND = "BULL_COUNTERTREND"
    BEAR_MAINSTREAM = "BEAR_MAINSTREAM"
    BEAR_COUNTERTREND = "BEAR_COUNTERTREND"

    @classmethod
    def from_monthly_weekly(
        cls,
        monthly: MonthlyState8,
        weekly: WeeklyFlowRelation,
    ) -> "SurfaceLabel":
        """根据月线状态和周线顺逆生成表面标签。"""
        if monthly.is_bull and weekly == WeeklyFlowRelation.WITH_FLOW:
            return cls.BULL_MAINSTREAM
        if monthly.is_bull and weekly == WeeklyFlowRelation.AGAINST_FLOW:
            return cls.BULL_COUNTERTREND
        if monthly.is_bear and weekly == WeeklyFlowRelation.WITH_FLOW:
            return cls.BEAR_MAINSTREAM
        return cls.BEAR_COUNTERTREND


# ---------------------------------------------------------------------------
# PAS 触发层枚举
# ---------------------------------------------------------------------------

class PasTriggerPattern(str, Enum):
    """五个 PAS 触发模式。"""
    BOF = "BOF"   # 假跌破后收回 — 已验证主线可用
    BPB = "BPB"   # 突破后回踩 — 已验证但拒绝主线
    PB = "PB"     # 普通回踩 — 条件格准入
    TST = "TST"   # 测试支撑 — 待独立验证
    CPB = "CPB"   # 压缩后突破 — 待独立验证，定义仍需收敛


class PasTriggerStatus(str, Enum):
    """PAS 触发器业务状态（不是代码状态，是治理状态）。"""
    MAINLINE = "MAINLINE"           # 主线可用
    CONDITIONAL = "CONDITIONAL"    # 条件格准入
    REJECTED = "REJECTED"           # 已验证但拒绝
    PENDING = "PENDING"             # 待独立验证


# PAS 各 trigger 的当前治理状态
PAS_TRIGGER_STATUS: dict[PasTriggerPattern, PasTriggerStatus] = {
    PasTriggerPattern.BOF: PasTriggerStatus.MAINLINE,
    PasTriggerPattern.BPB: PasTriggerStatus.REJECTED,
    PasTriggerPattern.PB: PasTriggerStatus.CONDITIONAL,
    PasTriggerPattern.TST: PasTriggerStatus.CONDITIONAL,  # 辅策略（2020后持续正收益）
    PasTriggerPattern.CPB: PasTriggerStatus.REJECTED,      # 剔除冻结（保留段负收益）
}


# ---------------------------------------------------------------------------
# 结构位枚举（新增）
# ---------------------------------------------------------------------------

class StructureLevelType(str, Enum):
    """结构位类型枚举 — 统一结构位语言的核心分类。"""
    SUPPORT = "SUPPORT"                     # 水平支撑位
    RESISTANCE = "RESISTANCE"               # 水平阻力位
    PIVOT_LOW = "PIVOT_LOW"                 # 波段低点
    PIVOT_HIGH = "PIVOT_HIGH"               # 波段高点
    POST_BREAKOUT_SUPPORT = "POST_BREAKOUT_SUPPORT"       # 突破后形成的新支撑
    POST_BREAKDOWN_RESISTANCE = "POST_BREAKDOWN_RESISTANCE"  # 跌破后形成的新阻力
    TEST_POINT = "TEST_POINT"               # 测试点（回踩触达位）


class BreakoutType(str, Enum):
    """突破事件类型 — 突破家族语义正式分类。"""
    VALID_BREAKOUT = "VALID_BREAKOUT"               # 有效突破
    FALSE_BREAKOUT = "FALSE_BREAKOUT"               # 假突破（BOF 场景）
    TEST = "TEST"                                    # 测试（TST 场景）
    PULLBACK_CONFIRMATION = "PULLBACK_CONFIRMATION" # 突破后回踩确认（BPB/CPB 场景）
    UNKNOWN = "UNKNOWN"                             # 尚未分类


# ---------------------------------------------------------------------------
# 不利条件枚举（新增）
# ---------------------------------------------------------------------------

class AdverseConditionType(str, Enum):
    """不利市场条件类型 — 不做过滤器的语言清单。"""
    COMPRESSION_NO_DIRECTION = "COMPRESSION_NO_DIRECTION"  # 压缩且无方向
    STRUCTURAL_CHAOS = "STRUCTURAL_CHAOS"                  # 结构混乱
    INSUFFICIENT_SPACE = "INSUFFICIENT_SPACE"              # 空间不足
    SIGNAL_CONFLICT = "SIGNAL_CONFLICT"                    # 多重信号冲突
    BACKGROUND_NOT_SUPPORTING = "BACKGROUND_NOT_SUPPORTING"  # 背景不支持


# ---------------------------------------------------------------------------
# 交易管理枚举（新增）
# ---------------------------------------------------------------------------

class TradeLifecycleState(str, Enum):
    """交易管理生命周期状态 — 交易管理模板的核心状态机。"""
    PENDING_ENTRY = "PENDING_ENTRY"         # 等待入场
    ACTIVE_INITIAL_STOP = "ACTIVE_INITIAL_STOP"   # 持有，初始止损保护中
    FIRST_TARGET_HIT = "FIRST_TARGET_HIT"   # 第一目标已达，半仓止盈后
    TRAILING_RUNNER = "TRAILING_RUNNER"     # runner 用跟踪止损保护
    CLOSED_WIN = "CLOSED_WIN"               # 盈利平仓
    CLOSED_LOSS = "CLOSED_LOSS"             # 亏损止损
    CLOSED_TIME = "CLOSED_TIME"             # 时间止损平仓
    CANCELLED = "CANCELLED"                 # 取消（信号失效未入场）


# ---------------------------------------------------------------------------
# 通用常量
# ---------------------------------------------------------------------------

# A 股指数标识
PRIMARY_INDEX_CODE = "000001.SH"       # 上证综指（主基准）
VALIDATION_INDEX_CODES = (
    "000300.SH",   # 沪深300
    "399001.SZ",   # 深证成指
    "399006.SZ",   # 创业板指
    "000688.SH",   # 科创50
)

# 市场背景实体标识（指数池）
MARKET_CONTEXT_ENTITY_CODE = "CN_WIDE_INDEX_POOL"

# A 股交易费率（双边）
COMMISSION_RATE = 0.0003    # 佣金 0.03%
STAMP_DUTY_RATE = 0.0005    # 印花税 0.05%（卖出单边）
TRANSFER_FEE_RATE = 0.00002 # 过户费 0.002%

# 默认资金合同（与 MarketLifespan-Quant 主线保持一致）
DEFAULT_CAPITAL_BASE = 1_000_000.0
DEFAULT_FIXED_NOTIONAL = 100_000.0
DEFAULT_LOT_SIZE = 100  # A 股最小交易单位（手）

# PAS 信号方向
PAS_SIGNAL_SIDE = "LONG"
PAS_SIGNAL_ACTION = "BUY"
