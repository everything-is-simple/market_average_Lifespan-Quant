"""data 模块 DuckDB 数据库 schema 初始化。"""

from __future__ import annotations

from pathlib import Path

import duckdb


# raw_market 数据库表定义
RAW_MARKET_SCHEMA_SQL = """
-- 原始日线行情（baostock 入库，未复权）
CREATE TABLE IF NOT EXISTS raw_daily_bar (
    code         VARCHAR NOT NULL,
    trade_date   DATE    NOT NULL,
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    volume       BIGINT,
    amount       DOUBLE,
    turn         DOUBLE,    -- 换手率
    pct_chg      DOUBLE,    -- 涨跌幅
    PRIMARY KEY (code, trade_date)
);

-- 股票基础信息
CREATE TABLE IF NOT EXISTS raw_stock_basic (
    code         VARCHAR PRIMARY KEY,
    code_name    VARCHAR,
    ipoDate      DATE,
    outDate      DATE,
    type         VARCHAR,   -- 1:股票 2:指数 3:其他
    status       VARCHAR,   -- 1:上市 2:退市 3:暂停上市
    updated_at   TIMESTAMP DEFAULT current_timestamp
);

-- 股票列表快照（每次全量刷新）
CREATE TABLE IF NOT EXISTS raw_stock_list_snapshot (
    snapshot_date DATE NOT NULL,
    code          VARCHAR NOT NULL,
    code_name     VARCHAR,
    PRIMARY KEY (snapshot_date, code)
);
""";

# market_base 数据库表定义
MARKET_BASE_SCHEMA_SQL = """
-- 后复权日线行情（基础分析层）
CREATE TABLE IF NOT EXISTS adj_daily_bar (
    code         VARCHAR NOT NULL,
    trade_date   DATE    NOT NULL,
    adj_open     DOUBLE,
    adj_high     DOUBLE,
    adj_low      DOUBLE,
    adj_close    DOUBLE,
    volume       BIGINT,
    amount       DOUBLE,
    volume_ma5   DOUBLE,
    volume_ma10  DOUBLE,
    volume_ma20  DOUBLE,
    ma5          DOUBLE,
    ma10         DOUBLE,
    ma20         DOUBLE,
    ma60         DOUBLE,
    atr14        DOUBLE,    -- 14日真实波幅均值
    PRIMARY KEY (code, trade_date)
);

-- 月线汇总行情（MALF 月线层输入）
CREATE TABLE IF NOT EXISTS monthly_bar (
    code         VARCHAR NOT NULL,
    month_start  DATE    NOT NULL,   -- 该月第一个交易日
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    volume       BIGINT,
    PRIMARY KEY (code, month_start)
);

-- 周线汇总行情（MALF 周线层输入）
CREATE TABLE IF NOT EXISTS weekly_bar (
    code         VARCHAR NOT NULL,
    week_start   DATE    NOT NULL,   -- 该周第一个交易日（周一）
    open         DOUBLE,
    high         DOUBLE,
    low          DOUBLE,
    close        DOUBLE,
    volume       BIGINT,
    PRIMARY KEY (code, week_start)
);
""";


def bootstrap_data_storage(
    raw_market_path: Path,
    market_base_path: Path,
) -> None:
    """初始化 raw_market 和 market_base 两个数据库的 schema。"""
    raw_market_path.parent.mkdir(parents=True, exist_ok=True)
    market_base_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(raw_market_path)) as conn:
        conn.execute(RAW_MARKET_SCHEMA_SQL)

    with duckdb.connect(str(market_base_path)) as conn:
        conn.execute(MARKET_BASE_SCHEMA_SQL)
