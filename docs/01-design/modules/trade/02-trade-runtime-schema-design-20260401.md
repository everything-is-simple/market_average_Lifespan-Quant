# trade 模块 — trade_runtime Schema 设计 / 2026-04-01

## 1. 设计目标

本文定义 `trade_runtime.duckdb`（L4 层）的最小可运行 schema，包括：

1. 表职责与分层逻辑
2. 完整 DDL（CREATE TABLE）
3. 写权边界与读权声明
4. 与父系统的对比取舍说明

---

## 2. 设计原则

### 2.1 最小可运行原则

父系统（MarketLifespan-Quant）`bootstrap_schema.py` 定义了 20+ 张表，覆盖了滚动回测、benchmark、企业行动、broker 实盘 session 等复杂场景。

本系统当前阶段选取**最小可运行子集（8张表）**，以下条件满足后才扩展：
- 需要滚动窗口回测 → 增加 `rebalance_period / rebalance_signal`
- 需要实盘 broker session → 增加 `broker_session_state / broker_order_instruction`
- 需要企业行动精确还原 → 增加 `corporate_action_adjustment_event`

### 2.2 写权独占原则

`trade_runtime.duckdb` 是 `trade` 模块独占写入的数据库：
- `trade` 写入：所有 8 张表
- `system` 只读：用于生成报告
- `report` 只读：用于可视化输出
- `position / alpha / malf` 禁止写入

### 2.3 可追溯原则

每张表的每行数据必须可追溯到：
- `run_id`（哪次运行）
- `code + signal_date`（哪笔信号）
- `trade_id`（哪笔交易）

---

## 3. 表目录（8 张核心表）

| 表名 | 类别 | 职责 |
|---|---|---|
| `trade_run` | 运行元数据 | 每次回测的元信息 |
| `trade_record` | 交易结果 | 每笔完整交易生命周期（结果合同落盘版） |
| `order_event` | 订单生命周期 | 每笔订单状态变更流水 |
| `fill_record` | 成交明细 | 每笔实际成交（含成本分解） |
| `position_daily_snapshot` | 持仓快照 | 每日持仓状态快照 |
| `daily_equity_curve` | 权益曲线 | 每日账户总权益 |
| `backtest_summary` | 回测汇总 | 单次回测的统计汇总 |
| `drawdown_analysis` | 回撤分析 | 最大回撤详细信息 |

---

## 4. 完整 DDL

### 4.1 trade_run — 运行元数据

```sql
CREATE TABLE IF NOT EXISTS trade_run (
    run_id          VARCHAR PRIMARY KEY,
    strategy_name   VARCHAR NOT NULL,
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    asof_date       DATE,
    pas_run_id      VARCHAR,              -- 关联的 PAS 信号 run
    position_run_id VARCHAR,              -- 关联的 position run
    initial_cash    DOUBLE NOT NULL,
    signal_count    INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR NOT NULL,     -- RUNNING | COMPLETED | FAILED
    notes           VARCHAR,
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
)
```

### 4.2 trade_record — 交易结果（TradeRecord 落盘版）

```sql
CREATE TABLE IF NOT EXISTS trade_record (
    trade_id            VARCHAR PRIMARY KEY,
    run_id              VARCHAR NOT NULL,
    code                VARCHAR NOT NULL,
    signal_id           VARCHAR NOT NULL,
    signal_date         DATE NOT NULL,
    signal_pattern      VARCHAR NOT NULL,
    surface_label       VARCHAR,
    entry_date          DATE NOT NULL,
    entry_price         DOUBLE NOT NULL,
    exit_date           DATE,
    exit_price          DOUBLE,
    initial_stop_price  DOUBLE NOT NULL,
    first_target_price  DOUBLE NOT NULL,
    risk_unit           DOUBLE NOT NULL,
    lot_count           INTEGER NOT NULL,
    entry_notional      DOUBLE NOT NULL,
    exit_notional       DOUBLE,
    entry_cost          DOUBLE,           -- 买入总成本（含佣金、过户费、滑点）
    exit_cost           DOUBLE,           -- 卖出总成本（含印花税）
    gross_pnl           DOUBLE,           -- 不含成本的盈亏
    net_pnl             DOUBLE,           -- 含全部成本的净盈亏
    pnl_pct             DOUBLE,           -- 净盈亏百分比
    r_multiple          DOUBLE,           -- 净盈亏 / risk_unit / lot_count / 100
    hold_days           INTEGER,          -- 实际持仓交易日数
    first_target_hit    BOOLEAN DEFAULT FALSE,
    exit_reason         VARCHAR,          -- INITIAL_STOP | TRAILING_STOP | TIME_STOP | FORCE_CLOSE
    lifecycle_state     VARCHAR NOT NULL, -- 最终状态
    pb_sequence_number  INTEGER,
    created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp,
    FOREIGN KEY (run_id) REFERENCES trade_run(run_id)
)
```

