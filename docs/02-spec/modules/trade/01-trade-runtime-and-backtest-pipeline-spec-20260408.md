# trade runtime 与 backtest pipeline 规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/trade/00-trade-charter-20260404.md`。

## 1. 范围

本规格冻结：

1. `TradeRecord / TradeRunSummary` 合同字段约束
2. `trade_runtime.duckdb` 中 `trade_record / trade_run_summary / trade_build_manifest` 的主字段与写权边界
3. `TradeManagementState / TradeManager / run_trade_build()` 与脚本入口的最小执行合同

本规格不覆盖：

1. 完整 Broker 实现
2. A 股成本模型完整版
3. system 层组合级汇总与基准对照

## 2. 当前实现状态

当前已核实到的 trade 代码落点：

1. `src/lq/trade/contracts.py` — 已实现
2. `src/lq/trade/management.py` — 已实现
3. `src/lq/trade/pipeline.py` — 已实现
4. `scripts/trade/build_trade_backtest.py` — 已实现

当前特别说明：

1. schema 中已定义 `trade_run_summary` 表。
2. 但截至本轮核实，`run_trade_build()` 已确认写入的是：
   - `trade_record`
   - `trade_build_manifest`
3. **尚未在当前 pipeline 中核实到 `trade_run_summary` 的实际写入语句。**

## 3. 合同字段约束

### 3.1 `TradeRecord`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `trade_id` | str | 单笔交易唯一标识 |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `entry_date` | date | 入场日期 |
| `exit_date` | `date | None` | 退出日期 |
| `signal_pattern` | str | 来源 trigger |
| `malf_context_4` | str | 正式 MALF 四格上下文 |
| `entry_price` | float | 入场价 |
| `exit_price` | `float | None` | 退出价 |
| `lot_count` | int | 手数 |
| `initial_stop_price` | float | 初始止损价 |
| `first_target_price` | float | 第一目标价 |
| `risk_unit` | float | 初始 1R |
| `pnl_amount` | `float | None` | 盈亏金额 |
| `pnl_pct` | `float | None` | 盈亏比例 |
| `r_multiple` | `float | None` | R 倍数 |
| `exit_reason` | `str | None` | 退出原因 |
| `lifecycle_state` | str | `TradeLifecycleState` 最终状态 |
| `pb_sequence_number` | `int | None` | 第一 PB 序号 |

### 3.2 `TradeRunSummary`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `run_id` | str | run 唯一标识 |
| `strategy_name` | str | 策略名称 |
| `asof_date` | date | 截止日期 |
| `signal_count` | int | 处理信号数 |
| `trade_count` | int | 交易数 |
| `win_count` | int | 胜笔数 |
| `loss_count` | int | 败笔数 |
| `avg_r_multiple` | `float | None` | 平均 R |
| `avg_pnl_pct` | `float | None` | 平均收益率 |
| `max_drawdown_pct` | `float | None` | 最大回撤 |

说明：

1. 该合同已在代码中定义。
2. 但当前 pipeline 是否已经完整产出并落库，必须以实际写入逻辑为准。

## 4. `trade_runtime.duckdb` 主表与写权边界

### 4.1 主表

由 `src/lq/trade/pipeline.py` 中 `TRADE_RUNTIME_SCHEMA_SQL` 建立：

| 表名 | 说明 |
| --- | --- |
| `trade_record` | 每笔已完成交易记录 |
| `trade_run_summary` | 回测 run 汇总表 |
| `trade_build_manifest` | 构建 manifest |

### 4.2 `trade_record` 最小列要求

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `trade_id` | VARCHAR | 交易主键 |
| `code` | VARCHAR | 股票代码 |
| `signal_date` | DATE | 信号日期 |
| `entry_date` | DATE | 入场日期 |
| `exit_date` | DATE | 退出日期 |
| `signal_pattern` | VARCHAR | 来源 trigger |
| `malf_context_4` | VARCHAR | MALF 四格上下文 |
| `entry_price` | DOUBLE | 入场价 |
| `exit_price` | DOUBLE | 退出价 |
| `lot_count` | INTEGER | 手数 |
| `initial_stop_price` | DOUBLE | 初始止损 |
| `first_target_price` | DOUBLE | 第一目标 |
| `risk_unit` | DOUBLE | 1R |
| `pnl_amount` | DOUBLE | 盈亏金额 |
| `pnl_pct` | DOUBLE | 盈亏比例 |
| `r_multiple` | DOUBLE | R 倍数 |
| `exit_reason` | VARCHAR | 退出原因 |
| `lifecycle_state` | VARCHAR | 生命周期状态 |
| `pb_sequence_number` | INTEGER | 第一 PB 序号 |
| `run_id` | VARCHAR | run 标识 |
| `created_at` | TIMESTAMP | 写入时间 |

