"""不利市场条件过滤器 — 优先级 A4 正式实现。

规则：先通过所有不利条件的检查，才允许进入 trigger 探测阶段。
每个条件独立判断，一旦触发任意一个，当日该股票禁止入场。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from lq.core.contracts import AdverseConditionType
from lq.malf.contracts import MalfContext


# ---------------------------------------------------------------------------
# 过滤参数常量
# ---------------------------------------------------------------------------

# A4-1: 压缩且无方向 — 近 N 日日内振幅收窄且均线走平
COMPRESSION_WINDOW = 10
COMPRESSION_FLAT_THRESHOLD = 0.005     # 均线斜率绝对值 < 0.5% 视为走平
COMPRESSION_RANGE_RATIO = 0.5          # 近期振幅 < 长期振幅的 50% 视为压缩

# A4-2: 结构混乱 — 近期高低点无规律（频繁交替突破高低）
CHAOS_WINDOW = 15
CHAOS_REVERSAL_COUNT = 4               # 15 日内超过 4 次方向切换视为混乱

# A4-3: 空间不足 — 支撑到阻力的空间太小不值得入场
MIN_SPACE_PCT = 0.05                   # 至少 5% 的潜在空间

# A4-4: 多重信号冲突 — 同一个股同日不同触发逻辑给出矛盾信号（暂用跨周期背离代替）

# A4-5: 背景不支持 — 月线/周线背景不支持做多
BEAR_PERSISTING_BLOCK = True           # 熊市持续期间屏蔽所有做多信号
BEAR_FORMING_BLOCK = False             # 熊市初期允许 BOF 信号（逆势尝试，默认关闭）


# ---------------------------------------------------------------------------
# 结果合同
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AdverseConditionResult:
    """单只股票的不利条件检查结果。"""

    code: str
    signal_date: date
    active_conditions: tuple[str, ...]   # 触发的 AdverseConditionType 值
    tradeable: bool                       # True = 无不利条件，可以进入探测
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "signal_date": self.signal_date.isoformat(),
            "active_conditions": list(self.active_conditions),
            "tradeable": self.tradeable,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 各条件检测函数
# ---------------------------------------------------------------------------

def _check_compression_no_direction(
    df: pd.DataFrame,
    compression_window: int = COMPRESSION_WINDOW,
) -> bool:
    """A4-1: 检测压缩且无方向。

    返回 True 表示触发了不利条件（不可交易）。
    """
    if len(df) < compression_window * 2:
        return False

    recent = df.tail(compression_window)
    long_window = df.tail(compression_window * 2).iloc[:compression_window]

    # 振幅对比
    recent_range = float((recent["adj_high"] - recent["adj_low"]).mean())
    long_range = float((long_window["adj_high"] - long_window["adj_low"]).mean())

    if long_range < 1e-9:
        return False

    compression = recent_range < long_range * COMPRESSION_RANGE_RATIO

    # 均线走平（用收盘价线性回归斜率判断）
    closes = recent["adj_close"].values.astype(float)
    if len(closes) >= 2:
        x = np.arange(len(closes), dtype=float)
        slope_abs = abs(float(np.polyfit(x, closes, 1)[0]))
        avg_price = float(np.mean(closes))
        normalized_slope = slope_abs / max(avg_price, 1e-9)
        flat = normalized_slope < COMPRESSION_FLAT_THRESHOLD
    else:
        flat = False

    return compression and flat


def _check_structural_chaos(
    df: pd.DataFrame,
    chaos_window: int = CHAOS_WINDOW,
) -> bool:
    """A4-2: 检测结构混乱（频繁方向切换）。

    返回 True 表示触发了不利条件。
    """
    if len(df) < chaos_window:
        return False

    closes = df.tail(chaos_window)["adj_close"].values.astype(float)
    direction_changes = 0
    for i in range(2, len(closes)):
        prev_dir = closes[i - 1] - closes[i - 2]
        curr_dir = closes[i] - closes[i - 1]
        if prev_dir * curr_dir < 0:  # 方向切换
            direction_changes += 1

    return direction_changes >= CHAOS_REVERSAL_COUNT


def _check_insufficient_space(
    nearest_support_price: float | None,
    nearest_resistance_price: float | None,
    current_price: float,
) -> bool:
    """A4-3: 检测空间不足。

    返回 True 表示触发了不利条件。
    """
    if nearest_support_price is None or nearest_resistance_price is None:
        return False

    if abs(current_price) < 1e-9:
        return False

    space_pct = (nearest_resistance_price - nearest_support_price) / current_price
    return space_pct < MIN_SPACE_PCT


def _check_background_not_supporting(malf_ctx: MalfContext | None) -> bool:
    """A4-5: 检测市场背景不支持做多。

    返回 True 表示触发了不利条件。
    """
    if malf_ctx is None:
        return False

    monthly = malf_ctx.monthly_state

    # 熊市持续阶段屏蔽
    if BEAR_PERSISTING_BLOCK and monthly == "BEAR_PERSISTING":
        return True

    # 熊市形成阶段（可选屏蔽）：BEAR_FORMING_BLOCK=True 时才屏蔽
    if BEAR_FORMING_BLOCK and monthly == "BEAR_FORMING":
        return True

    # 熊市高位逆势反弹背景下（逆流反弹），也屏蔽做多
    if monthly == "BEAR_PERSISTING" and malf_ctx.weekly_flow == "against_flow":
        return True

    return False


# ---------------------------------------------------------------------------
# 主函数：统一运行所有不利条件检查
# ---------------------------------------------------------------------------

def check_adverse_conditions(
    code: str,
    signal_date: date,
    daily_bars: pd.DataFrame,
    malf_ctx: MalfContext | None = None,
    nearest_support_price: float | None = None,
    nearest_resistance_price: float | None = None,
) -> AdverseConditionResult:
    """运行所有不利条件检查，返回检查结果合同。

    参数：
        code                   — 股票代码
        signal_date            — 信号日期
        daily_bars             — 近期日线数据（含 adj_high/adj_low/adj_close）
        malf_ctx               — MALF 上下文快照（可选，用于背景检查）
        nearest_support_price  — 最近支撑位价格（可选，用于空间检查）
        nearest_resistance_price — 最近阻力位价格（可选，用于空间检查）

    返回：
        AdverseConditionResult — 包含所有触发的不利条件
    """
    active: list[str] = []
    note_parts: list[str] = []

    # A4-1: 压缩且无方向
    if not daily_bars.empty and _check_compression_no_direction(daily_bars):
        active.append(AdverseConditionType.COMPRESSION_NO_DIRECTION.value)
        note_parts.append("波动率压缩且均线走平")

    # A4-2: 结构混乱
    if not daily_bars.empty and _check_structural_chaos(daily_bars):
        active.append(AdverseConditionType.STRUCTURAL_CHAOS.value)
        note_parts.append(f"近{CHAOS_WINDOW}日频繁方向切换")

    # A4-3: 空间不足
    if not daily_bars.empty:
        current_price = float(daily_bars.tail(1)["adj_close"].iloc[0]) if not daily_bars.empty else 0.0
        if _check_insufficient_space(nearest_support_price, nearest_resistance_price, current_price):
            active.append(AdverseConditionType.INSUFFICIENT_SPACE.value)
            note_parts.append(f"支撑到阻力空间不足{MIN_SPACE_PCT:.0%}")

    # A4-5: 背景不支持（A4-4 信号冲突暂留为后续实现）
    if _check_background_not_supporting(malf_ctx):
        active.append(AdverseConditionType.BACKGROUND_NOT_SUPPORTING.value)
        monthly = malf_ctx.monthly_state if malf_ctx else "unknown"
        note_parts.append(f"月线背景不支持做多（{monthly}）")

    tradeable = len(active) == 0
    return AdverseConditionResult(
        code=code,
        signal_date=signal_date,
        active_conditions=tuple(active),
        tradeable=tradeable,
        notes="；".join(note_parts) if note_parts else "无不利条件",
    )


def is_tradeable(
    code: str,
    signal_date: date,
    daily_bars: pd.DataFrame,
    malf_ctx: MalfContext | None = None,
    nearest_support_price: float | None = None,
    nearest_resistance_price: float | None = None,
) -> bool:
    """快捷函数：是否可以进入 trigger 探测阶段（无不利条件）。"""
    result = check_adverse_conditions(
        code,
        signal_date,
        daily_bars,
        malf_ctx,
        nearest_support_price,
        nearest_resistance_price,
    )
    return result.tradeable