### 4.3 order_event — 订单生命周期流水

```sql
CREATE TABLE IF NOT EXISTS order_event (
    event_id        VARCHAR PRIMARY KEY,  -- uuid
    run_id          VARCHAR NOT NULL,
    order_id        VARCHAR NOT NULL,
    signal_id       VARCHAR,
    code            VARCHAR NOT NULL,
    action          VARCHAR NOT NULL,     -- BUY | SELL
    event_date      DATE NOT NULL,
    from_status     VARCHAR,              -- PENDING | FILLED | REJECTED | EXPIRED
    to_status       VARCHAR NOT NULL,
    origin          VARCHAR NOT NULL,     -- UPSTREAM_SIGNAL | EXIT_STOP_LOSS | EXIT_TRAILING_STOP | FORCE_CLOSE
    exit_reason_code VARCHAR,
    is_partial_exit BOOLEAN DEFAULT FALSE,
    quantity        INTEGER,
    price           DOUBLE,
    event_note      VARCHAR,
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp
)
```

### 4.4 fill_record — 成交明细

```sql
CREATE TABLE IF NOT EXISTS fill_record (
    fill_id             VARCHAR PRIMARY KEY,  -- order_id + _F
    run_id              VARCHAR NOT NULL,
    order_id            VARCHAR NOT NULL,
    trade_id            VARCHAR,              -- 关联 trade_record
    code                VARCHAR NOT NULL,
    fill_date           DATE NOT NULL,
    action              VARCHAR NOT NULL,     -- BUY | SELL
    fill_price          DOUBLE NOT NULL,      -- 含滑点的实际成交价
    fill_shares         INTEGER NOT NULL,
    fill_notional       DOUBLE NOT NULL,
    commission          DOUBLE NOT NULL,
    stamp_duty          DOUBLE NOT NULL DEFAULT 0,
    transfer_fee        DOUBLE NOT NULL DEFAULT 0,
    slippage_cost       DOUBLE NOT NULL DEFAULT 0,
    total_cost          DOUBLE NOT NULL,
    exit_reason_code    VARCHAR,
    is_partial_exit     BOOLEAN DEFAULT FALSE,
    remaining_qty_after INTEGER,
    created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp
)
```

### 4.5 position_daily_snapshot — 每日持仓快照

```sql
CREATE TABLE IF NOT EXISTS position_daily_snapshot (
    run_id              VARCHAR NOT NULL,
    trade_date          DATE NOT NULL,
    code                VARCHAR NOT NULL,
    position_id         VARCHAR NOT NULL,    -- = buy order_id
    trade_id            VARCHAR NOT NULL,
    entry_date          DATE NOT NULL,
    entry_price         DOUBLE NOT NULL,
    remaining_shares    INTEGER NOT NULL,
    current_price       DOUBLE NOT NULL,     -- 当日收盘价
    max_price_seen      DOUBLE NOT NULL,
    current_stop_price  DOUBLE NOT NULL,
    market_value        DOUBLE NOT NULL,
    unrealized_pnl      DOUBLE,
    hold_days           INTEGER NOT NULL,
    lifecycle_state     VARCHAR NOT NULL,
    first_target_hit    BOOLEAN DEFAULT FALSE,
    breakeven_triggered BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (run_id, trade_date, code)
)
```

### 4.6 daily_equity_curve — 权益曲线

