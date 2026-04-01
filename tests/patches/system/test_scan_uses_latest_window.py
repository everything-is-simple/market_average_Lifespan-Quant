"""P0-01 补丁测试：扫描窗口必须使用最近 N 根日线，而非最早 N 根。

回归防护：
    给定 200 根日线数据，进入 detector 的最后一根必须是 signal_date 当天。
    窗口长度正确（不多不少，<=120 根）。

由于 orchestration.py 直接依赖 DuckDB 数据库，此测试通过 mock 隔离 DB 调用，
只测试"查询语义"（排序方向）和"窗口裁剪"逻辑。
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lq.system.orchestration import run_daily_signal_scan


def _make_daily_df(n: int, signal_date: date) -> pd.DataFrame:
    """构造 n 根升序日线 DataFrame，最后一根是 signal_date。"""
    dates = [signal_date - timedelta(days=n - 1 - i) for i in range(n)]
    return pd.DataFrame({
        "date": dates,
        "adj_open":  [10.0] * n,
        "adj_high":  [10.5] * n,
        "adj_low":   [9.5] * n,
        "adj_close": [10.0 + i * 0.01 for i in range(n)],
        "volume":    [1_000_000] * n,
        "volume_ma20": [1_000_000] * n,
        "ma10":      [10.0] * n,
        "ma20":      [10.0] * n,
    })


class TestScanUsesLatestWindow:
    def test_last_bar_is_signal_date(self):
        """进入 detector 的数据最后一根必须是 signal_date 当日。"""
        signal_date = date(2024, 6, 28)
        captured_df: list[pd.DataFrame] = []

        # 构造模拟查询结果：200 根数据按 DESC 顺序（数据库返回顺序）
        mock_df_desc = _make_daily_df(200, signal_date).sort_values("date", ascending=False).reset_index(drop=True)

        def fake_build_structure(code, sd, df):
            captured_df.append(df.copy())
            # 返回一个最小合法快照避免后续崩溃
            from lq.structure.contracts import StructureSnapshot
            return StructureSnapshot(
                code=code, signal_date=sd,
                pivot_highs=[], pivot_lows=[],
                support_levels=[], resistance_levels=[],
                nearest_support=None, nearest_resistance=None,
                latest_breakout=None,
            )

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.df.side_effect = [
            mock_df_desc,
            pd.DataFrame(),  # monthly_bar（空）
            pd.DataFrame(),  # weekly_bar（空）
        ]

        with (
            patch("lq.system.orchestration.duckdb") as mock_duckdb,
            patch("lq.system.orchestration.build_structure_snapshot", side_effect=fake_build_structure),
            patch("lq.system.orchestration.build_malf_context_for_stock", return_value=None),
            patch("lq.system.orchestration.check_adverse_conditions") as mock_filter,
        ):
            mock_duckdb.connect.return_value = mock_conn
            mock_filter.return_value = MagicMock(tradeable=False)

            run_daily_signal_scan(
                signal_date=signal_date,
                codes=["000001.SZ"],
            )

        assert len(captured_df) == 1, "应捕获到一次 build_structure_snapshot 调用"
        df = captured_df[0]

        # 最后一根必须是 signal_date
        last_date = pd.to_datetime(df["date"].iloc[-1]).date() if not isinstance(df["date"].iloc[-1], date) else df["date"].iloc[-1]
        assert last_date == signal_date, (
            f"最后一根日线应为 signal_date={signal_date}，得到 {last_date}"
        )

    def test_window_not_exceeds_limit(self):
        """窗口不超过 120 根。"""
        signal_date = date(2024, 6, 28)
        captured_df: list[pd.DataFrame] = []

        # 模拟数据库已经限制返回 120 根（DESC 顺序）
        mock_df_desc = _make_daily_df(120, signal_date).sort_values("date", ascending=False).reset_index(drop=True)

        def fake_build_structure(code, sd, df):
            captured_df.append(df.copy())
            from lq.structure.contracts import StructureSnapshot
            return StructureSnapshot(
                code=code, signal_date=sd,
                pivot_highs=[], pivot_lows=[],
                support_levels=[], resistance_levels=[],
                nearest_support=None, nearest_resistance=None,
                latest_breakout=None,
            )

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.execute.return_value.df.side_effect = [
            mock_df_desc,
            pd.DataFrame(),
            pd.DataFrame(),
        ]

        with (
            patch("lq.system.orchestration.duckdb") as mock_duckdb,
            patch("lq.system.orchestration.build_structure_snapshot", side_effect=fake_build_structure),
            patch("lq.system.orchestration.build_malf_context_for_stock", return_value=None),
            patch("lq.system.orchestration.check_adverse_conditions") as mock_filter,
        ):
            mock_duckdb.connect.return_value = mock_conn
            mock_filter.return_value = MagicMock(tradeable=False)

            run_daily_signal_scan(signal_date=signal_date, codes=["000001.SZ"])

        assert len(captured_df[0]) <= 120
