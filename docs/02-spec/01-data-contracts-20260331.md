# 跨模块结果合同总览 / 2026-04-08

> 本文件是 `02-spec/` 根层总览，汇总当前主线下的跨模块结果合同与七库读写边界。
> 更细的字段、表结构、runner 约束，优先以各模块独立 spec 为准；若模块 spec 暂缺，则必须回到当前代码与已闭环 execution 结论核实。

## 1. 原则

1. 模块间只传**结果合同**，不传内部中间 DataFrame 或内部特征矩阵。
2. 正式主线固定为：`data → malf → structure → filter → alpha/pas → position → trade → system`。
3. 正式字段与兼容残留必须明确区分；兼容字段允许保留，但不得冒充当前主轴。
4. 若根层总览与模块独立 spec 冲突，以**模块独立 spec** 为准。
5. 若 spec 与已闭环 execution 结论冲突，应先回看对应结论，再修 spec，不得凭记忆补写。

## 2. 核心结果合同一览

### 2.1 `MalfContext`（`malf → filter / alpha`）

当前代码落点：`src/lq/malf/contracts.py`

字段分层：

1. 定位字段：`code`、`signal_date`
2. 执行层主字段：`long_background_2`、`intermediate_role_2`、`malf_context_4`
3. 计算层兼容字段：`monthly_state`、`weekly_flow`、`monthly_strength`、`weekly_strength`
4. 日线节奏字段：`is_new_high_today`、`new_high_seq`、`days_since_last_new_high`、`new_high_count_in_window`
5. 生命周期字段：`amplitude_rank_*`、`duration_rank_*`、`new_price_rank_*`、`lifecycle_rank_*`
6. 四分位辅助字段：`amplitude_quartile`、`duration_quartile`、`new_price_quartile`、`lifecycle_quartile`

正式主轴说明：

1. 当前执行层主轴是 `long_background_2 / intermediate_role_2 / malf_context_4`。
2. `monthly_state / weekly_flow` 允许保留为兼容诊断字段，但不再是执行层正式主字段。

### 2.2 `StructureSnapshot`（`structure → filter / alpha`）

当前代码落点：`src/lq/structure/contracts.py`

正式字段：

1. `code`
2. `signal_date`
3. `support_levels`
4. `resistance_levels`
5. `recent_breakout`
6. `nearest_support`
7. `nearest_resistance`

派生读数：

1. `has_clear_structure`
2. `available_space_pct`

### 2.3 `AdverseConditionResult`（`filter → alpha / system`）

当前代码落点：`src/lq/filter/adverse.py`

正式字段：

1. `code`
2. `signal_date`
3. `active_conditions`
4. `tradeable`
5. `notes`

说明：`tradeable=True` 只表示“允许进入 trigger 探测”，不等于已经产生信号。

### 2.4 `PasSignal`（`alpha/pas → position`）

当前代码落点：`src/lq/alpha/pas/contracts.py`

正式字段分组：

1. 标识字段：`signal_id`、`code`、`signal_date`、`pattern`
2. MALF 正式字段：`malf_context_4`、`long_background_2`、`intermediate_role_2`
3. 价格与强度字段：`strength`、`signal_low`、`entry_ref_price`
4. 生命周期字段：`amplitude_rank_*`、`duration_rank_*`、`new_price_rank_*`、`lifecycle_rank_*`
5. 四分位字段：`amplitude_quartile`、`duration_quartile`、`new_price_quartile`、`lifecycle_quartile`
6. 兼容字段：`monthly_state`、`weekly_flow`
7. 研究增强字段：`pb_sequence_number`

说明：

1. `pb_sequence_number` 已是正式合同字段，不再只是研究草稿。
2. `monthly_state / weekly_flow` 仍可能出现在 `PasSignal` 中，但当前属于兼容保留，不替代 `malf_context_4`。

### 2.5 `PositionPlan`（`position → trade`）

当前代码落点：`src/lq/position/contracts.py`

正式字段：

1. `code`
2. `signal_date`
3. `entry_date`
4. `signal_pattern`
5. `signal_low`
6. `entry_price`
7. `initial_stop_price`
8. `first_target_price`
9. `risk_unit`
10. `lot_count`
11. `notional`

### 2.6 `TradeRecord`（`trade → system / report`）