```sql
CREATE TABLE IF NOT EXISTS daily_equity_curve (
    run_id          VARCHAR NOT NULL,
    trade_date      DATE NOT NULL,
    cash_balance    DOUBLE NOT NULL,
    market_value    DOUBLE NOT NULL,     -- 所有持仓按收盘价估值
    total_equity    DOUBLE NOT NULL,     -- cash + market_value
    position_count  INTEGER NOT NULL,   -- 当日持仓只数
    realized_pnl    DOUBLE,             -- 当日已实现盈亏
    exposure_ratio  DOUBLE,             -- market_value / total_equity
    drawdown_pct    DOUBLE,             -- 相对历史最高权益的回撤
    created_at      TIMESTAMP NOT NULL DEFAULT current_timestamp,
    PRIMARY KEY (run_id, trade_date)
)
```

### 4.7 backtest_summary — 回测汇总

```sql
CREATE TABLE IF NOT EXISTS backtest_summary (
    run_id              VARCHAR PRIMARY KEY,
    initial_cash        DOUBLE NOT NULL,
    ending_cash         DOUBLE NOT NULL,
    ending_equity       DOUBLE NOT NULL,
    total_invested      DOUBLE,          -- 累计投入资金
    total_cost          DOUBLE NOT NULL, -- 全部交易成本
    total_commission    DOUBLE,
    total_stamp_duty    DOUBLE,
    total_transfer_fee  DOUBLE,
    total_slippage      DOUBLE,
    gross_return_pct    DOUBLE,          -- 不含成本收益率
    net_return_pct      DOUBLE,          -- 含成本净收益率
    max_drawdown_pct    DOUBLE,
    trade_count         INTEGER NOT NULL,
    win_count           INTEGER NOT NULL,
    loss_count          INTEGER NOT NULL,
    win_rate            DOUBLE,          -- win_count / trade_count
    avg_r_multiple      DOUBLE,          -- 平均 R 倍数
    avg_hold_days       DOUBLE,
    profit_factor       DOUBLE,          -- gross_win / abs(gross_loss)
    expected_value      DOUBLE,          -- win_rate * avg_win - (1-win_rate) * avg_loss
    first_target_hit_rate DOUBLE,        -- 触达第一目标的比例
    created_at          TIMESTAMP NOT NULL DEFAULT current_timestamp,
    FOREIGN KEY (run_id) REFERENCES trade_run(run_id)
)
```

### 4.8 drawdown_analysis — 回撤分析

```sql
CREATE TABLE IF NOT EXISTS drawdown_analysis (
    run_id                  VARCHAR PRIMARY KEY,
    peak_date               DATE,
    peak_equity             DOUBLE,
    trough_date             DATE,
    trough_equity           DOUBLE,
    max_drawdown_pct        DOUBLE,
    max_drawdown_duration_days INTEGER,    -- 从峰值到谷值的交易日数
    recovery_date           DATE,           -- 恢复到峰值的日期（NULL=未恢复）
    recovery_duration_days  INTEGER,        -- 从谷值到恢复的交易日数（NULL=未恢复）
    created_at              TIMESTAMP NOT NULL DEFAULT current_timestamp,
    FOREIGN KEY (run_id) REFERENCES trade_run(run_id)
)
```

---

## 5. 写权与读权边界

| 角色 | trade_run | trade_record | order_event | fill_record | position_daily_snapshot | daily_equity_curve | backtest_summary | drawdown_analysis |
|---|---|---|---|---|---|---|---|---|
| `trade` | W | W | W | W | W | W | W | W |
| `system` | R | R | R | R | R | R | R | R |
| `report` | R | R | — | — | R | R | R | R |
| `position` | — | — | — | — | — | — | — | — |
| `alpha` | — | — | — | — | — | — | — | — |

W = 写入，R = 只读，— = 禁止访问

---

## 6. 关键外键与 JOIN 路径

```
trade_run (run_id)
    └─ trade_record (run_id, trade_id, signal_id)
           └─ fill_record (order_id → trade_record.trade_id)
           └─ order_event (order_id, signal_id)
           └─ position_daily_snapshot (run_id, trade_id)

trade_run (run_id)
    └─ daily_equity_curve (run_id, trade_date)
    └─ backtest_summary (run_id)
    └─ drawdown_analysis (run_id)
```

常用 JOIN 查询模板：

