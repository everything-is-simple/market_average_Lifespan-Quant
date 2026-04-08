from __future__ import annotations

"""验证后复权因子计算与价格应用合同。"""

from datetime import date

import pandas as pd

from lq.data.compute.adjust import apply_backward_adjustment, compute_backward_factors


_EVENT_COLUMNS = [
    "event_date",
    "category",
    "fenhong",
    "peigujia",
    "songzhuangu",
    "peigu",
]


def _empty_events() -> pd.DataFrame:
    return pd.DataFrame(columns=_EVENT_COLUMNS)


def _make_factor_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ],
            "close": [10.0, 10.5, 11.0, 11.5],
        }
    )


def _make_apply_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["000001.SZ", "000001.SZ", "000001.SZ", "000001.SZ"],
            "trade_date": [
                date(2024, 1, 2),
                date(2024, 1, 3),
                date(2024, 1, 4),
                date(2024, 1, 5),
            ],
            "open": [10.0, 10.2, 10.8, 11.2],
            "high": [10.3, 10.4, 11.1, 11.6],
            "low": [9.8, 10.0, 10.5, 11.0],
            "close": [10.0, 10.5, 11.0, 11.5],
            "volume": [1000, 1100, 1200, 1300],
            "amount": [10000, 11550, 13200, 14950],
            "is_suspended": [False, True, False, False],
        }
    )


def test_compute_backward_factors_returns_all_one_when_no_events() -> None:
    raw_bars = _make_factor_bars()

    result = compute_backward_factors(raw_bars, _empty_events())

    assert list(result.index) == [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
    assert result.tolist() == [1.0, 1.0, 1.0, 1.0]


def test_compute_backward_factors_handles_single_dividend_event() -> None:
    raw_bars = _make_factor_bars()
    events = pd.DataFrame(
        [
            {
                "event_date": date(2024, 1, 5),
                "category": 1,
                "fenhong": 1.0,
                "peigujia": 0.0,
                "songzhuangu": 0.0,
                "peigu": 0.0,
            }
        ]
    )

    result = compute_backward_factors(raw_bars, events)

    expected = round((11.0 - 0.1) / 11.0, 8)
    assert result[date(2024, 1, 2)] == expected
    assert result[date(2024, 1, 3)] == expected
    assert result[date(2024, 1, 4)] == expected
    assert result[date(2024, 1, 5)] == 1.0


def test_compute_backward_factors_handles_composite_event() -> None:
    raw_bars = _make_factor_bars()
    events = pd.DataFrame(
        [
            {
                "event_date": date(2024, 1, 5),
                "category": 1,
                "fenhong": 1.0,
                "peigujia": 8.0,
                "songzhuangu": 5.0,
                "peigu": 2.0,
            }
        ]
    )

    result = compute_backward_factors(raw_bars, events)

    numerator = 11.0 - 0.1 + 8.0 * 0.2
    denominator = (1.0 + 0.5 + 0.2) * 11.0
    expected = round(numerator / denominator, 8)

    assert result[date(2024, 1, 2)] == expected
    assert result[date(2024, 1, 3)] == expected
    assert result[date(2024, 1, 4)] == expected
    assert result[date(2024, 1, 5)] == 1.0


def test_compute_backward_factors_accumulates_multiple_events() -> None:
    raw_bars = _make_factor_bars()
    events = pd.DataFrame(
        [
            {
                "event_date": date(2024, 1, 4),
                "category": 1,
                "fenhong": 1.0,
                "peigujia": 0.0,
                "songzhuangu": 0.0,
                "peigu": 0.0,
            },
            {
                "event_date": date(2024, 1, 5),
                "category": 1,
                "fenhong": 0.5,
                "peigujia": 0.0,
                "songzhuangu": 0.0,
                "peigu": 0.0,
            },
        ]
    )

    result = compute_backward_factors(raw_bars, events)

    factor_2024_01_04 = (10.5 - 0.1) / 10.5
    factor_2024_01_05 = (11.0 - 0.05) / 11.0
    cumulative = round(factor_2024_01_04 * factor_2024_01_05, 8)
    latest_only = round(factor_2024_01_05, 8)

    assert result[date(2024, 1, 2)] == cumulative
    assert result[date(2024, 1, 3)] == cumulative
    assert result[date(2024, 1, 4)] == latest_only
    assert result[date(2024, 1, 5)] == 1.0


def test_apply_backward_adjustment_filters_suspended_and_adjusts_prices() -> None:
    raw_bars = _make_apply_bars()
    events = pd.DataFrame(
        [
            {
                "event_date": date(2024, 1, 5),
                "category": 1,
                "fenhong": 1.0,
                "peigujia": 0.0,
                "songzhuangu": 0.0,
                "peigu": 0.0,
            }
        ]
    )

    result = apply_backward_adjustment(raw_bars, events)

    expected_factor = round((11.0 - 0.1) / 11.0, 8)

    assert list(result["trade_date"]) == [date(2024, 1, 2), date(2024, 1, 4), date(2024, 1, 5)]
    assert list(result["adjust_method"]) == ["backward", "backward", "backward"]
    assert result.loc[result["trade_date"] == date(2024, 1, 2), "adjustment_factor"].iloc[0] == expected_factor
    assert result.loc[result["trade_date"] == date(2024, 1, 4), "adjustment_factor"].iloc[0] == expected_factor
    assert result.loc[result["trade_date"] == date(2024, 1, 5), "adjustment_factor"].iloc[0] == 1.0
    assert result.loc[result["trade_date"] == date(2024, 1, 2), "open"].iloc[0] == round(10.0 * expected_factor, 4)
    assert result.loc[result["trade_date"] == date(2024, 1, 4), "close"].iloc[0] == round(11.0 * expected_factor, 4)
    assert result.loc[result["trade_date"] == date(2024, 1, 5), "close"].iloc[0] == 11.5