当前代码落点：`src/lq/trade/contracts.py`

正式字段分组：

1. 标识字段：`trade_id`、`code`、`signal_date`、`entry_date`、`exit_date`
2. 信号来源字段：`signal_pattern`、`malf_context_4`、`pb_sequence_number`
3. 价格与仓位字段：`entry_price`、`exit_price`、`lot_count`、`initial_stop_price`、`first_target_price`、`risk_unit`
4. 结果字段：`pnl_amount`、`pnl_pct`、`r_multiple`、`exit_reason`
5. 生命周期字段：`lifecycle_state`

### 2.7 兼容字段治理

1. `monthly_state`、`weekly_flow` 允许作为兼容诊断字段存在。
2. `surface_label`、旧 `pas_context` 等旧命名不再作为当前正式主轴写入根层 spec。
3. 若某模块仍保留兼容字段，必须在该模块 spec 或 design 中显式标注其兼容身份。

## 3. 七数据库写权与读取边界

**核心原则**：七库全持久化；历史一旦发生就是永恒的瞬间——绝不因“顺手方便”退回单次内存计算口径。

| 层级 | 数据库 | Owner | 主要消费者 | 当前已确认主表 / 主输出 |
|---|---|---|---|---|
| L1 | `raw_market` | `data` | `data` | `raw_stock_daily`、`raw_xdxr_event` |
| L2 | `market_base` | `data` | `malf`、`structure`、`alpha`、`trade` | `stock_daily_adjusted` |
| L3 | `malf` | `malf` | `filter`、`alpha`、`system` | `execution_context_snapshot` |
| L3 | `structure` | `structure` | `filter`、`alpha` | `structure_snapshot` |
| L3 | `filter` | `filter` | `alpha`、`system` | `filter_snapshot` |
| L3 | `research_lab` | `alpha/pas`、`position` | `trade`、`system` | `pas_selected_trace`、`pas_formal_signal` |
| L4 | `trade_runtime` | `trade`、`system` | `system`、`report` | `trade_record` |

边界规则：

1. 模块只写自己拥有的正式数据库。
2. 下游可以读上游正式输出，但不得反向写入上游库。
3. 根层总览只确认当前已核实的表与边界；更细 schema 仍需回到模块 spec 与代码。

### 3.1 当前已核实的正式落表

1. `market_base.stock_daily_adjusted`
2. `malf.execution_context_snapshot`
3. `structure.structure_snapshot`
4. `filter.filter_snapshot`
5. `research_lab.pas_selected_trace`
6. `research_lab.pas_formal_signal`
7. `trade_runtime.trade_record`

### 3.2 Runner 与内存控制约定

1. 单机约束仍是 32G 内存上限。
2. 各 runner 必须优先遵守“读 → 算 → 写 → 释放”的批处理循环。
3. 允许按股票批次或日期区间分批，不允许跨批无界累积中间结果。
4. checkpoint / resume 是主线推荐能力，但是否已在每个模块完全落地，必须回到对应模块 runner 核实。

### 3.3 关于 `config_hash`

1. `config_hash` selective rebuild 是全局设计纪律。
2. 但根层总览**不再假定**每张正式表都已经完整实现该字段。
3. 是否已实际落库，必须以对应模块 schema、pipeline 与 execution 结论为准。

## 4. 模块级 spec 覆盖现状

当前已存在独立 spec：

1. `modules/core/01-core-contracts-paths-and-resumable-spec-20260408.md`
2. `modules/data/01-data-l2-backward-adjustment-compute-spec-20260401.md`
3. `modules/malf/01-malf-four-context-lifecycle-execution-contract-spec-20260407.md`
4. `modules/alpha/01-alpha-pas-contracts-and-pipeline-spec-20260401.md`
5. `modules/structure/01-structure-snapshot-contracts-and-pipeline-spec-20260408.md`
6. `modules/filter/01-filter-adverse-conditions-and-pipeline-spec-20260408.md`
7. `modules/position/01-position-contracts-and-sizing-spec-20260408.md`
8. `modules/trade/01-trade-runtime-and-backtest-pipeline-spec-20260408.md`
9. `modules/system/01-system-orchestration-and-governance-spec-20260408.md`

当前模块级 spec 已全覆盖。
