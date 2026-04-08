# position 合同与 sizing 规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/position/00-position-charter-20260331.md`。

## 1. 范围

本规格冻结：

1. `PositionPlan / ExitLeg / PositionExitPlan` 合同字段约束
2. `compute_position_plan()` 与 `build_exit_plan()` 的最小执行合同
3. `position` 对上游 `PasSignal` 与下游 `trade` 的桥接边界

本规格不覆盖：

1. 9 种 sizing 家族的完整研究表 schema
2. `research_lab` 中 5 张 position 研究表的真实落库实现
3. system 层如何选择 position policy

## 2. 当前实现状态

当前已核实到的 position 代码落点：

1. `src/lq/position/contracts.py` — 已实现
2. `src/lq/position/sizing.py` — 已实现

当前**未在代码中核实到**的内容：

1. position 独立 bootstrap
2. position 独立 pipeline
3. `research_lab` 中 5 张 position 研究表的当前实现与写入逻辑

因此，本规格当前定位为：

- **正式合同 + sizing 计算规格**
- 不把 design 中的研究表目标态冒充为“已实现 persistence”

## 3. 合同字段约束

### 3.1 `PositionPlan`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `entry_date` | date | `T+1` 执行日 |
| `signal_pattern` | str | `PasTriggerPattern` 值 |
| `signal_low` | float | 信号 K 线低点 |
| `entry_price` | float | `T+1` 开盘预估入场价 |
| `initial_stop_price` | float | 初始止损价 |
| `first_target_price` | float | 第一目标价（`entry + 1R`） |
| `risk_unit` | float | `1R = entry - stop` |
| `lot_count` | int | 实际手数 |
| `notional` | float | 实际名义金额 |

说明：

1. `PositionPlan` 是 trade 前的冻结仓位合同。
2. 当前 sizing 主线仍是 `fixed_notional` 控制线。

### 3.2 `ExitLeg`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `leg_id` | str | 单腿唯一标识 |
| `leg_type` | str | 当前实现为 `first_target / runner / stop` |
| `exit_price` | float | 该腿计划退出价 |
| `lot_count` | int | 该腿手数 |
| `is_partial` | bool | 是否为部分退出 |

### 3.3 `PositionExitPlan`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `plan_id` | str | 退出计划标识 |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `entry_plan` | `PositionPlan` | 入场计划 |
| `legs` | `tuple[ExitLeg, ...]` | 所有退出腿 |
| `trailing_stop_trigger` | float | `build_exit_plan()` 生成的 runner 初始 trigger 占位值，不等同于 trade 运行期的动态最高价 trailing stop |
| `time_stop_days` | int | 时间止损天数上限 |

## 4. 执行合同

### 4.1 头寸规划

```python
plan = compute_position_plan(
    signal,
    entry_price,
    fixed_notional=DEFAULT_FIXED_NOTIONAL,
    lot_size=DEFAULT_LOT_SIZE,
    stop_buffer_pct=STOP_BUFFER_PCT,
)
```

执行语义：

1. `entry_date = next_trading_day(signal.signal_date)`
2. 初始止损默认取 `signal.signal_low * (1 - stop_buffer_pct)`
3. `risk_unit = entry_price - initial_stop`
4. 若 `risk_unit <= 0`，退化为 `entry_price * 0.005`
5. 第一目标价为 `entry_price + risk_unit`

### 4.2 退出计划

```python
exit_plan = build_exit_plan(
    plan,
    trailing_pct=RUNNER_TRAILING_PCT,
    time_stop_days=TIME_STOP_DAYS,
)
```

当前实现语义：

1. 腿 1：`first_target`
2. 腿 2：`runner`
3. `half_lots = max(1, plan.lot_count // 2)`
4. `runner_lots = plan.lot_count - half_lots`
5. `trailing_stop_trigger = plan.entry_price * (1 - trailing_pct)` 只是 `position` 层写出的初始占位值
6. 真正运行期的动态 runner 跟踪止损由 `trade.management` 维护：当前使用 `TRAILING_ACTIVATION_R = 1.0` 与 `TRAILING_STEP_PCT = 0.06`

## 5. A 股与 1R 约束

1. `position` 遵守 `T` 发信号、`T+1` 开盘执行。
2. 当前实现的 `lot_count` 是“手数”，而 `notional` 用 `lot_count * lot_size * entry_price` 计算。
3. `risk_unit > 0` 是正式目标；`<= 0` 时退化为最小风险保护。
4. 当前 sizing 不消费 MALF 生命周期字段做动态调权。

## 6. 写权边界

允许：

1. `position` 读取 `PasSignal`
2. `position` 读取交易日历辅助 `T+1` 计算
3. `trade` 读取 `PositionPlan / PositionExitPlan`

禁止：

1. `position` 直接写 `trade_runtime.duckdb`
2. `position` 代替 `trade` 生成 `TradeRecord`
3. 在未核实 pipeline 的情况下，把 design 中的 5 张研究表宣称为“当前已实现写入”

## 7. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/position/contracts.py` | ✅ 已有 | `PositionPlan / ExitLeg / PositionExitPlan` |
| `src/lq/position/sizing.py` | ✅ 已有 | 1R 头寸规划与退出计划生成 |

## 8. 当前确认的下游消费方式

1. 当前 `trade.pipeline` 直接在 trade 内部调用 `compute_position_plan()`
2. 当前 `trade.pipeline` 尚未核实到对 `PositionExitPlan` 的主线直接消费
3. 当前仓库里尚未核实到“position 独立落库后再由 trade 桥接读取”的正式实现
4. 因此现阶段的真实主线更接近：`PasSignal → compute_position_plan() → TradeManager → TradeRecord`
