"""P1-02 补丁测试：解释链（StockScanTrace）三件套字段完整性验证。

回归防护：
    - 通过过滤的股票：解释链应包含 tradeable=True + pas_traces（非空）
    - 被过滤的股票：解释链应包含 tradeable=False + adverse_conditions + 空 pas_traces
    - SystemRunSummary.stock_traces 数量应等于实际处理的股票数（跳过/异常除外）
    - 解释链字段通过 run_id + code + signal_date 可联查
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lq.system.orchestration import StockScanTrace, SystemRunSummary


# ---------------------------------------------------------------------------
# StockScanTrace 单元测试
# ---------------------------------------------------------------------------

class TestStockScanTraceContract:
    """验证 StockScanTrace 数据合同自身的正确性。"""

    def _make_trace(self, tradeable: bool, pas_traces=()) -> StockScanTrace:
        return StockScanTrace(
            run_id="scan-2024-06-03-abc",
            code="000001.SZ",
            signal_date=date(2024, 6, 3),
            monthly_state="BULL_PERSISTING",
            surface_label="BULL_MAINSTREAM",
            tradeable=tradeable,
            adverse_conditions=() if tradeable else ("BACKGROUND_NOT_SUPPORTING",),
            adverse_notes="无不利条件" if tradeable else "月线背景不支持",
            pas_traces=pas_traces,
        )

    def test_tradeable_trace_has_pas_traces(self):
        """通过过滤的股票应携带 pas_traces。"""
        dummy_trace = {"pattern": "BOF", "triggered": True, "strength": 0.7}
        trace = self._make_trace(tradeable=True, pas_traces=(dummy_trace,))
        assert trace.tradeable is True
        assert len(trace.pas_traces) == 1
        assert trace.pas_traces[0]["pattern"] == "BOF"

    def test_blocked_trace_has_empty_pas_traces(self):
        """被过滤的股票 pas_traces 应为空。"""
        trace = self._make_trace(tradeable=False)
        assert trace.tradeable is False
        assert trace.pas_traces == ()
        assert len(trace.adverse_conditions) > 0

    def test_as_dict_has_required_keys(self):
        """as_dict() 应输出七个必要字段。"""
        trace = self._make_trace(tradeable=True)
        d = trace.as_dict()
        for key in ("run_id", "code", "signal_date", "monthly_state",
                    "surface_label", "tradeable", "adverse_conditions",
                    "adverse_notes", "pas_traces"):
            assert key in d, f"as_dict() 缺少字段 {key}"

    def test_as_dict_signal_date_is_iso_string(self):
        """as_dict() 中 signal_date 应为 ISO 格式字符串。"""
        trace = self._make_trace(tradeable=True)
        d = trace.as_dict()
        assert d["signal_date"] == "2024-06-03"

    def test_linkable_by_run_id_code_date(self):
        """三元组 (run_id, code, signal_date) 应唯一标识一条解释链记录。"""
        trace = self._make_trace(tradeable=True)
        d = trace.as_dict()
        assert d["run_id"] == "scan-2024-06-03-abc"
        assert d["code"] == "000001.SZ"
        assert d["signal_date"] == "2024-06-03"


# ---------------------------------------------------------------------------
# SystemRunSummary.stock_traces 集成场景
# ---------------------------------------------------------------------------

class TestSystemRunSummaryStockTraces:
    """验证 SystemRunSummary 正确携带解释链列表。"""

    def _make_summary(self, stock_traces: list[dict]) -> SystemRunSummary:
        return SystemRunSummary(
            run_id="scan-2024-06-03-xyz",
            signal_date=date(2024, 6, 3),
            codes_scanned=len(stock_traces),
            codes_filtered_out=sum(1 for t in stock_traces if not t["tradeable"]),
            signals_found=1,
            pattern_counts={"BOF": 1},
            top_signals=[],
            scan_errors=[],
            stock_traces=stock_traces,
        )

    def test_stock_traces_count_matches_scanned(self):
        """stock_traces 数量应与扫描股票数一致。"""
        traces = [
            {"code": "000001.SZ", "tradeable": True,  "pas_traces": [{"pattern": "BOF"}]},
            {"code": "000002.SZ", "tradeable": False, "pas_traces": []},
        ]
        summary = self._make_summary(traces)
        assert len(summary.stock_traces) == 2

    def test_filtered_out_count_matches_traces(self):
        """codes_filtered_out 应等于 tradeable=False 的 trace 数量。"""
        traces = [
            {"code": "000001.SZ", "tradeable": True,  "pas_traces": []},
            {"code": "000002.SZ", "tradeable": False, "pas_traces": []},
            {"code": "000003.SZ", "tradeable": False, "pas_traces": []},
        ]
        summary = self._make_summary(traces)
        assert summary.codes_filtered_out == 2

    def test_as_dict_includes_stock_traces(self):
        """as_dict() 输出应包含 stock_traces 字段。"""
        traces = [{"code": "000001.SZ", "tradeable": True, "pas_traces": []}]
        summary = self._make_summary(traces)
        d = summary.as_dict()
        assert "stock_traces" in d
        assert d["stock_traces"][0]["code"] == "000001.SZ"

    def test_tradeable_trace_preserves_pas_count(self):
        """通过过滤的股票解释链应保留全部 pas_traces（不只是触发的）。"""
        # 5 个触发器，只有 1 个触发，解释链应保存全部 5 个
        pas_traces = [
            {"pattern": "BOF", "triggered": True,  "strength": 0.7},
            {"pattern": "PB",  "triggered": False, "strength": None},
            {"pattern": "TST", "triggered": False, "strength": None},
            {"pattern": "CPB", "triggered": False, "strength": None},
            {"pattern": "BPB", "triggered": False, "strength": None},
        ]
        traces = [{"code": "000001.SZ", "tradeable": True, "pas_traces": pas_traces}]
        summary = self._make_summary(traces)
        assert len(summary.stock_traces[0]["pas_traces"]) == 5