### 4.3 写权边界

允许：

1. `trade` 写 `trade_runtime.duckdb`
2. `trade` 读 `research_lab.pas_formal_signal`
3. `trade` 读 `market_base.stock_daily_adjusted`
4. `trade` 在内部调用 `position.sizing` 与 `TradeManager`

禁止：

1. `trade` 写 `research_lab.duckdb`
2. `trade` 回写 `pas_formal_signal`
3. `trade` 伪造上游 `MalfContext` 或 `PasSignal`

## 5. 执行合同

### 5.1 交易管理状态

`TradeManagementState` 当前最小核心字段：

1. `trade_id`
2. `code`
3. `signal_date`
4. `entry_date`
5. `entry_price`
6. `initial_stop_price`
7. `first_target_price`
8. `risk_unit`
9. `total_lots`
10. `active_lots`
11. `signal_pattern`
12. `malf_context_4`
13. `pb_sequence_number`
14. `lifecycle_state`
15. `current_stop_price`
16. `highest_price_seen`
17. `hold_days`
18. `first_target_hit`
19. `breakeven_triggered`

### 5.2 TradeManager 生命周期语义

当前实现的关键步骤：

1. `activate(entry_price)` 后进入 `ACTIVE_INITIAL_STOP`
2. 先检查初始止损
3. 再检查第一目标半仓止盈
4. 盈利超过阈值后提损到成本价
5. 进入 runner 跟踪止损
6. 达到最大持仓天数后触发时间止损

### 5.3 多日期批量回测

```python
result = run_trade_build(
    market_base_path=Path(...),
    malf_db_path=Path(...),
    research_lab_path=Path(...),
    trade_db_path=Path(...),
    signal_dates=[...],
    codes=None,
    strategy_name="pas_default",
    resume=False,
    reset_checkpoint=False,
    settings=None,
    verbose=True,
)
```

当前真实流程：

1. 按日期逐日处理
2. 从 `research_lab.pas_formal_signal` 读取当日信号
3. 在 trade 内部构造 `PasSignal`
4. 调用 `compute_position_plan()` 生成头寸规划
5. 创建 `TradeManagementState` 并驱动 `TradeManager.update()`
6. 调用 `to_trade_record()` 生成最终 `TradeRecord`
7. 写入 `trade_record`
8. 写入 `trade_build_manifest`

### 5.4 脚本入口

```text
python scripts/trade/build_trade_backtest.py --start 2015-01-01 --end 2026-04-07
python scripts/trade/build_trade_backtest.py --date 2026-04-07
python scripts/trade/build_trade_backtest.py --start 2015-01-01 --end 2026-04-07 --resume
```

## 6. 幂等与恢复约束

1. `trade_record` 以 `trade_id` 为主键。
2. 当前 pipeline 采用“按 `trade_id` 先删后插”的方式实现幂等重写。
3. 支持 checkpoint 断点续传。
4. 根层设计纪律中的 `config_hash` 仍是全局方向，但本规格不假定当前 `trade_runtime` 表已完整落地该字段。

## 7. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/trade/contracts.py` | ✅ 已有 | `TradeRecord / TradeRunSummary` |
| `src/lq/trade/management.py` | ✅ 已有 | `TradeManagementState / TradeManager` |
| `src/lq/trade/pipeline.py` | ✅ 已有 | schema、批量回测、checkpoint、落表 |
| `scripts/trade/build_trade_backtest.py` | ✅ 已有 | CLI 入口 |

## 8. 当前与设计目标的差异

1. design 中的完整 Broker / BacktestEngine / 成本模型是目标态，不等于当前已全部实现。
2. 当前已核实主线是一个简化的 trade pipeline。
3. 当前已核实的 position-trade 桥接发生在 `trade.pipeline` 内部，而不是先落 position 独立研究表再桥接读取。
