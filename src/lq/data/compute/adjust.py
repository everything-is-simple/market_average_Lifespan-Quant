"""data.compute.adjust — 后复权因子计算。

口径（继承父系统 137 号卡）：
  - 只处理 raw_xdxr_event.category = 1（主除权除息事件）
  - 后复权：以最新价为基准，历史价格向下调整
  - 复权因子公式：
      factor_i = (prev_close - fenhong/10 + peigujia × peigu/10)
                 / ((1 + (songzhuangu + peigu)/10) × prev_close)
    其中各字段单位：fenhong/songzhuangu/peigu 均为"每10股"，需除以10换算成"每股"。
  - 停牌日不写入 stock_daily_adjusted
"""

from __future__ import annotations

from datetime import date

import pandas as pd


def compute_backward_factors(
    raw_bars: pd.DataFrame,
    xdxr_events: pd.DataFrame,
) -> pd.Series:
    """为单只股票计算每个交易日的后复权因子。

    参数：
        raw_bars    — 原始日线 DataFrame，必须含 ['trade_date', 'close']，无需有序
        xdxr_events — 该股票的除权除息事件，必须含
                      ['event_date', 'category', 'fenhong', 'peigujia',
                       'songzhuangu', 'peigu']

    返回：
        pd.Series，index 为 date，values 为后复权因子（float），最新日 = 1.0。
        无数据时返回全 1.0 的 Series。
    """
    if raw_bars.empty:
        return pd.Series(dtype=float)

    # 只保留 category=1（主除权除息）
    cat1 = xdxr_events[xdxr_events["category"] == 1].copy() if not xdxr_events.empty else pd.DataFrame()

    # 构建 trade_date → close 的映射（用于查找 prev_close）
    bars_sorted = raw_bars.sort_values("trade_date").reset_index(drop=True)
    date_to_close: dict[date, float] = {
        row["trade_date"]: float(row["close"])
        for _, row in bars_sorted.iterrows()
        if row["close"] is not None and float(row["close"]) > 0
    }
    all_dates = sorted(date_to_close.keys())

    if cat1.empty:
        # 无除权事件 → 全部因子为 1.0
        return pd.Series({d: 1.0 for d in all_dates})

    # 计算每个 xdxr 事件的 factor_i（需要 event_date 前最近一个交易日的收盘价）
    event_factors: dict[date, float] = {}
    for _, evt in cat1.iterrows():
        ev_date = evt["event_date"]
        if isinstance(ev_date, str):
            ev_date = date.fromisoformat(ev_date)

        # 找 event_date 前最近一个有收盘价的交易日
        prev_dates = [d for d in all_dates if d < ev_date]
        if not prev_dates:
            continue
        prev_close = date_to_close[prev_dates[-1]]
        if prev_close <= 0:
            continue

        fenhong    = float(evt.get("fenhong")    or 0) / 10.0   # 元/股
        peigujia   = float(evt.get("peigujia")   or 0)          # 元/股（配股价已是每股）
        songzhuangu = float(evt.get("songzhuangu") or 0) / 10.0  # 每股送转股数
        peigu      = float(evt.get("peigu")      or 0) / 10.0   # 每股配股数

        numerator   = prev_close - fenhong + peigujia * peigu
        denominator = (1.0 + songzhuangu + peigu) * prev_close

        if denominator <= 0 or numerator <= 0:
            continue   # 异常事件跳过（不影响其他事件）

        f = numerator / denominator
        # 防止异常因子（过大或过小均跳过）
        if 0.01 < f < 10.0:
            event_factors[ev_date] = event_factors.get(ev_date, 1.0) * f

    if not event_factors:
        return pd.Series({d: 1.0 for d in all_dates})

    # 从最新日期往前累积乘：backward_factor(T) = ∏ factor_i for event_date > T
    # 按 event_date 降序排列
    events_desc = sorted(event_factors.items(), key=lambda x: x[0], reverse=True)
    ei = 0
    cum = 1.0
    result: dict[date, float] = {}

    for d in reversed(all_dates):
        # 应用所有 event_date > d 的事件因子（因为这些事件发生在 d 之后）
        while ei < len(events_desc) and events_desc[ei][0] > d:
            cum *= events_desc[ei][1]
            ei += 1
        result[d] = round(cum, 8)

    return pd.Series(result)


def apply_backward_adjustment(
    raw_bars: pd.DataFrame,
    xdxr_events: pd.DataFrame,
) -> pd.DataFrame:
    """将后复权因子应用到原始日线，返回可写入 stock_daily_adjusted 的 DataFrame。

    参数：
        raw_bars    — 原始日线，必须含 ['code', 'trade_date', 'open', 'high',
                      'low', 'close', 'volume', 'amount', 'is_suspended']
        xdxr_events — 该股票的除权除息事件（可以为空 DataFrame）

    返回：
        DataFrame，列与 stock_daily_adjusted schema 对应，停牌日已过滤。
    """
    if raw_bars.empty:
        return pd.DataFrame()

    # 过滤停牌日
    df = raw_bars[~raw_bars["is_suspended"].fillna(False).astype(bool)].copy()
    if df.empty:
        return pd.DataFrame()

    code = str(df["code"].iloc[0])
    factors = compute_backward_factors(df, xdxr_events)

    # 对齐 factor 到每行
    df = df.sort_values("trade_date").reset_index(drop=True)
    df["adjustment_factor"] = df["trade_date"].map(factors).fillna(1.0)

    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        df[col] = (df[col].astype(float) * df["adjustment_factor"]).round(4)

    df["adjust_method"] = "backward"

    # 选取输出列（与 bootstrap schema 对应）
    out = df[[
        "code", "trade_date", "adjust_method",
        "open", "high", "low", "close",
        "volume", "amount", "adjustment_factor",
    ]].copy()
    return out
