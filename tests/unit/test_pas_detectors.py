"""PAS 五触发探测器单元测试。"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from lq.alpha.pas.detectors import (
    detect_bof,
    detect_bpb,
    detect_pb,
    detect_tst,
    detect_cpb,
    run_all_detectors,
    MIN_HISTORY,
)
from lq.core.contracts import PasTriggerPattern


def _make_df(
    n_days: int = 60,
    trend: str = "up",
    signal_low_pct: float = 0.97,
    signal_close_pct: float = 1.01,
    last_vol_ratio: float = 1.0,
) -> pd.DataFrame:
    """生成测试日线数据。"""
    base = 10.0
    dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(n_days)]
    rows = []
    for i, d in enumerate(dates):
        if trend == "up":
            price = base + i * 0.05
        elif trend == "down":
            price = base + (n_days - i) * 0.05
        else:
            price = base + np.sin(i / 5) * 0.5

        vol = 1_000_000
        row = {
            "date": d,
            "adj_open": price * 0.995,
            "adj_high": price * 1.02,
            "adj_low": price * 0.98,
            "adj_close": price,
            "volume": int(vol * (last_vol_ratio if i == n_days - 1 else 1.0)),
            "volume_ma20": 1_000_000,
            "ma10": price * 0.99,
            "ma20": price * 0.97,
        }
        rows.append(row)

    # 最后一根K线设置信号特征
    last = rows[-1]
    last["adj_low"] = last["adj_close"] * signal_low_pct
    last["adj_close"] = last["adj_close"] * signal_close_pct

    return pd.DataFrame(rows)


def _make_bof_df(n_days: int = 30) -> pd.DataFrame:
    """生成适合 BOF 触发的测试数据（假跌破后收回）。"""
    df = _make_df(n_days=n_days, trend="up")
    # 构造近期支撑区（多个低点聚集在同一区域）
    base_support = float(df["adj_low"].iloc[-10:-2].mean())

    # 最后一根 K 线：日内跌破支撑，但收盘收回
    last_idx = len(df) - 1
    df.loc[last_idx, "adj_low"] = base_support * 0.97   # 跌破支撑
    df.loc[last_idx, "adj_close"] = base_support * 1.02  # 收回支撑上方
    df.loc[last_idx, "adj_high"] = base_support * 1.05
    df.loc[last_idx, "volume"] = 1_100_000   # 量能正常

    return df


class TestBOFDetector:
    def test_insufficient_history(self):
        df = _make_df(n_days=5)
        trace = detect_bof("000001.SZ", date(2024, 1, 6), df)
        assert trace.triggered is False
        assert trace.skip_reason == "INSUFFICIENT_HISTORY"

    def test_missing_columns(self):
        df = pd.DataFrame({"date": [date(2024, 1, 1)], "adj_close": [10.0]})
        trace = detect_bof("000001.SZ", date(2024, 1, 1), df)
        assert trace.triggered is False
        assert trace.skip_reason is not None and "MISSING_COLUMNS" in trace.skip_reason

    def test_bof_signal_structure(self):
        """验证 BOF 探测器在构造数据上能产出正确结构（不强求触发，只验证结构）。"""
        df = _make_bof_df(n_days=30)
        signal_date = df["date"].iloc[-1]
        trace = detect_bof("000001.SZ", signal_date, df)
        # 无论是否触发，关键字段必须存在
        assert trace.pattern == PasTriggerPattern.BOF.value
        assert trace.signal_id.startswith("PAS_")
        assert isinstance(trace.triggered, bool)
        if trace.triggered:
            assert trace.strength is not None
            assert 0.0 <= trace.strength <= 1.0


class TestPBDetector:
    def test_insufficient_history(self):
        df = _make_df(n_days=5)
        trace = detect_pb("000001.SZ", date(2024, 1, 6), df)
        assert trace.triggered is False
        assert trace.skip_reason == "INSUFFICIENT_HISTORY"

    def test_pb_uptrend_structure(self):
        """PB 在上升趋势中的结构验证。"""
        df = _make_df(n_days=50, trend="up")
        signal_date = df["date"].iloc[-1]
        trace = detect_pb("000001.SZ", signal_date, df)
        assert trace.pattern == PasTriggerPattern.PB.value
        assert isinstance(trace.triggered, bool)

    def test_pb_tracks_pb_sequence(self):
        """PB 触发时应携带 pb_sequence_number。"""
        df = _make_df(n_days=50, trend="up")
        signal_date = df["date"].iloc[-1]
        trace = detect_pb("000001.SZ", signal_date, df)
        if trace.triggered:
            assert trace.pb_sequence_number is not None
            assert trace.pb_sequence_number >= 1


class TestRunAllDetectors:
    def test_returns_all_patterns(self):
        df = _make_df(n_days=70, trend="up")
        signal_date = df["date"].iloc[-1]
        traces = run_all_detectors("000001.SZ", signal_date, df)
        patterns = {t.pattern for t in traces}
        for p in PasTriggerPattern:
            assert p.value in patterns

    def test_returns_correct_count(self):
        df = _make_df(n_days=70, trend="up")
        signal_date = df["date"].iloc[-1]
        traces = run_all_detectors("000001.SZ", signal_date, df)
        assert len(traces) == 5   # 五个 trigger

    def test_subset_patterns(self):
        df = _make_df(n_days=70, trend="up")
        signal_date = df["date"].iloc[-1]
        traces = run_all_detectors(
            "000001.SZ", signal_date, df,
            patterns=["BOF", "PB"]
        )
        assert len(traces) == 2
