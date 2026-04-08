# 010. filter 不利条件过滤器效果评估 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/010-filter-adverse-condition-evaluation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/010-filter-adverse-condition-evaluation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `010` 卡纠偏为当前系统口径的 `filter` 效果评估卡。
2. 已在卡内明确：本卡必须基于当前正式链路，且 `019` 之后不得再把旧 `monthly_state / weekly_flow` 写成 filter 的正式主轴。
3. 已在卡内明确：本卡是评估卡，不直接增删 filter 条件，也不直接修改主线阈值。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖正式 `filter` 结果、正式信号结果与正式交易结果。
2. 本卡要求至少比较三组：通过过滤、被过滤、不过滤基线。
3. 本卡要求拆出单条件贡献，避免只给整体结果。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. 五类条件频率表。
2. 三组对比表：通过过滤 / 被过滤 / 无过滤基线。
3. 单条件贡献表。
4. 对“filter 是否值得保留为主线准入层”的最终判断。

## 当前结论性证据

1. 本轮完成的是 execution 卡面纠偏与闭环准备，不是过滤器效果统计本身。
2. 当前可以确认的结论是：`010` 已具备进入真实验证执行的卡面与闭环入口。

## 真实执行模板（基于已确认字段）

1. 过滤主表：`filter.duckdb.filter_snapshot`，当前正式输出字段已确认包含 `tradeable`、`condition_count`、`active_conditions`、`notes`。
2. 下游信号表：`research_lab.duckdb.pas_formal_signal`。
3. 下游交易表：`trade_runtime.duckdb.trade_record`。
4. `通过过滤` 组可以直接定义为：`filter_snapshot.tradeable = TRUE` 且存在下游信号/交易记录。
5. `被过滤` 组可以直接从 `filter_snapshot.tradeable = FALSE` 抽样，并按 `condition_count`、`active_conditions` 统计频率。
6. **当前正式主线表无法直接给出“无过滤基线”**；若要做该对照，必须单独执行一轮“禁用 filter 的实验 run”，并将其作为独立 evidence 资产记录，不能假设正式库中已经存在该基线。
