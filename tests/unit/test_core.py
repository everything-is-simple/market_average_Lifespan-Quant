"""core 模块单元测试。"""

from __future__ import annotations

import json
import pytest
from datetime import date
from pathlib import Path

from lq.core.contracts import (
    MonthlyState8,
    WeeklyFlowRelation,
    MalfContext4,
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


class TestMalfContext4:
    def test_from_monthly_weekly_bull_mainstream(self):
        result = MalfContext4.from_monthly_weekly(
            MonthlyState8.BULL_PERSISTING,
            WeeklyFlowRelation.WITH_FLOW,
        )
        assert result == MalfContext4.BULL_MAINSTREAM

    def test_from_monthly_weekly_bull_countertrend(self):
        result = MalfContext4.from_monthly_weekly(
            MonthlyState8.BULL_PERSISTING,
            WeeklyFlowRelation.AGAINST_FLOW,
        )
        assert result == MalfContext4.BULL_COUNTERTREND

    def test_from_monthly_weekly_bear_mainstream(self):
        result = MalfContext4.from_monthly_weekly(
            MonthlyState8.BEAR_PERSISTING,
            WeeklyFlowRelation.WITH_FLOW,
        )
        assert result == MalfContext4.BEAR_MAINSTREAM

    def test_from_monthly_weekly_bear_countertrend(self):
        result = MalfContext4.from_monthly_weekly(
            MonthlyState8.BEAR_PERSISTING,
            WeeklyFlowRelation.AGAINST_FLOW,
        )
        assert result == MalfContext4.BEAR_COUNTERTREND


class TestPasTriggerStatus:
    def test_bof_is_mainline(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.BOF] == PasTriggerStatus.MAINLINE

    def test_bpb_is_rejected(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.BPB] == PasTriggerStatus.REJECTED

    def test_pb_is_conditional(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.PB] == PasTriggerStatus.CONDITIONAL

    def test_tst_is_conditional(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.TST] == PasTriggerStatus.CONDITIONAL

    def test_cpb_is_rejected(self):
        assert PAS_TRIGGER_STATUS[PasTriggerPattern.CPB] == PasTriggerStatus.REJECTED


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


class TestJsonCheckpointStore:
    """JsonCheckpointStore 单元测试。"""

    def test_exists_false_when_no_file(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        assert store.exists is False

    def test_load_returns_none_when_no_file(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        assert store.load() is None

    def test_save_and_load_roundtrip(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        payload = {"status": "running", "step": 3}
        store.save(payload)
        assert store.exists is True
        loaded = store.load()
        assert loaded == payload

    def test_update_merges_fields(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        store.save({"status": "running", "step": 1})
        store.update(step=2, extra="ok")
        loaded = store.load()
        assert loaded["status"] == "running"
        assert loaded["step"] == 2
        assert loaded["extra"] == "ok"

    def test_clear_removes_file(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        store.save({"x": 1})
        store.clear()
        assert store.exists is False

    def test_clear_on_nonexistent_file_is_silent(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        store = JsonCheckpointStore(tmp_path / "cp.json")
        store.clear()  # 不抛异常

    def test_save_creates_parent_directories(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        deep_path = tmp_path / "a" / "b" / "c" / "cp.json"
        store = JsonCheckpointStore(deep_path)
        store.save({"ok": True})
        assert deep_path.exists()


class TestResumableHelpers:
    """resumable 工具函数单元测试。"""

    def test_stable_json_dumps_sorts_keys(self):
        from lq.core.resumable import stable_json_dumps
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert stable_json_dumps(d1) == stable_json_dumps(d2)

    def test_build_resume_digest_deterministic(self):
        from lq.core.resumable import build_resume_digest
        fp = {"runner": "test", "window": "2026-01"}
        assert build_resume_digest(fp) == build_resume_digest(fp)

    def test_build_resume_digest_length_16(self):
        from lq.core.resumable import build_resume_digest
        digest = build_resume_digest({"x": 1})
        assert len(digest) == 16

    def test_build_resume_digest_differs_on_different_input(self):
        from lq.core.resumable import build_resume_digest
        assert build_resume_digest({"a": 1}) != build_resume_digest({"a": 2})

    def test_resolve_default_checkpoint_path_structure(self, tmp_path):
        from lq.core.resumable import resolve_default_checkpoint_path
        from lq.core.paths import WorkspaceRoots, DatabasePaths
        from lq.core.paths import default_settings
        ws = default_settings()
        p = resolve_default_checkpoint_path(
            settings_root=ws,
            domain="data",
            runner_name="build_l2",
            fingerprint={"window": "2026-01"},
        )
        assert p.suffix == ".json"
        assert "data" in str(p)
        assert "resume" in str(p)
        assert "build_l2_" in p.name

    def test_parse_optional_date_none(self):
        from lq.core.resumable import parse_optional_date
        assert parse_optional_date(None) is None
        assert parse_optional_date("") is None

    def test_parse_optional_date_iso_string(self):
        from lq.core.resumable import parse_optional_date
        result = parse_optional_date("2026-03-31")
        assert result == date(2026, 3, 31)

    def test_save_resumable_checkpoint_injects_fingerprint(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        from lq.core.resumable import save_resumable_checkpoint
        store = JsonCheckpointStore(tmp_path / "cp.json")
        fp = {"runner": "test", "window": "2026"}
        result = save_resumable_checkpoint(store, fingerprint=fp, payload={"status": "done"})
        assert result["fingerprint"] == fp
        assert result["status"] == "done"
        loaded = store.load()
        assert loaded["fingerprint"] == fp

    def test_prepare_resumable_checkpoint_fresh_start(self, tmp_path):
        from lq.core.resumable import prepare_resumable_checkpoint
        from lq.core.paths import default_settings
        ws = default_settings()
        cp_path = tmp_path / "cp.json"
        store, state = prepare_resumable_checkpoint(
            checkpoint_path=cp_path,
            settings_root=ws,
            domain="test",
            runner_name="runner",
            fingerprint={"x": 1},
            resume=False,
            reset_checkpoint=False,
        )
        assert state is None
        assert store.path == cp_path

    def test_prepare_resumable_checkpoint_resume_valid(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        from lq.core.resumable import prepare_resumable_checkpoint
        from lq.core.paths import default_settings
        ws = default_settings()
        cp_path = tmp_path / "cp.json"
        fp = {"x": 1}
        # 先写入一个 running checkpoint
        JsonCheckpointStore(cp_path).save({"fingerprint": fp, "status": "running", "step": 2})
        store, state = prepare_resumable_checkpoint(
            checkpoint_path=cp_path,
            settings_root=ws,
            domain="test",
            runner_name="runner",
            fingerprint=fp,
            resume=True,
            reset_checkpoint=False,
        )
        assert state is not None
        assert state["step"] == 2

    def test_prepare_resumable_checkpoint_fingerprint_mismatch_raises(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        from lq.core.resumable import prepare_resumable_checkpoint
        from lq.core.paths import default_settings
        ws = default_settings()
        cp_path = tmp_path / "cp.json"
        JsonCheckpointStore(cp_path).save({"fingerprint": {"x": 1}, "status": "running"})
        with pytest.raises(ValueError, match="不匹配"):
            prepare_resumable_checkpoint(
                checkpoint_path=cp_path,
                settings_root=ws,
                domain="test",
                runner_name="runner",
                fingerprint={"x": 999},
                resume=True,
                reset_checkpoint=False,
            )

    def test_prepare_resumable_checkpoint_running_without_resume_raises(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        from lq.core.resumable import prepare_resumable_checkpoint
        from lq.core.paths import default_settings
        ws = default_settings()
        cp_path = tmp_path / "cp.json"
        fp = {"x": 1}
        JsonCheckpointStore(cp_path).save({"fingerprint": fp, "status": "running"})
        with pytest.raises(ValueError, match="未完成"):
            prepare_resumable_checkpoint(
                checkpoint_path=cp_path,
                settings_root=ws,
                domain="test",
                runner_name="runner",
                fingerprint=fp,
                resume=False,
                reset_checkpoint=False,
            )

    def test_prepare_resumable_checkpoint_reset_clears(self, tmp_path):
        from lq.core.checkpoint import JsonCheckpointStore
        from lq.core.resumable import prepare_resumable_checkpoint
        from lq.core.paths import default_settings
        ws = default_settings()
        cp_path = tmp_path / "cp.json"
        fp = {"x": 1}
        JsonCheckpointStore(cp_path).save({"fingerprint": fp, "status": "running"})
        store, state = prepare_resumable_checkpoint(
            checkpoint_path=cp_path,
            settings_root=ws,
            domain="test",
            runner_name="runner",
            fingerprint=fp,
            resume=False,
            reset_checkpoint=True,  # 强制清空
        )
        assert state is None
        assert not cp_path.exists()
