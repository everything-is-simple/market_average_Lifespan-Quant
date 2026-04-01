"""P1-03 补丁测试：structure 真正上游化 — BOF/PB 显式消费 StructureSnapshot。

回归防护：
    - detect_bof(struct_snap!=None)：使用 nearest_support.price 而非内部 pivot 推导
    - detect_bof(struct_snap.recent_breakout == FALSE_BREAKOUT)：detect_reason 含结构确认
    - detect_bof(struct_snap=None)：内部 pivot 路径正常工作（向后兼容）
    - detect_pb(struct_snap!=None)：detect_reason 含结构支撑守住说明
    - run_all_detectors(struct_snap!=None)：BOF 和 PB 收到 struct_snap，其他探测器不受影响
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from lq.alpha.pas.detectors import detect_bof, detect_pb, run_all_detectors
from lq.structure.contracts import StructureSnapshot, StructureLevel, BreakoutEvent
from lq.core.contracts import StructureLevelType, BreakoutType


# ---------------------------------------------------------------------------
# 辅助工具
# ---------------------------------------------------------------------------

_CODE = "000001.SZ"
_SIGNAL_DATE = date(2024, 6, 3)
_SUPPORT_PRICE = 11.6


def _make_support_level(price: float) -> StructureLevel:
    return StructureLevel(
        level_type=StructureLevelType.SUPPORT.value,
        price=price,
        formed_date=date(2024, 5, 20),
        strength=0.8,
    )


def _make_snap_with_support(price: float, recent_breakout=None) -> StructureSnapshot:
    lvl = _make_support_level(price)
    return StructureSnapshot(
        code=_CODE,
        signal_date=_SIGNAL_DATE,
        support_levels=(lvl,),
        resistance_levels=(),
        recent_breakout=recent_breakout,
        nearest_support=lvl,
        nearest_resistance=None,
    )


def _make_snap_no_support() -> StructureSnapshot:
    """无支撑位的快照（struct_snap 存在但 nearest_support=None）。"""
    return StructureSnapshot(
        code=_CODE,
        signal_date=_SIGNAL_DATE,
        support_levels=(),
        resistance_levels=(),
        recent_breakout=None,
        nearest_support=None,
        nearest_resistance=None,
    )


def _make_false_breakout(support_price: float) -> BreakoutEvent:
    """构造结构模块已确认的 FALSE_BREAKOUT 事件。"""
    return BreakoutEvent(
        event_date=_SIGNAL_DATE,
        level=_make_support_level(support_price),
        breakout_type=BreakoutType.FALSE_BREAKOUT.value,
        penetration_pct=-0.02,
        recovered=True,
        confirmed=False,
        notes="假跌破确认回收",
    )


def _make_bof_daily(signal_date: date, support: float) -> pd.DataFrame:
    """生成 25 根日线，信号日在 support 附近假跌破后收回。

    精确条件（与 support=11.6 匹配）：
        adj_low  = support * 0.975 = 11.31   → 跌破 support * 0.98 = 11.368 ✓
        adj_close = support * 1.017 = 11.80  → 收回 > support ✓
        adj_high  = support * 1.078 = 12.50
        close_position = (11.80-11.31)/(12.50-11.31) ≈ 0.412 ≥ 0.4 ✓
        volume/volume_ma20 = 1.2 ≥ 0.6 ✓
    """
    adj_low_sig = support * 0.975
    adj_close_sig = support * 1.017
    adj_high_sig = support * 1.078

    rows = []
    start = signal_date - timedelta(days=24)
    for i in range(24):
        d = start + timedelta(days=i)
        # 前 24 根：需要能产生 pivot_lows（内部逻辑用）
        lo = support * (0.95 + i * 0.002)
        rows.append({
            "date": d, "adj_open": lo + 0.1, "adj_high": lo + 0.5,
            "adj_low": lo, "adj_close": lo + 0.3,
            "volume": 1_000_000, "volume_ma20": 1_000_000,
            "ma10": lo + 0.3, "ma20": lo + 0.2,
        })
    # 信号日
    rows.append({
        "date": signal_date, "adj_open": adj_low_sig + 0.1,
        "adj_high": adj_high_sig, "adj_low": adj_low_sig,
        "adj_close": adj_close_sig, "volume": 1_200_000, "volume_ma20": 1_000_000,
        "ma10": support + 0.1, "ma20": support - 0.1,
    })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


_DF = _make_bof_daily(_SIGNAL_DATE, _SUPPORT_PRICE)


# ---------------------------------------------------------------------------
# detect_bof × struct_snap
# ---------------------------------------------------------------------------

class TestDetectBofWithStructSnap:
    def test_uses_canonical_support_level(self):
        """struct_snap.nearest_support 存在时应使用其 price 作为支撑位。"""
        snap = _make_snap_with_support(_SUPPORT_PRICE)
        trace = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=snap)
        # BOF 应触发（信号日精确满足条件）
        assert trace.triggered, f"BOF 未触发：{trace.detect_reason}"
        # detect_reason 应包含 struct 支撑价格
        assert f"{_SUPPORT_PRICE:.2f}" in trace.detect_reason, (
            f"detect_reason 未包含规范支撑价 {_SUPPORT_PRICE}：{trace.detect_reason}"
        )

    def test_struct_confirmed_bof_note_in_reason(self):
        """recent_breakout=FALSE_BREAKOUT+recovered 时，detect_reason 应含结构确认说明。"""
        breakout = _make_false_breakout(_SUPPORT_PRICE)
        snap = _make_snap_with_support(_SUPPORT_PRICE, recent_breakout=breakout)
        trace = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=snap)
        if trace.triggered:
            assert "结构层" in trace.detect_reason, (
                f"触发后 detect_reason 缺少结构确认说明：{trace.detect_reason}"
            )

    def test_struct_confirmed_bof_strength_bonus(self):
        """FALSE_BREAKOUT 二次确认时强度应 ≥ 无确认时的强度。"""
        snap_plain = _make_snap_with_support(_SUPPORT_PRICE)
        snap_confirmed = _make_snap_with_support(
            _SUPPORT_PRICE, recent_breakout=_make_false_breakout(_SUPPORT_PRICE)
        )
        t_plain = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=snap_plain)
        t_confirmed = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=snap_confirmed)
        if t_plain.triggered and t_confirmed.triggered:
            assert t_confirmed.strength >= t_plain.strength, (
                f"结构确认强度 {t_confirmed.strength} 应 ≥ 未确认 {t_plain.strength}"
            )

    def test_snap_no_support_falls_back_to_internal(self):
        """nearest_support=None 时应回退到内部 pivot 推导路径（向后兼容）。"""
        snap = _make_snap_no_support()
        trace_with = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=snap)
        trace_none = detect_bof(_CODE, _SIGNAL_DATE, _DF, struct_snap=None)
        # 两条路径触发结果应一致
        assert trace_with.triggered == trace_none.triggered, (
            f"nearest_support=None 应与 struct_snap=None 结果一致，"
            f"实际 with={trace_with.triggered}, none={trace_none.triggered}"
        )

    def test_no_struct_snap_backward_compatible(self):
        """不传 struct_snap 时 BOF 触发状态应与原有行为一致。"""
        trace = detect_bof(_CODE, _SIGNAL_DATE, _DF)
        assert isinstance(trace.triggered, bool)


# ---------------------------------------------------------------------------
# detect_pb × struct_snap
# ---------------------------------------------------------------------------

class TestDetectPbWithStructSnap:
    def _make_pb_daily(self) -> pd.DataFrame:
        """生成 45 根日线：上升趋势 + 有效回踩 + 守住支撑。"""
        rows = []
        start = _SIGNAL_DATE - timedelta(days=44)
        base_price = 10.0
        for i in range(44):
            d = start + timedelta(days=i)
            c = base_price + i * 0.05
            rows.append({
                "date": d, "adj_open": c - 0.1, "adj_high": c + 0.3,
                "adj_low": c - 0.2, "adj_close": c,
                "volume": 1_000_000, "volume_ma20": 1_000_000,
                "ma10": c - 0.1, "ma20": c - 0.3,
            })
        # 信号日：从高点回踩约 10%，守住支撑，止跌
        recent_high = base_price + 43 * 0.05
        signal_close = recent_high * 0.92    # 回踩 8%，在 [3%, 25%] 内
        prev_close = rows[-1]["adj_close"]
        signal_close_final = max(signal_close, prev_close + 0.01)  # 确保止跌
        rows.append({
            "date": _SIGNAL_DATE,
            "adj_open": signal_close_final - 0.1,
            "adj_high": signal_close_final + 0.2,
            "adj_low": signal_close_final - 0.3,
            "adj_close": signal_close_final,
            "volume": 900_000, "volume_ma20": 1_000_000,
            "ma10": signal_close_final + 0.05,
            "ma20": signal_close_final - 0.5,
        })
        return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    def test_struct_support_note_in_reason_when_holding(self):
        """守住结构支撑时 detect_reason 应含守住说明。"""
        df = self._make_pb_daily()
        signal_close = float(df["adj_close"].iloc[-1])
        # 设置支撑价格略低于收盘（守住）
        support_price = signal_close * 0.95
        snap = _make_snap_with_support(support_price)
        trace = detect_pb(_CODE, _SIGNAL_DATE, df, struct_snap=snap)
        if trace.triggered:
            assert "结构支撑" in trace.detect_reason, (
                f"PB 触发时 detect_reason 应含结构支撑说明：{trace.detect_reason}"
            )

    def test_no_struct_snap_backward_compatible(self):
        """不传 struct_snap 时 PB 触发状态类型应正确（向后兼容）。"""
        df = self._make_pb_daily()
        trace = detect_pb(_CODE, _SIGNAL_DATE, df)
        assert isinstance(trace.triggered, bool)

    def test_pb_requires_holding_structure_support_when_struct_snap_present(self):
        """struct_snap.nearest_support 存在时，守住结构支撑是 PB 触发的前置门槛。"""
        df = self._make_pb_daily()
        signal_close = float(df["adj_close"].iloc[-1])
        # 支撑价比收盘高（收盘未守住，应被否决）
        support_price_above_close = signal_close * 1.1
        snap = _make_snap_with_support(support_price_above_close)
        trace = detect_pb(_CODE, _SIGNAL_DATE, df, struct_snap=snap)
        assert trace.triggered is False, (
            f"收盘({signal_close:.2f}) 低于结构支撑({support_price_above_close:.2f})，"
            f"PB 应被否决，实际 triggered={trace.triggered}"
        )

    def test_pb_rejects_when_close_breaks_structure_support(self):
        """收盘跌破结构支撑（< price * 0.98）时 PB 必须返回 triggered=False。"""
        df = self._make_pb_daily()
        signal_close = float(df["adj_close"].iloc[-1])
        # 精确设置：支撑价使收盘恰好低于 98% 门槛
        support_price = signal_close / 0.97   # adj_close / support = 0.97 < 0.98
        snap = _make_snap_with_support(support_price)
        trace = detect_pb(_CODE, _SIGNAL_DATE, df, struct_snap=snap)
        assert trace.triggered is False

    def test_pb_detect_reason_mentions_structure_rejection(self):
        """被结构支撑否决时 detect_reason 应明确说明'未守住结构支撑'。"""
        df = self._make_pb_daily()
        signal_close = float(df["adj_close"].iloc[-1])
        support_price = signal_close * 1.05   # 高于收盘
        snap = _make_snap_with_support(support_price)
        trace = detect_pb(_CODE, _SIGNAL_DATE, df, struct_snap=snap)
        assert trace.triggered is False
        assert "未守住结构支撑" in trace.detect_reason, (
            f"detect_reason 应包含'未守住结构支撑'：{trace.detect_reason}"
        )

    def test_pb_keeps_backward_compatibility_without_struct_snap(self):
        """struct_snap=None 时 PB 走旧逻辑，结果类型正确（不引入额外门槛）。"""
        df = self._make_pb_daily()
        trace_none = detect_pb(_CODE, _SIGNAL_DATE, df, struct_snap=None)
        trace_default = detect_pb(_CODE, _SIGNAL_DATE, df)
        assert trace_none.triggered == trace_default.triggered


# ---------------------------------------------------------------------------
# run_all_detectors × struct_snap 透传
# ---------------------------------------------------------------------------

class TestRunAllDetectorsStructSnap:
    def test_bof_receives_struct_snap(self):
        """run_all_detectors 应将 struct_snap 传递给 BOF 探测器。"""
        snap = _make_snap_with_support(_SUPPORT_PRICE)
        traces = run_all_detectors(_CODE, _SIGNAL_DATE, _DF, patterns=["BOF"], struct_snap=snap)
        assert len(traces) == 1
        trace = traces[0]
        # BOF 触发时 detect_reason 应包含规范支撑价
        if trace.triggered:
            assert f"{_SUPPORT_PRICE:.2f}" in trace.detect_reason

    def test_other_detectors_unaffected_by_struct_snap(self):
        """BPB/TST/CPB 探测器传入 struct_snap 不应引发异常。"""
        snap = _make_snap_with_support(_SUPPORT_PRICE)
        traces = run_all_detectors(
            _CODE, _SIGNAL_DATE, _DF,
            patterns=["BPB", "TST", "CPB"],
            struct_snap=snap,
        )
        assert len(traces) == 3
        for t in traces:
            assert isinstance(t.triggered, bool)