```sql
-- 查询单次回测所有赢单
SELECT tr.code, tr.signal_date, tr.r_multiple, tr.net_pnl, tr.exit_reason
FROM trade_record tr
WHERE tr.run_id = ?
  AND tr.r_multiple > 0
ORDER BY tr.r_multiple DESC;

-- 查询权益曲线
SELECT trade_date, total_equity, drawdown_pct
FROM daily_equity_curve
WHERE run_id = ?
ORDER BY trade_date;

-- 按 exit_reason 分组统计
SELECT exit_reason,
       COUNT(*) AS count,
       AVG(r_multiple) AS avg_r,
       AVG(hold_days) AS avg_hold
FROM trade_record
WHERE run_id = ?
GROUP BY exit_reason;
```

---

## 7. Bootstrap 函数设计

```python
TRADE_RUNTIME_SCHEMA_SQL = [
    "CREATE TABLE IF NOT EXISTS trade_run (...)",
    "CREATE TABLE IF NOT EXISTS trade_record (...)",
    "CREATE TABLE IF NOT EXISTS order_event (...)",
    "CREATE TABLE IF NOT EXISTS fill_record (...)",
    "CREATE TABLE IF NOT EXISTS position_daily_snapshot (...)",
    "CREATE TABLE IF NOT EXISTS daily_equity_curve (...)",
    "CREATE TABLE IF NOT EXISTS backtest_summary (...)",
    "CREATE TABLE IF NOT EXISTS drawdown_analysis (...)",
]

def bootstrap_trade_runtime(database_path: Path | None = None) -> Path:
    """初始化 trade_runtime.duckdb 的完整 schema。"""
    settings = default_settings()
    resolved = Path(database_path or settings.databases.trade_runtime)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(resolved))
    try:
        for sql in TRADE_RUNTIME_SCHEMA_SQL:
            conn.execute(sql)
    finally:
        conn.close()
    return resolved
```

---

## 8. 与父系统的对比取舍

| 父系统表 | 本系统处理 | 原因 |
|---|---|---|
| `signal_snapshot` | 合并进 `trade_record.signal_id/pattern` | 信号已在 research_lab 存储，无需重复 |
| `order_intent` | → `order_event`（简化版） | 只需流水，不需单独 intent 表 |
| `position_snapshot` | → `position_daily_snapshot` | 精简字段，保留核心持仓状态 |
| `replay_trade` | → `trade_record`（合并） | 不做独立 replay，直接生命周期记录 |
| `rebalance_period/signal/position` | 暂不实现 | 当前无滚动再平衡需求 |
| `execution_fill` | → `fill_record` | 精简字段，移除 liquidity_tier |
| `order_ticket + order_state_event` | → `order_event`（流水） | 合并为单张流水表 |
| `benchmark_window` | 暂不实现 | benchmark 是研究层工具，不在主线 |
| `equity_drawdown_analysis` | → `drawdown_analysis` | 保留，回撤分析是核心 |
| `broker_order_instruction` | 暂不实现 | 实盘预留，当前 Simulated 不需要 |
| `account_state_snapshot` | 合并进 `daily_equity_curve` | 不需要 period_index 维度 |
| `continuous_position_state` | → `position_daily_snapshot` | 同义，合并 |
| `broker_session_state` | 暂不实现 | 实盘才需要 |
| `corporate_action_adjustment_event` | 暂不实现 | 数据层已后复权，broker 层免除 |
| `pas_signal_event` | 不实现 | 信号在 research_lab 已有，无需重复 |
| `entry_execution_plan + risk_unit_state` | 合并进 `trade_record` | 字段直接在 trade_record 存储 |
| `trade_position_leg + trailing_stop_state + exit_decision_event` | 合并进 `position_daily_snapshot + order_event` | TradeManager 内部状态落在快照和流水 |

---

## 9. 扩展路径

当以下需求出现时，按顺序扩展：

```
P1（当前）：8 张核心表
P2（滚动回测）：+ rebalance_period, rebalance_signal, rebalance_position
P3（实盘对接）：+ broker_order_instruction, broker_session_state
P4（企业行动）：+ corporate_action_adjustment_event
P5（benchmark）：+ benchmark_window
```

每次扩展必须开新卡，并更新本文档的扩展路径记录。
