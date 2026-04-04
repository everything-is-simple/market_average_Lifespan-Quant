"""PAS 五触发探测器实现。

治理状态（父系统冻结口径）：
    BOF  — core/primary_trend_driver，persisting 四格主力，父系统卡 93
    BPB  — excluded/not_for_long_alpha，永久禁止主线，父系统卡 131
    PB   — conditional/conditional_assist_driver，条件格准入，父系统卡 110/121
    TST  — conditional/conditional_assist_driver，条件格准入，父系统卡 126 ✅
    CPB  — excluded/rejected，三段回测保留段负收益，system 层禁止调用，父系统卡 129/258
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from lq.core.contracts import PasTriggerPattern, BreakoutType
from lq.alpha.pas.contracts import PasDetectTrace, PasSignal
from lq.malf.contracts import build_signal_id
from lq.structure.contracts import StructureSnapshot


# ---------------------------------------------------------------------------
# 通用参数
# ---------------------------------------------------------------------------
EPSILON = 1e-9

# 每个 trigger 的最小历史数据要求（交易日）
MIN_HISTORY = {
    PasTriggerPattern.BOF.value: 21,
    PasTriggerPattern.BPB.value: 26,
    PasTriggerPattern.PB.value: 41,
    PasTriggerPattern.TST.value: 61,
    PasTriggerPattern.CPB.value: 41,
}

# 必须包含的列
REQUIRED_COLUMNS = {"date", "adj_open", "adj_high", "adj_low", "adj_close", "volume", "volume_ma20"}


def _clip(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return float(np.clip(v, lo, hi))


def _check_columns(df: pd.DataFrame) -> set[str]:
    return REQUIRED_COLUMNS - set(df.columns)


def _base_trace(
    code: str,
    signal_date: date,
    pattern: str,
    history_days: int,
) -> dict:
    min_days = MIN_HISTORY[pattern]
    return {
        "signal_id": build_signal_id(code, signal_date, pattern),
        "pattern": pattern,
        "triggered": False,
        "strength": None,
        "skip_reason": None,
        "detect_reason": None,
        "history_days": history_days,
        "min_history_days": min_days,
        "pb_sequence_number": None,
    }


def _insufficient_trace(code: str, signal_date: date, pattern: str, history_days: int) -> PasDetectTrace:
    t = _base_trace(code, signal_date, pattern, history_days)
    t["skip_reason"] = "INSUFFICIENT_HISTORY"
    t["detect_reason"] = "INSUFFICIENT_HISTORY"
    return PasDetectTrace(**t)


def _find_pivot_lows(window: pd.DataFrame) -> list[tuple[int, float]]:
    """识别窗口内的局部低点（左右各看1根）。"""
    lows = window["adj_low"].values.astype(float)
    pivots = []
    for i in range(1, len(lows) - 1):
        if lows[i] <= lows[i - 1] and lows[i] < lows[i + 1]:
            pivots.append((i, lows[i]))
    return pivots


def _count_pb_sequence(df: pd.DataFrame, signal_date: date) -> int | None:
    """统计当前上升波段中已发生的 PB 次数（A3 第一 PB 追踪）。

    简单规则：从最近一个明显低点起，统计向下回踩次数。
    """
    if len(df) < 10:
        return None
    closes = df["adj_close"].values.astype(float)
    # 找到最近20根中的最低点位置（假设从那里开始上升波段）
    recent_20 = closes[-20:]
    swing_start_idx = int(np.argmin(recent_20))
    # 从 swing start 到现在，统计下跌后回升的次数
    pb_count = 0
    going_up = True
    for i in range(swing_start_idx + 1, len(recent_20)):
        if going_up and recent_20[i] < recent_20[i - 1]:
            pb_count += 1
            going_up = False
        elif not going_up and recent_20[i] > recent_20[i - 1]:
            going_up = True
    return max(1, pb_count)


# ---------------------------------------------------------------------------
# BOF 探测器 — 假跌破后收回
# 状态：已验证，主线可用
# ---------------------------------------------------------------------------

def detect_bof(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
    struct_snap: StructureSnapshot | None = None,
) -> PasDetectTrace:
    """BOF（Breakout Failure）探测器。

    触发条件：
    1. 存在明确的支撑区（优先使用 struct_snap.nearest_support；否则由近 20 日低点群推导）
    2. 当日最低价跌破支撑区下沿（假跌破）
    3. 当日收盘价收回支撑区以上（收回确认）
    4. 收盘位置偏强（收在当日价格区间的上半部分）
    5. 量能不过度萎缩（≥ 20日均量的 0.6 倍）

    struct_snap（可选）：
        若 struct_snap.nearest_support 非 None，直接使用其 price 作为规范支撑位，
        跳过内部 pivot 推导。struct_snap.recent_breakout == FALSE_BREAKOUT 时额外
        记录结构层确认信息，并对强度计算加成。
    """
    pattern = PasTriggerPattern.BOF.value
    history_days = len(df)
    min_days = MIN_HISTORY[pattern]

    missing = _check_columns(df)
    if missing:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["skip_reason"] = f"MISSING_COLUMNS:{missing}"
        t["detect_reason"] = f"MISSING_COLUMNS:{missing}"
        return PasDetectTrace(**t)

    if history_days < min_days:
        return _insufficient_trace(code, signal_date, pattern, history_days)

    df = df.sort_values("date").tail(min_days).reset_index(drop=True)
    last = df.iloc[-1]
    window = df.iloc[:-1]  # 不含当日

    adj_low = float(last["adj_low"])
    adj_high = float(last["adj_high"])
    adj_close = float(last["adj_close"])
    volume = float(last["volume"])
    volume_ma20 = float(last["volume_ma20"])

    # 支撑区：优先使用结构模块规范支撑位；否则由近 20 日 pivot 低点推导
    struct_confirmed_bof = False
    if struct_snap is not None and struct_snap.nearest_support is not None:
        support_level = struct_snap.nearest_support.price
        support_band_lower = support_level * 0.98
        # 若结构模块已识别 FALSE_BREAKOUT 且已收回，则视为结构层二次确认
        if (
            struct_snap.recent_breakout is not None
            and struct_snap.recent_breakout.breakout_type == BreakoutType.FALSE_BREAKOUT
            and struct_snap.recent_breakout.recovered
        ):
            struct_confirmed_bof = True
    else:
        pivot_lows = _find_pivot_lows(window.tail(20))
        if not pivot_lows:
            t = _base_trace(code, signal_date, pattern, history_days)
            t["detect_reason"] = "NO_PIVOT_LOW_FOUND"
            return PasDetectTrace(**t)
        support_level = np.mean([p[1] for p in pivot_lows[-3:]])  # 最近3个低点均值
        support_band_lower = support_level * 0.98  # 支撑区下沿（允许 2% 误差）

    # 条件1：日内最低价跌破支撑下沿
    broke_below = adj_low < support_band_lower

    # 条件2：收盘收回支撑区以上
    recovered = adj_close > support_level

    # 条件3：收盘偏强（在当日 K 线区间上 40% 以上）
    bar_range = adj_high - adj_low
    if bar_range < EPSILON:
        close_position = 0.5
    else:
        close_position = (adj_close - adj_low) / bar_range
    strong_close = close_position >= 0.4

    # 条件4：量能不过度萎缩
    volume_ok = volume_ma20 < EPSILON or volume / volume_ma20 >= 0.6

    if broke_below and recovered and strong_close and volume_ok:
        # 强度计算：收盘位置 + 量能 + 穿越深度 + 结构层确认加成
        penetration_depth = (support_level - adj_low) / max(support_level, EPSILON)
        struct_bonus = 0.1 if struct_confirmed_bof else 0.0
        strength = _clip(
            close_position * 0.5
            + min(volume / max(volume_ma20, EPSILON), 2.0) * 0.2
            + min(penetration_depth * 5, 0.3)
            + struct_bonus
        )
        t = _base_trace(code, signal_date, pattern, history_days)
        t["triggered"] = True
        t["strength"] = strength
        struct_note = "（结构层已确认 FALSE_BREAKOUT）" if struct_confirmed_bof else ""
        t["detect_reason"] = (
            f"假跌破支撑({support_level:.2f})并收回{struct_note}，"
            f"收盘位置={close_position:.2f}，"
            f"量比={volume / max(volume_ma20, EPSILON):.2f}"
        )
        return PasDetectTrace(**t)

    reason_parts = []
    if not broke_below:
        reason_parts.append(f"未跌破支撑({support_level:.2f}，当日低={adj_low:.2f})")
    if not recovered:
        reason_parts.append(f"未收回支撑(收盘={adj_close:.2f})")
    if not strong_close:
        reason_parts.append(f"收盘偏弱(位置={close_position:.2f})")
    if not volume_ok:
        reason_parts.append(f"量能萎缩(量比={volume / max(volume_ma20, EPSILON):.2f})")

    t = _base_trace(code, signal_date, pattern, history_days)
    t["detect_reason"] = "；".join(reason_parts) or "未触发"
    return PasDetectTrace(**t)


# ---------------------------------------------------------------------------
# BPB 探测器 — 突破后回踩确认
# 状态：已验证，三年样本拒绝主线
# ---------------------------------------------------------------------------

def detect_bpb(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
) -> PasDetectTrace:
    """BPB（Breakout Pullback）探测器。

    触发条件：
    1. 近 10~26 日内有明确向上突破阻力位的记录
    2. 突破后价格回踩至原阻力位附近（现变支撑）
    3. 当日守住原突破位并开始企稳
    4. 量能确认

    注意：BPB 在三年样本中未通过正式验证，代码保留但主线不启用。
    """
    pattern = PasTriggerPattern.BPB.value
    history_days = len(df)
    min_days = MIN_HISTORY[pattern]

    missing = _check_columns(df)
    if missing:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["skip_reason"] = f"MISSING_COLUMNS:{missing}"
        t["detect_reason"] = f"MISSING_COLUMNS:{missing}"
        return PasDetectTrace(**t)

    if history_days < min_days:
        return _insufficient_trace(code, signal_date, pattern, history_days)

    df = df.sort_values("date").tail(min_days).reset_index(drop=True)
    last = df.iloc[-1]

    adj_close = float(last["adj_close"])
    adj_low = float(last["adj_low"])
    adj_high = float(last["adj_high"])
    volume = float(last["volume"])
    volume_ma20 = float(last["volume_ma20"])

    # 查找近期高点（可能的突破位）
    highs = df["adj_high"].values.astype(float)
    recent_high_idx = int(np.argmax(highs[:-5])) if len(highs) > 5 else 0
    breakout_level = highs[recent_high_idx]

    # 突破位后续价格是否确认突破（收盘超过高点）
    post_breakout = df.iloc[recent_high_idx + 1:]
    if post_breakout.empty:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["detect_reason"] = "无法识别突破后确认阶段"
        return PasDetectTrace(**t)

    confirmed_breakout = any(
        float(row["adj_close"]) > breakout_level * 1.01
        for _, row in post_breakout.iterrows()
    )

    # 当前是否回踩至原突破位附近（允许 3% 误差）
    near_breakout_level = (
        adj_low <= breakout_level * 1.03
        and adj_close >= breakout_level * 0.97
    )

    # 量能
    volume_ok = volume_ma20 < EPSILON or volume / volume_ma20 >= 0.7

    if confirmed_breakout and near_breakout_level and volume_ok:
        bar_range = adj_high - adj_low
        close_pos = (adj_close - adj_low) / max(bar_range, EPSILON)
        strength = _clip(close_pos * 0.6 + min(volume / max(volume_ma20, EPSILON), 2.0) * 0.2)
        t = _base_trace(code, signal_date, pattern, history_days)
        t["triggered"] = True
        t["strength"] = strength
        t["detect_reason"] = (
            f"突破后回踩至 {breakout_level:.2f} 附近并守住，"
            f"量比={volume / max(volume_ma20, EPSILON):.2f}"
        )
        return PasDetectTrace(**t)

    t = _base_trace(code, signal_date, pattern, history_days)
    t["detect_reason"] = (
        f"突破确认={confirmed_breakout}，"
        f"回踩至位={near_breakout_level}，"
        f"量能={volume_ok}"
    )
    return PasDetectTrace(**t)


# ---------------------------------------------------------------------------
# PB 探测器 — 普通回踩
# 状态：已验证，条件格准入
# ---------------------------------------------------------------------------

def detect_pb(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
    struct_snap: StructureSnapshot | None = None,
) -> PasDetectTrace:
    """PB（Pullback）探测器 — 上涨趋势中的正常回踩。

    触发条件：
    1. 近期（20日）整体趋势向上（ma20 向上）
    2. 近 5~10 日出现明显回踩（从近期高点下跌 5%~20%）
    3. 当日出现止跌信号（收盘高于前一日收盘，或收阳线）
    4. 收盘高于关键均线（ma10 或 ma20）
    5. 量能不过度放大（避免下跌趋势延续）

    struct_snap（可选）：
        若 struct_snap.nearest_support 非 None，守住结构支撑是触发的前置門槛：
            adj_close >= nearest_support.price * 0.98
        不满足时直接返回 triggered=False（结构层否决）。
        满足门槛后在强度计算中加成 0.1。
        struct_snap=None 或 nearest_support=None 时保持向后兼容。
    """
    pattern = PasTriggerPattern.PB.value
    history_days = len(df)
    min_days = MIN_HISTORY[pattern]

    missing = _check_columns(df)
    if missing or "ma20" not in df.columns or "ma10" not in df.columns:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["skip_reason"] = "MISSING_COLUMNS"
        t["detect_reason"] = "需要 ma10/ma20 列"
        return PasDetectTrace(**t)

    if history_days < min_days:
        return _insufficient_trace(code, signal_date, pattern, history_days)

    df = df.sort_values("date").tail(min_days).reset_index(drop=True)
    last = df.iloc[-1]
    prev = df.iloc[-2]

    adj_close = float(last["adj_close"])
    adj_low = float(last["adj_low"])
    adj_high = float(last["adj_high"])
    prev_close = float(prev["adj_close"])
    ma10 = float(last["ma10"]) if not pd.isna(last["ma10"]) else None
    ma20 = float(last["ma20"]) if not pd.isna(last["ma20"]) else None
    volume = float(last["volume"])
    volume_ma20 = float(last["volume_ma20"])

    # 近 20 日均线方向
    closes_20 = df["adj_close"].values.astype(float)[-20:]
    trend_up = closes_20[-1] > closes_20[0]

    # 近期高点（不含当日）
    recent_high = float(df["adj_high"].iloc[:-1].max())
    pullback_pct = (recent_high - adj_close) / max(recent_high, EPSILON)

    # 条件判断
    is_trending_up = trend_up
    valid_pullback = 0.03 <= pullback_pct <= 0.25
    stop_falling = adj_close > prev_close
    above_ma = (ma20 is not None and adj_close > ma20 * 0.98) or (
        ma10 is not None and adj_close > ma10 * 0.98
    )
    volume_ok = volume_ma20 < EPSILON or volume / volume_ma20 <= 1.5

    # 第一 PB 追踪
    pb_seq = _count_pb_sequence(df, signal_date)

    # 结构支撑门槛（P1-05）
    # struct_snap 存在且 nearest_support 有效时：守住是触发的前置条件，不是加分项
    struct_support_note = ""
    struct_bonus = 0.0
    if struct_snap is not None and struct_snap.nearest_support is not None:
        support_price = struct_snap.nearest_support.price
        holding_support = adj_close >= support_price * 0.98
        if not holding_support:
            t = _base_trace(code, signal_date, pattern, history_days)
            t["detect_reason"] = (
                f"未守住结构支撑({support_price:.2f})，"
                f"收盘={adj_close:.2f} < 门槛={support_price * 0.98:.2f}"
            )
            return PasDetectTrace(**t)
        struct_support_note = f"，守住结构支撑({support_price:.2f})"
        struct_bonus = 0.1

    if is_trending_up and valid_pullback and stop_falling and above_ma and volume_ok:
        bar_range = adj_high - adj_low
        close_pos = (adj_close - adj_low) / max(bar_range, EPSILON)
        strength = _clip(
            close_pos * 0.4
            + (0.3 if pb_seq == 1 else 0.1)  # 第一 PB 加分
            + (1.0 - pullback_pct / 0.25) * 0.3
            + struct_bonus
        )
        t = _base_trace(code, signal_date, pattern, history_days)
        t["triggered"] = True
        t["strength"] = strength
        t["pb_sequence_number"] = pb_seq
        t["detect_reason"] = (
            f"上升趋势回踩 {pullback_pct:.1%}，"
            f"第{pb_seq}次PB，"
            f"收盘企稳于均线上方{struct_support_note}"
        )
        return PasDetectTrace(**t)

    t = _base_trace(code, signal_date, pattern, history_days)
    t["detect_reason"] = (
        f"趋势向上={is_trending_up}，"
        f"有效回踩={valid_pullback}({pullback_pct:.1%})，"
        f"止跌={stop_falling}，均线上={above_ma}"
    )
    return PasDetectTrace(**t)


# ---------------------------------------------------------------------------
# TST 探测器 — 测试支撑
# 状态：conditional/conditional_assist_driver，条件格准入（父系统卡 126 已冻结）
# ---------------------------------------------------------------------------

def detect_tst(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
) -> PasDetectTrace:
    """TST（Test Support）探测器 — 价格测试支撑后反弹。

    触发条件：
    1. 存在明确的水平支撑区（多次触及的价格带）
    2. 当日最低价触及支撑区（允许 1% 以内穿越）
    3. 当日收盘守住支撑（收回支撑区以上）
    4. 测试动作轻柔（量能偏小，非恐慌性抛售）
    5. 无近期破位历史（支撑区近 5 日未被有效跌破）

    注意：此 trigger 在区间震荡行情中可能更有效（假说，待验证）。
    """
    pattern = PasTriggerPattern.TST.value
    history_days = len(df)
    min_days = MIN_HISTORY[pattern]

    missing = _check_columns(df)
    if missing:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["skip_reason"] = f"MISSING_COLUMNS:{missing}"
        t["detect_reason"] = f"MISSING_COLUMNS:{missing}"
        return PasDetectTrace(**t)

    if history_days < min_days:
        return _insufficient_trace(code, signal_date, pattern, history_days)

    df = df.sort_values("date").tail(min_days).reset_index(drop=True)
    last = df.iloc[-1]

    adj_low = float(last["adj_low"])
    adj_close = float(last["adj_close"])
    adj_high = float(last["adj_high"])
    volume = float(last["volume"])
    volume_ma20 = float(last["volume_ma20"])

    # 在 61 日窗口中找支撑区（低点密集区）
    window = df.iloc[:-1]  # 不含当日
    pivot_lows = _find_pivot_lows(window.tail(40))
    if len(pivot_lows) < 2:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["detect_reason"] = "支撑区不明确（需至少 2 个低点）"
        return PasDetectTrace(**t)

    # 计算支撑区价格（最近 3 个低点的均值和标准差）
    recent_lows = [p[1] for p in pivot_lows[-3:]]
    support_center = float(np.mean(recent_lows))
    support_std = float(np.std(recent_lows))
    support_band_lower = support_center - max(support_std, support_center * 0.01)
    support_band_upper = support_center + max(support_std, support_center * 0.01)

    # 条件1：日内最低价触及支撑区
    touched_support = adj_low <= support_band_upper * 1.01

    # 条件2：收盘守住支撑区以上
    defended = adj_close >= support_band_lower * 0.99

    # 条件3：测试轻柔（量能相对偏小）
    quiet_test = volume_ma20 < EPSILON or volume / volume_ma20 <= 1.2

    # 条件4：近 5 日无破位（不含当日）
    recent_5 = window.tail(5)
    no_recent_break = all(
        float(row["adj_close"]) >= support_band_lower * 0.97
        for _, row in recent_5.iterrows()
    )

    if touched_support and defended and quiet_test and no_recent_break:
        bar_range = adj_high - adj_low
        close_pos = (adj_close - adj_low) / max(bar_range, EPSILON)
        strength = _clip(
            close_pos * 0.5
            + (0.3 if quiet_test else 0.1)
            + (0.2 if no_recent_break else 0.0)
        )
        t = _base_trace(code, signal_date, pattern, history_days)
        t["triggered"] = True
        t["strength"] = strength
        t["detect_reason"] = (
            f"测试支撑区({support_center:.2f})并守住，"
            f"量比={volume / max(volume_ma20, EPSILON):.2f}"
        )
        return PasDetectTrace(**t)

    t = _base_trace(code, signal_date, pattern, history_days)
    t["detect_reason"] = (
        f"触及支撑={touched_support}，"
        f"守住={defended}，"
        f"安静测试={quiet_test}，"
        f"无近期破位={no_recent_break}"
    )
    return PasDetectTrace(**t)


# ---------------------------------------------------------------------------
# CPB 探测器 — 压缩后突破
# 状态：conditional/conditional_assist_driver，条件格准入（父系统卡 129 已冻结）
# ---------------------------------------------------------------------------

def detect_cpb(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
) -> PasDetectTrace:
    """CPB（Compression then Pullback/Breakout）探测器 — 压缩整理后的突破。

    当前实现：把"压缩整理"理解为近期波动率收窄，然后价格向上扩张。

    触发条件：
    1. 近 10~20 日 ATR 或日内振幅显著收窄（压缩阶段）
    2. 当日收盘显著高于压缩区间上沿（向上扩张突破）
    3. 量能放大确认
    4. 收盘偏强

    注意：此定义与书义（复杂回调后的突破）仍有出入，定义待收敛。
    """
    pattern = PasTriggerPattern.CPB.value
    history_days = len(df)
    min_days = MIN_HISTORY[pattern]

    missing = _check_columns(df)
    if missing:
        t = _base_trace(code, signal_date, pattern, history_days)
        t["skip_reason"] = f"MISSING_COLUMNS:{missing}"
        t["detect_reason"] = f"MISSING_COLUMNS:{missing}"
        return PasDetectTrace(**t)

    if history_days < min_days:
        return _insufficient_trace(code, signal_date, pattern, history_days)

    df = df.sort_values("date").tail(min_days).reset_index(drop=True)
    last = df.iloc[-1]

    adj_close = float(last["adj_close"])
    adj_low = float(last["adj_low"])
    adj_high = float(last["adj_high"])
    volume = float(last["volume"])
    volume_ma20 = float(last["volume_ma20"])

    # 计算近 20 日与近 5 日的日内振幅（波动率代理）
    df_window = df.iloc[:-1]
    ranges_20 = (df_window["adj_high"] - df_window["adj_low"]).values.astype(float)
    ranges_5 = ranges_20[-5:]
    avg_range_20 = float(np.mean(ranges_20)) if len(ranges_20) > 0 else 0.0
    avg_range_5 = float(np.mean(ranges_5)) if len(ranges_5) > 0 else 0.0

    # 压缩判断：近 5 日均幅 < 近 20 日均幅的 60%
    compression_present = avg_range_20 > EPSILON and avg_range_5 < avg_range_20 * 0.6

    # 压缩区间上沿（近 5 日高点）
    compression_high = float(df_window.tail(5)["adj_high"].max())

    # 当日突破压缩上沿
    breakout_compression = adj_close > compression_high * 1.005

    # 量能放大
    volume_expand = volume_ma20 < EPSILON or volume / volume_ma20 >= 1.2

    # 收盘偏强
    bar_range = adj_high - adj_low
    close_pos = (adj_close - adj_low) / max(bar_range, EPSILON)
    strong_close = close_pos >= 0.5

    if compression_present and breakout_compression and volume_expand and strong_close:
        strength = _clip(
            close_pos * 0.4
            + min(volume / max(volume_ma20, EPSILON), 3.0) / 3.0 * 0.3
            + 0.3
        )
        t = _base_trace(code, signal_date, pattern, history_days)
        t["triggered"] = True
        t["strength"] = strength
        t["detect_reason"] = (
            f"压缩后突破({compression_high:.2f})，"
            f"量比={volume / max(volume_ma20, EPSILON):.2f}，"
            f"收盘位置={close_pos:.2f}"
        )
        return PasDetectTrace(**t)

    t = _base_trace(code, signal_date, pattern, history_days)
    t["detect_reason"] = (
        f"压缩={compression_present}(5日均幅={avg_range_5:.2f}/20日={avg_range_20:.2f})，"
        f"突破={breakout_compression}，量放大={volume_expand}"
    )
    return PasDetectTrace(**t)


# ---------------------------------------------------------------------------
# 批量运行所有探测器
# ---------------------------------------------------------------------------

def run_all_detectors(
    code: str,
    signal_date: date,
    df: pd.DataFrame,
    patterns: list[str] | None = None,
    struct_snap: StructureSnapshot | None = None,
) -> list[PasDetectTrace]:
    """对单只股票运行指定（或全部）PAS 探测器。

    struct_snap（可选）：
        传入结构位快照，由 BOF 和 PB 显式消费（上游化）。
        其他探测器（BPB/TST/CPB）暂不消费，接口预留以备后续扩展。
    """
    all_patterns = patterns or [p.value for p in PasTriggerPattern]
    results = []
    for pattern in all_patterns:
        if pattern == PasTriggerPattern.BOF.value:
            results.append(detect_bof(code, signal_date, df, struct_snap=struct_snap))
        elif pattern == PasTriggerPattern.PB.value:
            results.append(detect_pb(code, signal_date, df, struct_snap=struct_snap))
        elif pattern == PasTriggerPattern.BPB.value:
            results.append(detect_bpb(code, signal_date, df))
        elif pattern == PasTriggerPattern.TST.value:
            results.append(detect_tst(code, signal_date, df))
        elif pattern == PasTriggerPattern.CPB.value:
            results.append(detect_cpb(code, signal_date, df))
    return results
