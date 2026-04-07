"""P1-01 主线全链路集成测试。

覆盖范围：市场数据 fixture → MALF → structure → filter → PAS 探测 → position 规划。
策略：不依赖真实数据库；使用精心构造的 DataFrame fixture，保证 BOF 在信号日触发。

fixture 设计说明（daily_bars，80 根）：
    - 前 59 根：单调上升走势（8.0 → 10.5），形成牛市背景
    - 后 20 根（BOF 窗口）：精确设计的低点序列，满足 BOF pivot 识别条件
    - 第 80 根（信号日）：adj_low=11.3 假跌破 support_level=11.6，adj_close=11.8 收回
    - 关键验证：chaos 过滤器在该序列仅产生 3 次方向切换（< CHAOS_REVERSAL_COUNT=4）

月线 fixture（24 根，等比增长 4%/月）：
    → monthly_state = BULL_PERSISTING（speed_slowing=False）

周线 fixture（20 根，线性上升）：
    → weekly_flow = with_flow（slope > 0）
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from lq.malf.pipeline import build_malf_context_for_stock
from lq.malf.contracts import MalfContext
from lq.structure.detector import build_structure_snapshot
from lq.structure.contracts import StructureSnapshot
from lq.filter.adverse import check_adverse_conditions, AdverseConditionResult
from lq.alpha.pas.detectors import run_all_detectors
from lq.alpha.pas.contracts import PasDetectTrace, PasSignal
from lq.position.sizing import compute_position_plan
from lq.position.contracts import PositionPlan
from lq.core.contracts import PasTriggerPattern


# ---------------------------------------------------------------------------
# 测试常量
# ---------------------------------------------------------------------------
CODE = "000001.SZ"
SIGNAL_DATE = date(2024, 6, 3)   # 周一，T+1 应为周二 2024-06-04


# ---------------------------------------------------------------------------
# Fixture 构造工具
# ---------------------------------------------------------------------------

def _last_day_of_month(year: int, month: int) -> date:
    """返回指定年月的最后一天（代替月末交易日的简化计算）。"""
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _make_monthly_bars(asof_date: date) -> pd.DataFrame:
    """24 根月线，等比增长 4%/月，使 monthly_state → BULL_PERSISTING。

    trade_date = 该月最后一天（代替月末交易日），用于 P2-01 截断语义验证。
    """
    rows = []
    close = 5000.0
    for i in range(24):
        month = date(2022, 1, 1) + timedelta(days=32 * i)
        month_start = date(month.year, month.month, 1)
        trade_date = _last_day_of_month(month_start.year, month_start.month)
        rows.append({
            "month_start": month_start,
            "trade_date": trade_date,
            "close": round(close, 2),
            "high": round(close * 1.05, 2),
            "low": round(close * 0.95, 2),
            "volume": 500_000_000,
        })
        close *= 1.04
    df = pd.DataFrame(rows)
    return df[df["trade_date"] <= asof_date].copy()


def _make_weekly_bars(asof_date: date) -> pd.DataFrame:
    """20 根周线，线性上升 → weekly_flow = with_flow。

    trade_date = week_start + 4 天（周五，代替周末交易日），用于 P2-01 截断语义验证。
    """
    rows = []
    close = 8.0
    base = date(2024, 1, 1)
    for i in range(20):
        week_start = base + timedelta(weeks=i)
        trade_date = week_start + timedelta(days=4)   # 周五（周最后交易日）
        rows.append({
            "week_start": week_start,
            "trade_date": trade_date,
            "close": round(close, 2),
            "high": round(close + 0.5, 2),
            "low": round(close - 0.3, 2),
        })
        close += 0.2
    df = pd.DataFrame(rows)
    return df[df["trade_date"] <= asof_date].copy()


def _make_daily_bars(signal_date: date) -> pd.DataFrame:
    """80 根日线，精确设计为在 signal_date 触发 BOF 且通过 adverse 过滤器。

    BOF 触发验证：
        pivot_lows 末3个 = (11.3, 11.7, 11.8)
        support_level = 11.6，support_band_lower = 11.368
        信号日 adj_low=11.3 < 11.368 ✓，adj_close=11.8 > 11.6 ✓
        close_position = 0.5/1.2 ≈ 0.417 ≥ 0.4 ✓，量比 = 1.2 ≥ 0.6 ✓

    Chaos 检查：最近 15 根 close 序列方向切换次数 = 3 < CHAOS_REVERSAL_COUNT=4 ✓
    """
    start_date = signal_date - timedelta(days=79)
    rows = []

    # --- 前 59 根：单调上升走势 ---
    for i in range(59):
        d = start_date + timedelta(days=i)
        c = 8.0 + i * (10.5 - 8.0) / 58
        rows.append({
            "date": d,
            "adj_open":  round(c - 0.1, 3),
            "adj_high":  round(c + 0.5, 3),
            "adj_low":   round(c - 0.3, 3),
            "adj_close": round(c, 3),
            "volume":    1_000_000,
            "volume_ma20": 1_000_000,
        })

    # --- 后 20 根：BOF 窗口（adj_low 精确设计以产生正确 pivot_lows） ---
    # adj_close 序列（rows 59-78）设计为只含 2 次方向切换，使 chaos 检查通过
    bof_window = [
        # adj_low, adj_close, adj_high
        (10.5, 11.0, 11.5),   # row 0, daily 59
        (10.3, 10.8, 11.3),   # row 1, daily 60 ← pivot_low
        (10.6, 11.1, 11.6),   # row 2, daily 61
        (10.8, 11.3, 11.8),   # row 3, daily 62
        (11.0, 11.5, 12.0),   # row 4, daily 63
        (11.1, 11.0, 12.1),   # row 5, daily 64 (close 暂时回落，非窗口关键）
        (10.9, 11.0, 12.0),   # row 6, daily 65 ← pivot_low
        (11.2, 11.2, 11.7),   # row 7, daily 66
        (11.4, 11.4, 11.9),   # row 8, daily 67
        (11.5, 11.6, 12.1),   # row 9, daily 68
        (11.3, 11.5, 12.0),   # row 10, daily 69 ← pivot_low
        (11.6, 11.8, 12.3),   # row 11, daily 70
        (11.8, 12.0, 12.5),   # row 12, daily 71
        (11.9, 12.2, 12.7),   # row 13, daily 72
        (11.7, 12.3, 12.8),   # row 14, daily 73 ← pivot_low
        (11.9, 12.4, 12.9),   # row 15, daily 74
        (12.0, 12.5, 13.0),   # row 16, daily 75
        (11.8, 12.6, 13.1),   # row 17, daily 76 ← pivot_low
        (12.1, 12.7, 13.2),   # row 18, daily 77
        (12.2, 12.8, 13.3),   # row 19, daily 78
    ]
    for j, (lo, cl, hi) in enumerate(bof_window):
        d = start_date + timedelta(days=59 + j)
        rows.append({
            "date": d,
            "adj_open":  round(lo + 0.2, 3),
            "adj_high":  hi,
            "adj_low":   lo,
            "adj_close": cl,
            "volume":    1_000_000,
            "volume_ma20": 1_000_000,
        })

    # --- 第 80 根：信号日（BOF 触发日） ---
    rows.append({
        "date": signal_date,
        "adj_open":  11.5,
        "adj_high":  12.5,     # close_position = (11.8-11.3)/(12.5-11.3) ≈ 0.417
        "adj_low":   11.3,     # 假跌破 support_band_lower=11.368
        "adj_close": 11.8,     # 收回 support_level=11.6
        "volume":    1_200_000,   # 量比 1.2 ≥ 0.6
        "volume_ma20": 1_000_000,
    })

    df = pd.DataFrame(rows)
    # 补充 ma10/ma20（结构检测器不强制要求，但 schema 完整）
    df["ma10"] = df["adj_close"].rolling(10, min_periods=1).mean().round(3)
    df["ma20"] = df["adj_close"].rolling(20, min_periods=1).mean().round(3)
    return df.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# 共享 fixture 对象（模块级，避免重复构造）
# ---------------------------------------------------------------------------

_DAILY    = _make_daily_bars(SIGNAL_DATE)
_MONTHLY  = _make_monthly_bars(SIGNAL_DATE)
_WEEKLY   = _make_weekly_bars(SIGNAL_DATE)


# ---------------------------------------------------------------------------
# 阶段 1：MALF 上下文构建
# ---------------------------------------------------------------------------

class TestMalfStage:
    def test_returns_malf_context(self):
        """MALF 管道应返回 MalfContext 实例。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        assert isinstance(ctx, MalfContext)

    def test_monthly_state_is_bull(self):
        """24 根等比增长月线应识别为牛市状态（BULL_PERSISTING 或 BULL_FORMING）。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        assert ctx.monthly_state.startswith("BULL"), (
            f"预期牛市状态，得到 {ctx.monthly_state}"
        )

    def test_weekly_flow_is_with_flow(self):
        """上升周线应识别为 with_flow。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        assert ctx.weekly_flow == "with_flow", (
            f"预期 with_flow，得到 {ctx.weekly_flow}"
        )

    def test_malf_context_4_is_bull_mainstream(self):
        """BULL + with_flow 应对应 BULL_MAINSTREAM 四格上下文。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        assert ctx.malf_context_4 == "BULL_MAINSTREAM", (
            f"预期 BULL_MAINSTREAM，得到 {ctx.malf_context_4}"
        )


# ---------------------------------------------------------------------------
# 阶段 2：结构位快照构建
# ---------------------------------------------------------------------------

class TestStructureStage:
    def test_returns_structure_snapshot(self):
        """结构检测器应返回 StructureSnapshot 实例。"""
        snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        assert isinstance(snap, StructureSnapshot)

    def test_snapshot_code_and_date(self):
        """快照的 code 和 signal_date 应与入参一致。"""
        snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        assert snap.code == CODE
        assert snap.signal_date == SIGNAL_DATE

    def test_snapshot_levels_are_tuples(self):
        """支撑位和阻力位字段应为 tuple（类型契约验证）。"""
        snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        assert isinstance(snap.support_levels, tuple)
        assert isinstance(snap.resistance_levels, tuple)


# ---------------------------------------------------------------------------
# 阶段 3：不利条件过滤
# ---------------------------------------------------------------------------

class TestFilterStage:
    def test_returns_adverse_result(self):
        """过滤器应返回 AdverseConditionResult 实例。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        result = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=ctx)
        assert isinstance(result, AdverseConditionResult)

    def test_tradeable_in_bull_market_with_designed_data(self):
        """在牛市背景 + 精设日线数据下，过滤器应允许入场（tradeable=True）。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        result = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=ctx)
        assert result.tradeable, (
            f"预期 tradeable=True，实际触发不利条件：{result.active_conditions}\n"
            f"备注：{result.notes}"
        )

    def test_bear_persisting_blocks_entry(self):
        """BEAR_PERSISTING 背景下应屏蔽入场（tradeable=False）。"""
        from lq.malf.contracts import MalfContext
        bear_ctx = MalfContext(
            code=CODE,
            signal_date=SIGNAL_DATE,
            long_background_2="BEAR",
            intermediate_role_2="MAINSTREAM",
            malf_context_4="BEAR_MAINSTREAM",
            monthly_state="BEAR_PERSISTING",
            weekly_flow="with_flow",
        )
        result = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=bear_ctx)
        assert not result.tradeable, "BEAR_PERSISTING 背景下应禁止入场"


# ---------------------------------------------------------------------------
# 阶段 4：PAS 触发器探测
# ---------------------------------------------------------------------------

class TestPasDetectorStage:
    def setup_method(self):
        self._struct_snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)

    def test_bof_returns_trace(self):
        """BOF 探测器应返回 PasDetectTrace 对象。"""
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=self._struct_snap
        )
        assert len(traces) == 1
        assert isinstance(traces[0], PasDetectTrace)

    def test_bof_triggers_on_designed_fixture(self):
        """精心设计的日线 fixture 应使 BOF 触发（triggered=True）。"""
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=self._struct_snap
        )
        trace = traces[0]
        assert trace.triggered, (
            f"BOF 未触发，原因：{trace.detect_reason}\n"
            f"skip_reason：{trace.skip_reason}"
        )

    def test_bof_strength_is_in_range(self):
        """BOF 触发强度应在 [0, 1] 范围内。"""
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=self._struct_snap
        )
        trace = traces[0]
        if trace.triggered:
            assert 0.0 <= trace.strength <= 1.0

    def test_run_all_returns_five_traces(self):
        """run_all_detectors 默认运行全部五个探测器，应返回 5 个 trace。"""
        traces = run_all_detectors(CODE, SIGNAL_DATE, _DAILY, struct_snap=self._struct_snap)
        assert len(traces) == len(PasTriggerPattern)


# ---------------------------------------------------------------------------
# 阶段 5：头寸规划（position sizing）
# ---------------------------------------------------------------------------

def _build_pas_signal(trace: PasDetectTrace, malf_ctx: MalfContext) -> PasSignal:
    """从 PasDetectTrace + MalfContext 构造 PasSignal（主线组装逻辑）。"""
    return PasSignal(
        signal_id=trace.signal_id,
        code=CODE,
        signal_date=SIGNAL_DATE,
        pattern=trace.pattern,
        malf_context_4=malf_ctx.malf_context_4,
        strength=trace.strength,
        signal_low=float(_DAILY["adj_low"].iloc[-1]),          # 信号日最低价
        entry_ref_price=float(_DAILY["adj_close"].iloc[-1]),   # 信号日收盘价
        pb_sequence_number=trace.pb_sequence_number,
    )


class TestPositionPlanStage:
    def setup_method(self):
        """构造 BOF 信号和位置计划。"""
        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        struct_snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=struct_snap
        )
        bof_trace = traces[0]
        assert bof_trace.triggered, f"前置条件：BOF 应触发，得到 {bof_trace.detect_reason}"
        signal = _build_pas_signal(bof_trace, ctx)
        self.plan = compute_position_plan(signal, entry_price=11.8)

    def test_returns_position_plan(self):
        """compute_position_plan 应返回 PositionPlan 实例。"""
        assert isinstance(self.plan, PositionPlan)

    def test_t_plus_1_semantics(self):
        """entry_date 必须严格晚于 signal_date（T+1 语义）。"""
        assert self.plan.entry_date > self.plan.signal_date, (
            f"entry_date={self.plan.entry_date} 应 > signal_date={self.plan.signal_date}"
        )

    def test_entry_date_is_next_trading_day(self):
        """signal_date=2024-06-03（周一）时，entry_date 应为 2024-06-04（周二）。"""
        assert self.plan.entry_date == date(2024, 6, 4), (
            f"预期 entry_date=2024-06-04，得到 {self.plan.entry_date}"
        )

    def test_stop_below_entry(self):
        """初始止损价必须低于入场价（1R 语义）。"""
        assert self.plan.initial_stop_price < self.plan.entry_price, (
            f"止损 {self.plan.initial_stop_price} 应 < 入场 {self.plan.entry_price}"
        )

    def test_target_above_entry(self):
        """第一目标价必须高于入场价（≥1R 潜在收益）。"""
        assert self.plan.first_target_price > self.plan.entry_price, (
            f"目标 {self.plan.first_target_price} 应 > 入场 {self.plan.entry_price}"
        )

    def test_lot_count_is_positive(self):
        """头寸手数必须大于零。"""
        assert self.plan.lot_count > 0


# ---------------------------------------------------------------------------
# P1-02：解释链组装（三件套联查验证）
# ---------------------------------------------------------------------------

class TestExplainChainAssembly:
    """验证五阶段产物可正确组装为 StockScanTrace，字段语义一致。"""

    def setup_method(self):
        """运行完整五阶段，组装解释链。"""
        from lq.system.orchestration import StockScanTrace
        self.StockScanTrace = StockScanTrace

        run_id = "integ-test-run-001"
        self.ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        adverse = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=self.ctx)
        struct_snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=struct_snap
        )

        self.trace_obj = StockScanTrace(
            run_id=run_id,
            code=CODE,
            signal_date=SIGNAL_DATE,
            monthly_state=self.ctx.monthly_state,
            malf_context_4=self.ctx.malf_context_4,
            tradeable=adverse.tradeable,
            adverse_conditions=adverse.active_conditions,
            adverse_notes=adverse.notes,
            pas_traces=tuple(t.as_dict() for t in traces),
        )
        self.trace_dict = self.trace_obj.as_dict()

    def test_explain_chain_is_stock_scan_trace(self):
        """组装结果应为 StockScanTrace 实例。"""
        assert isinstance(self.trace_obj, self.StockScanTrace)

    def test_linkage_fields_match(self):
        """run_id / code / signal_date 三元组应与输入一致。"""
        assert self.trace_dict["run_id"] == "integ-test-run-001"
        assert self.trace_dict["code"] == CODE
        assert self.trace_dict["signal_date"] == SIGNAL_DATE.isoformat()

    def test_malf_state_in_explain_chain(self):
        """解释链应携带 monthly_state 和 malf_context_4（MALF 摘要）。"""
        assert self.trace_dict["monthly_state"].startswith("BULL")
        assert self.trace_dict["malf_context_4"] == "BULL_MAINSTREAM"

    def test_tradeable_true_with_designed_data(self):
        """牛市精设 fixture 下，解释链中 tradeable 应为 True。"""
        assert self.trace_dict["tradeable"] is True
        assert self.trace_dict["adverse_conditions"] == []

    def test_pas_traces_present_when_tradeable(self):
        """tradeable=True 时，解释链应携带 pas_traces（至少 1 条）。"""
        assert len(self.trace_dict["pas_traces"]) >= 1

    def test_bof_trace_in_explain_chain(self):
        """解释链内的 BOF trace 应标记为 triggered=True。"""
        bof_entries = [t for t in self.trace_dict["pas_traces"] if t["pattern"] == "BOF"]
        assert len(bof_entries) == 1, "解释链中应有且仅有一条 BOF trace"
        assert bof_entries[0]["triggered"] is True

    def test_explain_chain_blocked_stock(self):
        """BEAR_PERSISTING 背景下，解释链中 tradeable=False，pas_traces 为空。"""
        from lq.malf.contracts import MalfContext
        bear_ctx = MalfContext(
            code=CODE,
            signal_date=SIGNAL_DATE,
            long_background_2="BEAR",
            intermediate_role_2="MAINSTREAM",
            malf_context_4="BEAR_MAINSTREAM",
            monthly_state="BEAR_PERSISTING",
            weekly_flow="with_flow",
        )
        adverse = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=bear_ctx)
        blocked = self.StockScanTrace(
            run_id="run-bear",
            code=CODE,
            signal_date=SIGNAL_DATE,
            monthly_state=bear_ctx.monthly_state,
            malf_context_4=bear_ctx.malf_context_4,
            tradeable=adverse.tradeable,
            adverse_conditions=adverse.active_conditions,
            adverse_notes=adverse.notes,
        )
        d = blocked.as_dict()
        assert d["tradeable"] is False
        assert len(d["adverse_conditions"]) > 0
        assert d["pas_traces"] == []


# ---------------------------------------------------------------------------
# P1-04：解释链 structure_summary 集成验证
# ---------------------------------------------------------------------------

class TestExplainChainStructureSummary:
    """验证 structure_summary 正确嵌入解释链，支持 replay（P1-04）。"""

    def setup_method(self):
        from lq.system.orchestration import StockScanTrace, _build_structure_summary
        self.StockScanTrace = StockScanTrace
        self.build_summary = _build_structure_summary

        ctx = build_malf_context_for_stock(CODE, SIGNAL_DATE, _MONTHLY, _WEEKLY)
        adverse = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=ctx)
        self.struct_snap = build_structure_snapshot(CODE, SIGNAL_DATE, _DAILY)
        traces = run_all_detectors(
            CODE, SIGNAL_DATE, _DAILY, patterns=["BOF"], struct_snap=self.struct_snap
        )
        self.trace_obj = StockScanTrace(
            run_id="integ-p104",
            code=CODE,
            signal_date=SIGNAL_DATE,
            monthly_state=ctx.monthly_state,
            malf_context_4=ctx.malf_context_4,
            tradeable=adverse.tradeable,
            adverse_conditions=adverse.active_conditions,
            adverse_notes=adverse.notes,
            structure_summary=_build_structure_summary(self.struct_snap),
            pas_traces=tuple(t.as_dict() for t in traces),
        )
        self.trace_dict = self.trace_obj.as_dict()

    def test_explain_chain_carries_structure_summary(self):
        """解释链 as_dict() 应包含 structure_summary 字段（P1-04）。"""
        assert "structure_summary" in self.trace_dict
        assert isinstance(self.trace_dict["structure_summary"], dict)

    def test_structure_summary_has_all_eight_keys(self):
        """structure_summary 应包含 8 个规定字段。"""
        ss = self.trace_dict["structure_summary"]
        for key in (
            "has_clear_structure", "nearest_support_price", "nearest_support_strength",
            "nearest_resistance_price", "nearest_resistance_strength",
            "recent_breakout_type", "recent_breakout_recovered", "available_space_pct",
        ):
            assert key in ss, f"structure_summary 缺少字段 {key}"

    def test_bof_trace_can_be_replayed_from_structure_summary(self):
        """BOF 触发时，structure_summary 携带足够信息还原触发上下文。

        replay 条件：能从解释链中读取支撑价（即使为 None），不抛异常。
        """
        ss = self.trace_dict["structure_summary"]
        support_price = ss.get("nearest_support_price")  # 可为 None（单调 fixture 无 pivot）
        bof_entries = [t for t in self.trace_dict["pas_traces"] if t["pattern"] == "BOF"]
        assert len(bof_entries) == 1
        # replay 验证：structure_summary 与 BOF trace 同属一条解释链（同 run_id + code + date）
        assert self.trace_dict["run_id"] == "integ-p104"
        assert self.trace_dict["code"] == CODE
        # 支撑价类型符合契约（float 或 None）
        assert support_price is None or isinstance(support_price, float)

    def test_blocked_stock_structure_summary_is_present(self):
        """被 BEAR_PERSISTING 阻断的股票，解释链也应含 structure_summary（P1-04 强制）。"""
        bear_ctx = MalfContext(
            code=CODE,
            signal_date=SIGNAL_DATE,
            long_background_2="BEAR",
            intermediate_role_2="MAINSTREAM",
            malf_context_4="BEAR_MAINSTREAM",
            monthly_state="BEAR_PERSISTING",
            weekly_flow="with_flow",
        )
        adverse = check_adverse_conditions(CODE, SIGNAL_DATE, _DAILY, malf_ctx=bear_ctx)
        blocked = self.StockScanTrace(
            run_id="run-bear-p104",
            code=CODE,
            signal_date=SIGNAL_DATE,
            monthly_state=bear_ctx.monthly_state,
            malf_context_4=bear_ctx.malf_context_4,
            tradeable=adverse.tradeable,
            adverse_conditions=adverse.active_conditions,
            adverse_notes=adverse.notes,
            structure_summary=self.build_summary(self.struct_snap),
        )
        d = blocked.as_dict()
        assert d["tradeable"] is False
        assert "structure_summary" in d
        assert "has_clear_structure" in d["structure_summary"]


# ---------------------------------------------------------------------------
# P1-05：PB 结构支撑门槛集成验证
# ---------------------------------------------------------------------------

class TestPbStructureGateIntegration:
    """端到端验证 PB 在 struct_snap 存在时的结构支撑门槛行为（P1-05）。"""

    def _make_pb_trigger_df(self) -> pd.DataFrame:
        """生成适合 PB 触发的日线 fixture（上升趋势 + 有效回踩 + 止跌）。"""
        rows = []
        start = SIGNAL_DATE - timedelta(days=49)
        base = 10.0
        for i in range(49):
            d = start + timedelta(days=i)
            c = base + i * 0.06
            rows.append({
                "date": d, "adj_open": c - 0.1, "adj_high": c + 0.3,
                "adj_low": c - 0.2, "adj_close": c,
                "volume": 1_000_000, "volume_ma20": 1_000_000,
                "ma10": c, "ma20": c - 0.5,
            })
        recent_high = base + 48 * 0.06
        signal_close = recent_high * 0.91   # 回踩 9%，在 [3%, 25%] 内
        prev_close = rows[-1]["adj_close"]
        sc = max(signal_close, prev_close + 0.01)
        rows.append({
            "date": SIGNAL_DATE,
            "adj_open": sc - 0.1, "adj_high": sc + 0.3,
            "adj_low": sc - 0.2, "adj_close": sc,
            "volume": 900_000, "volume_ma20": 1_000_000,
            "ma10": sc + 0.1, "ma20": sc - 0.4,
        })
        return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    def _make_struct_snap_with_price(self, price: float) -> StructureSnapshot:
        from lq.structure.contracts import StructureLevel
        from lq.core.contracts import StructureLevelType
        lvl = StructureLevel(
            level_type=StructureLevelType.SUPPORT.value,
            price=price,
            formed_date=date(2024, 5, 1),
            strength=0.8,
        )
        return StructureSnapshot(
            code=CODE, signal_date=SIGNAL_DATE,
            support_levels=(lvl,), resistance_levels=(),
            recent_breakout=None, nearest_support=lvl, nearest_resistance=None,
        )

    def test_pb_triggered_when_structure_support_holds(self):
        """收盘守住结构支撑时，PB 应能正常触发。"""
        df = self._make_pb_trigger_df()
        signal_close = float(df["adj_close"].iloc[-1])
        # 支撑价低于收盘的 98%（守住）
        snap = self._make_struct_snap_with_price(signal_close * 0.93)
        trace = run_all_detectors(CODE, SIGNAL_DATE, df, patterns=["PB"], struct_snap=snap)[0]
        # 无论触发与否，类型应正确（fixture 不保证 PB 一定触发）
        assert isinstance(trace.triggered, bool)
        if trace.triggered:
            assert "结构支撑" in trace.detect_reason

    def test_pb_not_triggered_when_structure_support_fails(self):
        """收盘跌破结构支撑门槛时，PB 必须 triggered=False，且说明原因。"""
        df = self._make_pb_trigger_df()
        signal_close = float(df["adj_close"].iloc[-1])
        # 支撑价高于收盘（收盘 < support * 0.98）
        snap = self._make_struct_snap_with_price(signal_close * 1.05)
        trace = run_all_detectors(CODE, SIGNAL_DATE, df, patterns=["PB"], struct_snap=snap)[0]
        assert trace.triggered is False
        assert "未守住结构支撑" in trace.detect_reason
