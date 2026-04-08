from __future__ import annotations

"""验证 PAS 准入桥接与兼容字段落盘。"""

from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from lq.alpha.pas.contracts import PasDetectTrace
from lq.alpha.pas.pipeline import run_pas_batch


def _build_market_base_db(db_path: Path, code: str, signal_date: date) -> None:
    rows = []
    start = signal_date - timedelta(days=89)
    price = 10.0
    current = start
    while current <= signal_date:
        rows.append({
            "code": code,
            "trade_date": current,
            "adjust_method": "backward",
            "open": round(price, 4),
            "high": round(price * 1.01, 4),
            "low": round(price * 0.99, 4),
            "close": round(price * 1.002, 4),
            "volume": 1_000_000,
            "amount": 10_000_000,
        })
        current += timedelta(days=1)
        price += 0.05

    df = pd.DataFrame(rows)
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE stock_daily_adjusted (
                code VARCHAR,
                trade_date DATE,
                adjust_method VARCHAR,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount BIGINT
            )
            """
        )
        conn.register("daily_df", df)
        conn.execute("INSERT INTO stock_daily_adjusted SELECT * FROM daily_df")


def _build_malf_db(
    db_path: Path,
    code: str,
    signal_date: date,
    malf_context_4: str,
    monthly_state: str,
    weekly_flow: str,
) -> None:
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE execution_context_snapshot (
                entity_scope VARCHAR,
                entity_code VARCHAR,
                calc_date DATE,
                long_background_2 VARCHAR,
                intermediate_role_2 VARCHAR,
                malf_context_4 VARCHAR,
                amplitude_rank_low INTEGER,
                amplitude_rank_high INTEGER,
                amplitude_rank_total INTEGER,
                duration_rank_low INTEGER,
                duration_rank_high INTEGER,
                duration_rank_total INTEGER,
                new_price_rank_low INTEGER,
                new_price_rank_high INTEGER,
                new_price_rank_total INTEGER,
                lifecycle_rank_low INTEGER,
                lifecycle_rank_high INTEGER,
                lifecycle_rank_total INTEGER,
                amplitude_quartile VARCHAR,
                duration_quartile VARCHAR,
                new_price_quartile VARCHAR,
                lifecycle_quartile VARCHAR
            )
            """
        )
        conn.execute(
            "INSERT INTO execution_context_snapshot VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                "stock",
                code,
                signal_date,
                "BULL",
                "MAINSTREAM" if weekly_flow == "with_flow" else "COUNTERTREND",
                malf_context_4,
                28,
                29,
                281,
                10,
                11,
                281,
                3,
                4,
                281,
                41,
                44,
                843,
                "Q1",
                "Q1",
                "Q1",
                "Q1",
            ],
        )
        conn.execute(
            """
            CREATE TABLE malf_context_snapshot (
                code VARCHAR,
                signal_date DATE,
                malf_context_4 VARCHAR,
                monthly_state VARCHAR,
                weekly_flow VARCHAR
            )
            """
        )
        conn.execute(
            "INSERT INTO malf_context_snapshot VALUES (?, ?, ?, ?, ?)",
            [code, signal_date, malf_context_4, monthly_state, weekly_flow],
        )


def _make_triggered_trace(code: str, signal_date: date, pattern: str) -> PasDetectTrace:
    return PasDetectTrace(
        signal_id=f"PAS_v1_{code}_{signal_date.isoformat()}_{pattern}",
        pattern=pattern,
        triggered=True,
        strength=0.8,
        skip_reason=None,
        detect_reason="patched",
        history_days=120,
        min_history_days=60,
        pb_sequence_number=None,
    )


def _fetch_signal_rows(research_lab_path: Path) -> list[tuple]:
    with duckdb.connect(str(research_lab_path), read_only=True) as conn:
        return conn.execute(
            "SELECT code, pattern, long_background_2, intermediate_role_2, malf_context_4, "
            "       amplitude_rank_low, amplitude_rank_high, amplitude_rank_total, "
            "       lifecycle_rank_low, lifecycle_rank_high, lifecycle_rank_total, "
            "       monthly_state, weekly_flow "
            "FROM pas_formal_signal ORDER BY code"
        ).fetchall()


def test_run_pas_batch_writes_admitted_signal_with_compat_fields(tmp_path, monkeypatch):
    code = "000001.SZ"
    signal_date = date(2024, 6, 3)
    market_base_path = tmp_path / "market_base.duckdb"
    malf_path = tmp_path / "malf.duckdb"
    research_lab_path = tmp_path / "research_lab.duckdb"

    _build_market_base_db(market_base_path, code, signal_date)
    _build_malf_db(
        malf_path,
        code,
        signal_date,
        "BULL_MAINSTREAM",
        "BULL_PERSISTING",
        "with_flow",
    )

    def fake_run_all_detectors(*args, **kwargs):
        return [_make_triggered_trace(code, signal_date, "PB")]

    monkeypatch.setattr("lq.alpha.pas.pipeline.run_all_detectors", fake_run_all_detectors)

    result = run_pas_batch(
        signal_date=signal_date,
        codes=[code],
        market_base_path=market_base_path,
        malf_db_path=malf_path,
        research_lab_path=research_lab_path,
        patterns=["PB"],
    )

    rows = _fetch_signal_rows(research_lab_path)
    assert result.triggered_count == 1
    assert rows == [
        (code, "PB", "BULL", "MAINSTREAM", "BULL_MAINSTREAM", 28, 29, 281, 41, 44, 843, "BULL_PERSISTING", "with_flow")
    ]


def test_run_pas_batch_blocks_rejected_cell(tmp_path, monkeypatch):
    code = "000001.SZ"
    signal_date = date(2024, 6, 3)
    market_base_path = tmp_path / "market_base.duckdb"
    malf_path = tmp_path / "malf.duckdb"
    research_lab_path = tmp_path / "research_lab.duckdb"

    _build_market_base_db(market_base_path, code, signal_date)
    _build_malf_db(
        malf_path,
        code,
        signal_date,
        "BULL_COUNTERTREND",
        "BULL_PERSISTING",
        "against_flow",
    )

    def fake_run_all_detectors(*args, **kwargs):
        return [_make_triggered_trace(code, signal_date, "PB")]

    monkeypatch.setattr("lq.alpha.pas.pipeline.run_all_detectors", fake_run_all_detectors)

    result = run_pas_batch(
        signal_date=signal_date,
        codes=[code],
        market_base_path=market_base_path,
        malf_db_path=malf_path,
        research_lab_path=research_lab_path,
        patterns=["PB"],
    )

    rows = _fetch_signal_rows(research_lab_path)
    assert result.triggered_count == 0
    assert rows == []
