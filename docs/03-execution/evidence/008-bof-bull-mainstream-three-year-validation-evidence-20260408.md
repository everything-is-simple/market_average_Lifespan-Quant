# 008. BOF 在 BULL_MAINSTREAM 格的独立三年验证 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/008-bof-bull-mainstream-three-year-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/008-bof-bull-mainstream-three-year-validation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `008` 卡纠偏为当前系统口径的 `BOF` 主线验证卡。
2. 已明确旧 `BULL_MAINSTREAM` 只保留为历史命名，不再作为当前正式主轴。
3. 已在卡内明确：正式分组必须以 `016-021` 之后的执行合同为准。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖正式 `BOF` 信号、正式仓位计划与正式交易结果。
2. 本卡如需按背景拆分，应优先使用 `execution_context_snapshot`、`malf_context_4` 等当前正式字段。
3. 旧 `surface_label` 当前仅允许作为历史对照注记，不作为 authoritative 主轴。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. 三年总表：样本数、胜率、平均 `R`、净 `R`、最大连亏或最大回撤。
2. 年度拆分表：逐年样本、逐年胜率、逐年净 `R`。
3. 正式背景拆分表：至少一组当前 MALF 正式背景分组比较。
4. 对历史版本结论差异的书面解释。

## 当前结论性证据

1. 本轮完成的是 execution 卡面纠偏与闭环准备，不是三年统计验证本身。
2. 当前可以确认的结论是：`008` 已具备进入真实验证执行的卡面与闭环入口。

## 真实执行模板（基于已确认字段）

1. 样本主表：`research_lab.duckdb.pas_formal_signal`，筛选条件为 `pattern = 'BOF'` 与目标时间窗口。
2. 背景主表：`malf.duckdb.execution_context_snapshot`，按 `entity_scope = 'stock'`、`entity_code = code`、`calc_date = signal_date` 关联；正式字段优先使用 `long_background_2`、`intermediate_role_2`、`malf_context_4`，不再回退到旧 `surface_label`。
3. 交易结果表：`trade_runtime.duckdb.trade_record`，筛选条件为 `signal_pattern = 'BOF'`；与信号表按 `code + signal_date + signal_pattern` 关联。
4. 若标题中的 `BULL_MAINSTREAM` 需要落到真实字段，执行口径应写成：`malf_context_4 = 'BULL_MAINSTREAM'`，并在 evidence 中注明这只是历史命名在当前正式字段上的映射。
5. evidence 最终至少应落三张表：三年总表、年度拆分表、按 `malf_context_4` 或等价正式背景字段的分组表。
