"""core 模块单元测试。"""

from __future__ import annotations

import pytest
from pathlib import Path

from lq.core.contracts import (
    MonthlyState8,
    WeeklyFlowRelation,
    SurfaceLabel,
    PasTriggerPattern,
    PasTriggerStatus,
    PAS_TRIGGER_STATUS,
    StructureLevelType,
    BreakoutType,
    AdverseConditionType,
    TradeLifecycleState,
)


class TestMonthlyState8:
    def test_all_values_exist(self):
        values = [s.value for s in MonthlyState8]
        assert "BULL_FORMING" in values
        assert "BULL_PERSISTING" in values
        assert "BULL_EXHAUSTING" in values
        assert "BULL_REVERSING" in values
        assert "BEAR_FORMING" in values
        assert "BEAR_PERSISTING" in values
        assert "BEAR_EXHAUSTING" in values
        assert "BEAR_REVERSING" in values
        assert len(values) == 8

    def test_is_bull(self):
        assert MonthlyState8.BULL_FORMING.is_bull is True
        assert MonthlyState8.BEAR_FORMING.is_bull is False

    def test_is_bear(self):
        assert MonthlyState8.BEAR_PERSISTING.is_bear is True
        assert MonthlyState8.BULL_PERSISTING.is_bear is False

    def test_is_trending(self):
        assert MonthlyState8.BULL_PERSISTING.is_trending is True
        assert MonthlyState8.BULL_EXHAUSTING.is_trending is False


class TestSurfaceLabel:
    def test_from_monthly_weekly_bull_mainstream(self):
        result = SurfaceLabel.from_monthly_weekly(
            MonthlyState8.BULL_PERSISTING,
            WeeklyFlowRelation.WITH_FLOW,
        )
        assert result == SurfaceLabel.BULL_MAINSTREAM

    def test_from_monthly_weekly_bull_countertrend(self):
        result = SurfaceLabel.from_monthly_weekly(
            MonthlyState8.BULL_PERSISTING,
            WeeklyFlowRelation.AGAINST_FLOW,
        )
        assert result == SurfaceLabel.BULL_COUNTERTREND

    def test_from_monthly_weekly_bear_mainstream(self):
        result = SurfaceLabel.from_monthly_weekly(
            MonthlyState8.BEAR_PERSISTING,
            WeeklyFlowRelation.WITH_FLOW,
        )
        assert result == SurfaceLabel.BEAR_MAINSTREAM

    def test_from_monthly_weekly_bear_countertrend(self):
        result = SurfaceLabel.from_monthly_weekly(
            MonthlyState8.BEAR_PERSISTING,
            WeeklyFlowRelation.AGAINST_FLOW,
        )
        assert result == SurfaceLabel.BEAR_COUNTERTREND


class TestPasTriggerStatus:
    def test_bof_is_mainline(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.BOF] == PasTriggerStatus.MAINLINE

    def test_bpb_is_rejected(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.BPB] == PasTriggerStatus.REJECTED

    def test_pb_is_conditional(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.PB] == PasTriggerStatus.CONDITIONAL

    def test_tst_cpb_are_pending(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.TST] == PasTriggerStatus.PENDING
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.CPB] == PasTriggerStatus.PENDING


class TestPaths:
    def test_discover_repo_root(self):
        from lq.core.paths import discover_repo_root
        root = discover_repo_root()
        assert (root / "pyproject.toml").exists()

    def test_default_settings(self):
        from lq.core.paths import default_settings
        ws = default_settings()
        assert ws.repo_root.exists()
        assert ws.data_root is not None
        assert ws.temp_root is not None
        # 检查数据库路径合同
        dbs = ws.databases
        assert dbs.raw_market.name == "raw_market.duckdb"
        assert dbs.market_base.name == "market_base.duckdb"
        assert dbs.research_lab.name == "research_lab.duckdb"
        assert dbs.malf.name == "malf.duckdb"
        assert dbs.trade_runtime.name == "trade_runtime.duckdb"
