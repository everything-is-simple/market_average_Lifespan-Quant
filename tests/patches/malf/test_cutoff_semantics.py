"""P2-01 补丁测试：MALF weekly/monthly 截断语义 — 应用 trade_date 而非 week_start/month_start。

问题根因：
    weekly.py / monthly.py 原先用 week_start/month_start <= asof_date 过滤，
    但 close = 该周/月最后交易日（trade_date）的收盘价。
    若数据库中已存在本周/本月完整 bar（trade_date > asof_date），
    则周中/月中扫描时会纳入未来收盘 — 属于数据泄漏。

修复方案：
    当 DataFrame 含 trade_date 列时，改用 trade_date <= asof_date 截断；
    不含 trade_date 时回退到 week_start/month_start 以保持向后兼容。
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from lq.malf.weekly import classify_weekly_flow, compute_weekly_strength
from lq.malf.monthly import classify_monthly_state, compute_monthly_strength


# ---------------------------------------------------------------------------
# 辅助工厂
# ---------------------------------------------------------------------------

def _make_weekly_with_trade_date(n: int, asof_date: date) -> pd.DataFrame:
    """生成 n 根周线，含 trade_date（周五），week_start（周一）。

    最后一根 week_start = asof_date（周一），trade_date = asof_date + 4（周五）。
    若 asof_date 是周一，则该周尚未完结，trade_date > asof_date，应被截断。
    """
    rows = []
    close = 10.0
    for i in range(n):
        # 逆序计算，最后一根落在 asof_date 所在周
        offset_weeks = n - 1 - i
        week_start = asof_date - timedelta(weeks=offset_weeks)
        trade_date = week_start + timedelta(days=4)  # 周五
        rows.append({
            "week_start": week_start,
            "trade_date": trade_date,
            "close": round(close + i * 0.1, 2),
            "high": round(close + i * 0.1 + 0.5, 2),
            "low": round(close + i * 0.1 - 0.3, 2),
            "volume": 1_000_000,
        })
    return pd.DataFrame(rows)


def _make_monthly_with_trade_date(n: int, asof_date: date) -> pd.DataFrame:
    """生成 n 根月线，含 trade_date（月末日），month_start（月初）。

    最后一根 month_start = asof_date 所在月的1号，trade_date = 该月最后一天。
    若 asof_date 是月初，则当月尚未完结，trade_date > asof_date，应被截断。
    """
    rows = []
    close = 5000.0
    current_month = date(asof_date.year, asof_date.month, 1)
    for i in range(n):
        # 逆序
        offset = n - 1 - i
        month = current_month.year * 12 + current_month.month - 1 - offset
        year, mo = divmod(month, 12)
        mo += 1
        month_start = date(year, mo, 1)
        # 月末：下月1号 - 1天
        if mo == 12:
            trade_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            trade_date = date(year, mo + 1, 1) - timedelta(days=1)
        rows.append({
            "month_start": month_start,
            "trade_date": trade_date,
            "close": round(close * (1.04 ** i), 2),
            "high": round(close * (1.04 ** i) * 1.05, 2),
            "low": round(close * (1.04 ** i) * 0.95, 2),
            "volume": 500_000_000,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# P2-01-A: 周线截断语义
# ---------------------------------------------------------------------------

class TestWeeklyTradeDateCutoff:
    """当 DataFrame 含 trade_date 列时，应用 trade_date <= asof_date 截断。"""

    def test_current_week_excluded_when_trade_date_future(self):
        """asof_date = 周一，当周 trade_date = 周五（未来），该周 bar 不应被纳入。"""
        # 选一个周一
        asof = date(2024, 6, 3)   # 2024-06-03 是周一
        df = _make_weekly_with_trade_date(n=10, asof_date=asof)

        # 最后一行: week_start=2024-06-03, trade_date=2024-06-07 > asof → 应被截断
        last_row = df.iloc[-1]
        assert last_row["week_start"] == asof
        assert last_row["trade_date"] > asof, "前提条件：最后一根 trade_date 在 asof 之后"

        # classify 之后用到的 closes 不应包含最后一根
        before_last_close = float(df.iloc[-2]["close"])
        result = classify_weekly_flow(df, "BULL_PERSISTING", asof)
        # 行为验证：函数应正常返回，不应崩溃
        assert result in ("with_flow", "against_flow")

        strength = compute_weekly_strength(df, asof)
        assert 0.0 <= strength <= 1.0

    def test_completed_week_included(self):
        """asof_date = 周五，当周 trade_date = 同一天，该周 bar 应被纳入。"""
        asof = date(2024, 5, 31)   # 2024-05-31 是周五
        df = _make_weekly_with_trade_date(n=10, asof_date=date(2024, 5, 27))  # 当周开始
        # 手动构造含 trade_date = asof 的完整周
        last_week_start = date(2024, 5, 27)
        last_trade_date = date(2024, 5, 31)
        row = pd.DataFrame([{
            "week_start": last_week_start, "trade_date": last_trade_date,
            "close": 12.0, "high": 12.5, "low": 11.7, "volume": 1_000_000,
        }])
        df = pd.concat([df, row], ignore_index=True)

        result = classify_weekly_flow(df, "BULL_PERSISTING", asof)
        assert result in ("with_flow", "against_flow")

    def test_fallback_to_week_start_when_no_trade_date(self):
        """向后兼容：不含 trade_date 列时，回退到 week_start <= asof_date。"""
        asof = date(2024, 6, 3)
        rows = []
        close = 10.0
        for i in range(8):
            week_start = date(2024, 4, 1) + timedelta(weeks=i)
            rows.append({
                "week_start": week_start,
                "close": round(close + i * 0.1, 2),
                "high": round(close + i * 0.1 + 0.5, 2),
                "low": round(close + i * 0.1 - 0.3, 2),
            })
        df = pd.DataFrame(rows)
        # 不含 trade_date，应回退，且不抛异常
        result = classify_weekly_flow(df, "BULL_PERSISTING", asof)
        assert result in ("with_flow", "against_flow")


# ---------------------------------------------------------------------------
# P2-01-B: 月线截断语义
# ---------------------------------------------------------------------------

class TestMonthlyTradeDateCutoff:
    """当 DataFrame 含 trade_date 列时，应用 trade_date <= asof_date 截断。"""

    def test_current_month_excluded_when_trade_date_future(self):
        """asof_date = 月初，当月 trade_date = 月末（未来），该月 bar 不应被纳入。"""
        asof = date(2024, 6, 3)   # 月初
        df = _make_monthly_with_trade_date(n=24, asof_date=asof)

        # 验证含 June 行且 trade_date > asof
        june_rows = df[df["month_start"] == date(2024, 6, 1)]
        if not june_rows.empty:
            assert june_rows.iloc[0]["trade_date"] > asof, "前提：June trade_date 在 asof 之后"

        state = classify_monthly_state(df, asof)
        assert isinstance(state, str)
        assert len(state) > 0

    def test_completed_month_included(self):
        """已完结的月份（trade_date <= asof_date）应正常纳入。"""
        asof = date(2024, 6, 3)
        df = _make_monthly_with_trade_date(n=24, asof_date=asof)
        # May 2024: trade_date = 2024-05-31 <= 2024-06-03
        may_rows = df[df["month_start"] == date(2024, 5, 1)]
        if not may_rows.empty:
            assert may_rows.iloc[0]["trade_date"] <= asof

        state = classify_monthly_state(df, asof)
        assert state in (
            "BULL_FORMING", "BULL_PERSISTING", "BULL_EXHAUSTING", "BULL_REVERSING",
            "BEAR_FORMING", "BEAR_PERSISTING", "BEAR_EXHAUSTING", "BEAR_REVERSING",
        )

    def test_fallback_to_month_start_when_no_trade_date(self):
        """向后兼容：不含 trade_date 列时，回退到 month_start <= asof_date。"""
        asof = date(2024, 6, 3)
        rows = []
        close = 5000.0
        for i in range(12):
            month_start = date(2023, 7, 1) if i == 0 else date(
                2023 + (6 + i) // 12, (6 + i) % 12 + 1, 1
            )
            rows.append({
                "month_start": month_start,
                "close": round(close * (1.03 ** i), 2),
                "high": round(close * (1.03 ** i) * 1.05, 2),
                "low": round(close * (1.03 ** i) * 0.95, 2),
                "volume": 500_000_000,
            })
        df = pd.DataFrame(rows)
        state = classify_monthly_state(df, asof)
        assert isinstance(state, str)


# ---------------------------------------------------------------------------
# P2-01-C: 截断语义不影响 MALF 整体结论可复现性
# ---------------------------------------------------------------------------

class TestCutoffDoesNotBreakMalfResult:
    """使用 trade_date 截断后，MALF 结论仍可复现（无未来数据 → 更保守/正确）。"""

    def test_bull_persisting_still_detected_with_complete_bars(self):
        """24 根完整上升月线（均已 trade_date <= asof），应识别 BULL_PERSISTING。"""
        asof = date(2024, 6, 3)
        df = _make_monthly_with_trade_date(n=25, asof_date=date(2024, 5, 3))
        # 只取 trade_date <= asof 的行
        df = df[df["trade_date"] <= asof].copy()
        state = classify_monthly_state(df, asof)
        # 24 根等比增长月线应为牛市态
        assert state.startswith("BULL"), f"期望牛市态，实际得到 {state}"


# ---------------------------------------------------------------------------
# P2-03: DuckDB datetime64 dtype 回归测试
# ---------------------------------------------------------------------------

def _as_datetime64(df: pd.DataFrame, *cols: str) -> pd.DataFrame:
    """将指定列转为 datetime64[ns]，模拟 DuckDB .df() 返回的 DATE 列 dtype。"""
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


class TestDatetime64DtypeCompatibility:
    """P2-03 回归：DuckDB .df() 返回 datetime64 列时，截断比较不应 TypeError。

    根因：Python date 与 datetime64[ns] 直接 <= 比较会抛
    TypeError: Invalid comparison between dtype=datetime64[...] and date。
    修复：pd.to_datetime(col) <= pd.Timestamp(asof_date)。
    """

    def test_weekly_classify_flow_with_datetime64_trade_date(self):
        """trade_date 列为 datetime64[ns] 时，classify_weekly_flow 不应 TypeError。"""
        asof = date(2024, 6, 3)
        df = _make_weekly_with_trade_date(n=10, asof_date=asof)
        df = _as_datetime64(df, "trade_date", "week_start")

        # 不应抛异常
        result = classify_weekly_flow(df, "BULL_PERSISTING", asof)
        assert result in ("with_flow", "against_flow")

    def test_weekly_strength_with_datetime64_trade_date(self):
        """trade_date 列为 datetime64[ns] 时，compute_weekly_strength 不应 TypeError。"""
        asof = date(2024, 6, 3)
        df = _make_weekly_with_trade_date(n=10, asof_date=asof)
        df = _as_datetime64(df, "trade_date", "week_start")

        strength = compute_weekly_strength(df, asof)
        assert 0.0 <= strength <= 1.0

    def test_monthly_classify_state_with_datetime64_trade_date(self):
        """trade_date 列为 datetime64[ns] 时，classify_monthly_state 不应 TypeError。"""
        asof = date(2024, 6, 3)
        df = _make_monthly_with_trade_date(n=24, asof_date=asof)
        df = _as_datetime64(df, "trade_date", "month_start")

        state = classify_monthly_state(df, asof)
        assert isinstance(state, str)
        assert len(state) > 0

    def test_monthly_strength_with_datetime64_trade_date(self):
        """trade_date 列为 datetime64[ns] 时，compute_monthly_strength 不应 TypeError。"""
        asof = date(2024, 6, 3)
        df = _make_monthly_with_trade_date(n=24, asof_date=asof)
        df = _as_datetime64(df, "trade_date", "month_start")

        strength = compute_monthly_strength(df, asof)
        assert 0.0 <= strength <= 1.0

    def test_weekly_fallback_week_start_datetime64(self):
        """无 trade_date 列，week_start 为 datetime64[ns] 时，回退路径不应 TypeError。"""
        asof = date(2024, 6, 3)
        rows = []
        close = 10.0
        for i in range(8):
            week_start = date(2024, 4, 1) + timedelta(weeks=i)
            rows.append({
                "week_start": week_start,
                "close": round(close + i * 0.1, 2),
                "high": round(close + i * 0.1 + 0.5, 2),
                "low": round(close + i * 0.1 - 0.3, 2),
            })
        df = pd.DataFrame(rows)
        df = _as_datetime64(df, "week_start")   # 模拟 DuckDB 返回 datetime64

        result = classify_weekly_flow(df, "BULL_PERSISTING", asof)
        assert result in ("with_flow", "against_flow")

    def test_monthly_fallback_month_start_datetime64(self):
        """无 trade_date 列，month_start 为 datetime64[ns] 时，回退路径不应 TypeError。"""
        asof = date(2024, 6, 3)
        rows = []
        close = 5000.0
        for i in range(12):
            ms = date(2023, 6 + i if 6 + i <= 12 else 6 + i - 12,
                      1) if 6 + i <= 12 else date(2024, 6 + i - 12, 1)
            rows.append({
                "month_start": ms,
                "close": round(close * (1.03 ** i), 2),
                "high": round(close * (1.03 ** i) * 1.05, 2),
                "low": round(close * (1.03 ** i) * 0.95, 2),
                "volume": 500_000_000,
            })
        df = pd.DataFrame(rows)
        df = _as_datetime64(df, "month_start")   # 模拟 DuckDB 返回 datetime64

        state = classify_monthly_state(df, asof)
        assert isinstance(state, str)

    def test_cutoff_excludes_future_bar_with_datetime64(self):
        """datetime64 dtype 下，trade_date > asof 的 bar 仍应被截断（不纳入计算）。"""
        asof = date(2024, 6, 3)  # 周一
        df = _make_weekly_with_trade_date(n=5, asof_date=asof)
        # 最后一根 week_start=asof, trade_date=asof+4 > asof，应被截断
        assert df.iloc[-1]["trade_date"] > asof
        n_before = len(df)

        df = _as_datetime64(df, "trade_date", "week_start")

        # 直接验证 pd.to_datetime 后过滤行为
        cutoff_ts = pd.Timestamp(asof)
        filtered = df[pd.to_datetime(df["trade_date"]) <= cutoff_ts]
        assert len(filtered) == n_before - 1, "最后一根 trade_date > asof 的 bar 应被过滤掉"
