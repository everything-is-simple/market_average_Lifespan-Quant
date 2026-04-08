# 013. 第一 PB 假说独立验证 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/013-first-pb-hypothesis-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/013-first-pb-hypothesis-validation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `013` 卡纠偏为当前系统口径的验证卡。
2. 已在卡内明确 `PB` 当前定位为 `CONDITIONAL`，且本卡只验证“第一笔 `PB` 是否显著优于后续 `PB`”。
3. 已在卡内明确：若正式结果合同中没有 `pb_sequence_number` 或等价字段，本卡不得伪关闭。
4. 已在卡内补入闭环文件约定，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖的核心字段是 `pb_sequence_number`。
2. 本卡当前依赖的结果层路径是：正式 `PB` 信号、正式交易结果、必要时的正式背景合同字段。
3. 本卡已明确：旧 `surface_label` 不再作为正式主轴，只能作为历史参考。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. `pb_sequence_number = 1` 与 `pb_sequence_number >= 2` 的样本数对比表。
2. 两组胜率、平均 `R`、净 `R` 的分组统计表。
3. 年度拆分表。
4. 如样本充分，再补正式背景分组比较表。

## 当前结论性证据

1. 本轮已完成的是 execution 文档纠偏与闭环准备，不是统计验证本身。
2. 当前可以确认的唯一结论是：`013` 已具备进入真实验证执行的卡面与闭环入口。

## 真实执行模板（基于已确认字段）

1. 主信号表：`research_lab.duckdb.pas_formal_signal`，筛选 `pattern = 'PB'`，并直接读取 `pb_sequence_number`。
2. 若需核对触发完整性，可辅查 `research_lab.duckdb.pas_selected_trace` 的 `pb_sequence_number` 字段，确认 trace 与正式信号是否一致。
3. 交易结果表：`trade_runtime.duckdb.trade_record`，筛选 `signal_pattern = 'PB'`，并直接读取 `pb_sequence_number`。
4. 正式比较分组应至少分为两组：`pb_sequence_number = 1` 与 `pb_sequence_number >= 2`；信号/交易联结键优先使用 `code + signal_date + signal_pattern + pb_sequence_number`。
5. 若需做背景拆分，优先使用 `pas_formal_signal` 已落入的 `malf_context_4`、`long_background_2`、`intermediate_role_2`，不足时再回查 `malf.duckdb.execution_context_snapshot`。
