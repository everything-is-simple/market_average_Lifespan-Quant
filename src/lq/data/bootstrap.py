"""data 模块 DuckDB 数据库 schema 初始化。

数据架构说明：
  raw_market.duckdb（L1）— mootdx 日线 + gbbq 除权除息 + tushare 资产快照
  market_base.duckdb（L2）— 后复权日线 + 周/月线聚合 + 交易日历
"""

from __future__ import annotations

from pathlib import Path

import duckdb


# ---------------------------------------------------------------------------
# L1 raw_market 数据库：原始数据，来自 mootdx / gbbq / tushare
# ---------------------------------------------------------------------------
RAW_MARKET_SCHEMA_STATEMENTS = [
    # 股票原始日线（来源：mootdx 读取通达信本地 .day 文件，未复权）
    """
    CREATE TABLE IF NOT EXISTS raw_stock_daily (
        provider_name  VARCHAR NOT NULL,          -- 数据来源标识，如 "tdx_local_day"
        code           VARCHAR NOT NULL,          -- 标准化代码，如 "000001.SZ"
        trade_date     DATE    NOT NULL,
        open           DOUBLE,
        high           DOUBLE,
        low            DOUBLE,
        close          DOUBLE,
        volume         DOUBLE,                    -- 成交量（手）
        amount         DOUBLE,                    -- 成交额（元）
        is_suspended   BOOLEAN DEFAULT FALSE,
        ingest_run_id  VARCHAR NOT NULL,
        PRIMARY KEY (code, trade_date)
    )
    """,
    # 指数原始日线（来源：mootdx，sh/sz 指数）
    """
    CREATE TABLE IF NOT EXISTS raw_index_daily (
        provider_name  VARCHAR NOT NULL,
        index_code     VARCHAR NOT NULL,          -- 如 "000001.SH"
        trade_date     DATE    NOT NULL,
        open           DOUBLE,
        high           DOUBLE,
        low            DOUBLE,
        close          DOUBLE,
        volume         DOUBLE,
        amount         DOUBLE,
        ingest_run_id  VARCHAR NOT NULL,
        PRIMARY KEY (index_code, trade_date)
    )
    """,
    # 除权除息事件（来源：通达信本地 gbbq 加密文件，用于计算后复权因子）
    """
    CREATE TABLE IF NOT EXISTS raw_xdxr_event (
        provider_name  VARCHAR NOT NULL,          -- "tdx_local_gbbq"
        code           VARCHAR NOT NULL,
        event_date     DATE    NOT NULL,
        category       INTEGER NOT NULL,          -- 1=除权除息 2=送配股上市 等 14 种
        category_name  VARCHAR,
        fenhong        DOUBLE,                    -- 每股分红（元）
        peigujia       DOUBLE,                    -- 配股价（元）
        songzhuangu    DOUBLE,                    -- 每股送转股数
        peigu          DOUBLE,                    -- 每股配股数
        suogu          DOUBLE,                    -- 缩股比例
        panqianliutong DOUBLE,                    -- 盘前流通股
        panhouliutong  DOUBLE,                    -- 盘后流通股
        qianzongguben  DOUBLE,                    -- 前总股本
        houzongguben   DOUBLE,                    -- 后总股本
        fenshu         DOUBLE,                    -- 权证份数
        xingquanjia    DOUBLE,                    -- 行权价
        ingest_run_id  VARCHAR NOT NULL,
        PRIMARY KEY (code, event_date, category)
    )
    """,
    # 资产快照（来源：tushare stock_basic API，低频刷新）
    """
    CREATE TABLE IF NOT EXISTS raw_asset_snapshot (
        provider_name   VARCHAR NOT NULL,         -- "tushare"
        code            VARCHAR NOT NULL,
        snapshot_date   DATE    NOT NULL,
        asset_name      VARCHAR,                  -- 股票名称
        exchange        VARCHAR,                  -- SH / SZ / BJ
        asset_type      VARCHAR,                  -- stock / index
        status          VARCHAR,                  -- L=上市 D=退市 P=暂停
        listing_date    DATE,
        delisting_date  DATE,
        ingest_run_id   VARCHAR NOT NULL,
        PRIMARY KEY (code, snapshot_date)
    )
    """,
    # 入库 manifest 记录（每次 ingest 写一条）
    """
    CREATE TABLE IF NOT EXISTS raw_ingest_manifest (
        run_id         VARCHAR PRIMARY KEY,
        provider_name  VARCHAR NOT NULL,
        dataset_name   VARCHAR NOT NULL,
        window_start   DATE,
        window_end     DATE,
        status         VARCHAR NOT NULL,
        rows_written   BIGINT  NOT NULL DEFAULT 0,
        created_at     TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]

# ---------------------------------------------------------------------------
# L2 market_base 数据库：复权后数据，全部由 L1 本地计算得到
# ---------------------------------------------------------------------------
MARKET_BASE_SCHEMA_STATEMENTS = [
    # 后复权日线行情（由 raw_stock_daily + raw_xdxr_event 本地计算）
    """
    CREATE TABLE IF NOT EXISTS stock_daily_adjusted (
        code              VARCHAR NOT NULL,
        trade_date        DATE    NOT NULL,
        adjust_method     VARCHAR NOT NULL DEFAULT 'backward',  -- 后复权
        open              DOUBLE,
        high              DOUBLE,
        low               DOUBLE,
        close             DOUBLE,
        volume            DOUBLE,
        amount            DOUBLE,
        adjustment_factor DOUBLE,                               -- 复权因子
        build_run_id      VARCHAR NOT NULL,
        PRIMARY KEY (code, trade_date, adjust_method)
    )
    """,
    # 后复权周线（由 stock_daily_adjusted 聚合）
    """
    CREATE TABLE IF NOT EXISTS stock_weekly_adjusted (
        code            VARCHAR NOT NULL,
        trade_date      DATE    NOT NULL,   -- 该周最后一个交易日
        week_start_date DATE,               -- 该周第一个交易日
        adjust_method   VARCHAR NOT NULL DEFAULT 'backward',
        open            DOUBLE,
        high            DOUBLE,
        low             DOUBLE,
        close           DOUBLE,
        volume          DOUBLE,
        amount          DOUBLE,
        build_run_id    VARCHAR NOT NULL,
        PRIMARY KEY (code, trade_date, adjust_method)
    )
    """,
    # 后复权月线（由 stock_daily_adjusted 聚合）
    """
    CREATE TABLE IF NOT EXISTS stock_monthly_adjusted (
        code             VARCHAR NOT NULL,
        trade_date       DATE    NOT NULL,  -- 该月最后一个交易日
        month_start_date DATE,              -- 该月第一个交易日
        adjust_method    VARCHAR NOT NULL DEFAULT 'backward',
        open             DOUBLE,
        high             DOUBLE,
        low              DOUBLE,
        close            DOUBLE,
        volume           DOUBLE,
        amount           DOUBLE,
        build_run_id     VARCHAR NOT NULL,
        PRIMARY KEY (code, trade_date, adjust_method)
    )
    """,
    # 指数日线（直接从 raw_index_daily 清洗，无复权）
    """
    CREATE TABLE IF NOT EXISTS index_daily (
        index_code   VARCHAR NOT NULL,
        trade_date   DATE    NOT NULL,
        open         DOUBLE,
        high         DOUBLE,
        low          DOUBLE,
        close        DOUBLE,
        volume       DOUBLE,
        amount       DOUBLE,
        build_run_id VARCHAR NOT NULL,
        PRIMARY KEY (index_code, trade_date)
    )
    """,
    # 指数周线（由 index_daily 聚合）
    """
    CREATE TABLE IF NOT EXISTS index_weekly (
        index_code      VARCHAR NOT NULL,
        trade_date      DATE    NOT NULL,
        week_start_date DATE,
        open            DOUBLE,
        high            DOUBLE,
        low             DOUBLE,
        close           DOUBLE,
        volume          DOUBLE,
        amount          DOUBLE,
        build_run_id    VARCHAR NOT NULL,
        PRIMARY KEY (index_code, trade_date)
    )
    """,
    # 指数月线（由 index_daily 聚合）
    """
    CREATE TABLE IF NOT EXISTS index_monthly (
        index_code       VARCHAR NOT NULL,
        trade_date       DATE    NOT NULL,
        month_start_date DATE,
        open             DOUBLE,
        high             DOUBLE,
        low              DOUBLE,
        close            DOUBLE,
        volume           DOUBLE,
        amount           DOUBLE,
        build_run_id     VARCHAR NOT NULL,
        PRIMARY KEY (index_code, trade_date)
    )
    """,
    # 交易日历（从 raw_stock_daily + raw_index_daily 中的 trade_date 去重得到）
    """
    CREATE TABLE IF NOT EXISTS trade_calendar (
        market_code  VARCHAR NOT NULL DEFAULT 'CN-A',
        trade_date   DATE    NOT NULL,
        is_open      BOOLEAN NOT NULL DEFAULT TRUE,
        build_run_id VARCHAR NOT NULL,
        PRIMARY KEY (market_code, trade_date)
    )
    """,
    # 标准化资产主表（来自 raw_asset_snapshot 去重/标准化，全系统统一资产基础表）
    """
    CREATE TABLE IF NOT EXISTS asset_master (
        code           VARCHAR NOT NULL,          -- 标准化代码，如 "000001.SZ"
        asset_name     VARCHAR,                   -- 股票名称
        exchange       VARCHAR,                   -- SH / SZ / BJ
        asset_type     VARCHAR,                   -- stock / index
        status         VARCHAR,                   -- L=上市 D=退市 P=暂停
        listing_date   DATE,
        delisting_date DATE,
        refreshed_at   DATE NOT NULL,             -- 本次刷新日期
        build_run_id   VARCHAR NOT NULL,
        PRIMARY KEY (code)
    )
    """,
    # 板块/行业分类主表（来自 TDX tdxhy.cfg / tdxzs.cfg）
    """
    CREATE TABLE IF NOT EXISTS block_master (
        block_code   VARCHAR NOT NULL,            -- 板块/行业代码
        block_name   VARCHAR,                     -- 板块/行业名称
        block_type   VARCHAR,                     -- industry / concept / area 等
        build_run_id VARCHAR NOT NULL,
        PRIMARY KEY (block_code)
    )
    """,
    # 股票-板块从属关系快照（来自 TDX block 文件，记录每次刷新时的成员关系）
    """
    CREATE TABLE IF NOT EXISTS block_membership_snapshot (
        block_code    VARCHAR NOT NULL,
        code          VARCHAR NOT NULL,           -- 股票代码
        snapshot_date DATE    NOT NULL,
        build_run_id  VARCHAR NOT NULL,
        PRIMARY KEY (block_code, code, snapshot_date)
    )
    """,
    # L2 构建 manifest 记录
    """
    CREATE TABLE IF NOT EXISTS base_build_manifest (
        run_id       VARCHAR PRIMARY KEY,
        source_name  VARCHAR NOT NULL,
        dataset_name VARCHAR NOT NULL,
        window_start DATE,
        window_end   DATE,
        status       VARCHAR NOT NULL,
        rows_written BIGINT  NOT NULL DEFAULT 0,
        created_at   TIMESTAMP NOT NULL DEFAULT current_timestamp
    )
    """,
]


def bootstrap_data_storage(
    raw_market_path: Path,
    market_base_path: Path,
) -> None:
    """初始化 raw_market（L1）和 market_base（L2）两个数据库的 schema。

    使用 CREATE TABLE IF NOT EXISTS，安全地在已有库上重复调用。
    """
    raw_market_path.parent.mkdir(parents=True, exist_ok=True)
    market_base_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(raw_market_path)) as conn:
        for stmt in RAW_MARKET_SCHEMA_STATEMENTS:
            conn.execute(stmt)

    with duckdb.connect(str(market_base_path)) as conn:
        for stmt in MARKET_BASE_SCHEMA_STATEMENTS:
            conn.execute(stmt)
