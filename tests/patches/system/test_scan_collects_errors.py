"""P0-02 补丁测试：扫描异常必须被记录，不能静默吞掉。

回归防护：
    单只股票在 MALF / DB 阶段抛出异常时，
    summary.scan_errors 里能看到失败记录（code/stage/error），
    不会无声消失，也不影响其他股票的扫描。
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from lq.system.orchestration import run_daily_signal_scan


class TestScanCollectsErrors:
    def test_single_stock_error_is_recorded(self):
        """单只股票抛异常时，summary.scan_errors 包含该股票的记录。"""
        signal_date = date(2024, 6, 28)

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        # 第一次 execute().df() 直接抛出异常
        mock_conn.execute.side_effect = RuntimeError("模拟数据库连接失败")

        with patch("lq.system.orchestration.duckdb") as mock_duckdb:
            mock_duckdb.connect.return_value = mock_conn
            summary = run_daily_signal_scan(
                signal_date=signal_date,
                codes=["000001.SZ"],
            )

        assert len(summary.scan_errors) == 1
        err = summary.scan_errors[0]
        assert err["code"] == "000001.SZ"
        assert err["stage"] == "scan"
        assert "模拟数据库连接失败" in err["error"]

    def test_error_in_one_stock_does_not_block_others(self):
        """一只股票失败不影响其他股票继续扫描。"""
        signal_date = date(2024, 6, 28)

        call_count = {"n": 0}

        def side_effect_connect(*args, **kwargs):
            call_count["n"] += 1
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: s
            mock_conn.__exit__ = MagicMock(return_value=False)
            if call_count["n"] == 1:
                # 第一只股票的连接抛异常
                mock_conn.execute.side_effect = RuntimeError("第一只股票失败")
            else:
                # 第二只股票返回空 DataFrame
                mock_conn.execute.return_value.df.return_value = pd.DataFrame()
            return mock_conn

        with (
            patch("lq.system.orchestration.duckdb") as mock_duckdb,
        ):
            mock_duckdb.connect.side_effect = side_effect_connect
            summary = run_daily_signal_scan(
                signal_date=signal_date,
                codes=["000001.SZ", "000002.SZ"],
            )

        # 扫描了两只股票
        assert summary.codes_scanned == 2
        # 第一只有错误
        assert len(summary.scan_errors) == 1
        assert summary.scan_errors[0]["code"] == "000001.SZ"

    def test_no_errors_means_empty_scan_errors(self):
        """无异常时 scan_errors 为空列表。"""
        signal_date = date(2024, 6, 28)

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        # 返回空 DataFrame（跳过 continue 分支）
        mock_conn.execute.return_value.df.return_value = pd.DataFrame()

        with patch("lq.system.orchestration.duckdb") as mock_duckdb:
            mock_duckdb.connect.return_value = mock_conn
            summary = run_daily_signal_scan(
                signal_date=signal_date,
                codes=["000001.SZ"],
            )

        assert summary.scan_errors == []
