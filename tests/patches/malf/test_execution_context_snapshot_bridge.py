from __future__ import annotations

"""验证 execution_context_snapshot 桥接落盘合同。"""

from datetime import date

import duckdb

from lq.malf.contracts import MalfContext
from lq.malf.pipeline import _context_to_row, _flush_batch, bootstrap_malf_storage


def test_flush_batch_writes_execution_context_snapshot(tmp_path):
    db_path = tmp_path / "malf.duckdb"
    bootstrap_malf_storage(db_path)

    ctx = MalfContext(
        code="000001.SZ",
        signal_date=date(2024, 6, 3),
        long_background_2="BULL",
        intermediate_role_2="MAINSTREAM",
        malf_context_4="BULL_MAINSTREAM",
        monthly_state="BULL_PERSISTING",
        weekly_flow="with_flow",
        amplitude_rank_low=28,
        amplitude_rank_high=29,
        amplitude_rank_total=281,
        duration_rank_low=10,
        duration_rank_high=11,
        duration_rank_total=281,
        new_price_rank_low=3,
        new_price_rank_high=4,
        new_price_rank_total=281,
        lifecycle_rank_low=41,
        lifecycle_rank_high=44,
        lifecycle_rank_total=843,
        amplitude_quartile="Q1",
        duration_quartile="Q1",
        new_price_quartile="Q1",
        lifecycle_quartile="Q1",
    )

    _flush_batch(db_path, [_context_to_row(ctx)], run_id="malf-run-001")

    with duckdb.connect(str(db_path), read_only=True) as conn:
        row = conn.execute(
            "SELECT entity_scope, entity_code, calc_date, run_id, "
            "       long_background_2, intermediate_role_2, malf_context_4, "
            "       amplitude_rank_low, amplitude_rank_high, amplitude_rank_total, "
            "       ranking_asof_date, contract_version "
            "FROM execution_context_snapshot"
        ).fetchone()

    assert row == (
        "stock",
        "000001.SZ",
        date(2024, 6, 3),
        "malf-run-001",
        "BULL",
        "MAINSTREAM",
        "BULL_MAINSTREAM",
        28,
        29,
        281,
        date(2024, 6, 3),
        "v1",
    )
