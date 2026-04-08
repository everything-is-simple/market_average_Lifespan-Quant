# 009. structure 与 BOF 联合验证 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/009-structure-bof-joint-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/009-structure-bof-joint-validation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `009` 卡纠偏为当前系统口径的 `structure × BOF` 联合验证卡。
2. 已在卡内明确：正式背景拆分若有需要，应使用当前正式字段，如 `malf_context_4`，不得回退到旧 `surface_label` 主轴。
3. 已在卡内明确：本卡只验证 `structure` 对 `BOF` 的区分力，不直接修改 detector、阈值或 trade 模板。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖正式 `BOF` 信号、正式结构位快照、正式交易结果。
2. 本卡关注的关键区分维度包括结构明确性、空间信息与阈值敏感性。
3. 本卡当前不承诺结构位一定提升 `BOF`，而是要求结果可复述、可否证。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. 分组对比表：样本数、胜率、平均 `R`、净 `R`。
2. 至少一轮阈值敏感性比较表。
3. 对结果统计稳定性的文字解释。
4. 对“structure 是否真实提升 BOF 质量”的最终判断。

## 当前结论性证据

1. 本轮完成的是 execution 卡面纠偏与闭环准备，不是联合统计验证本身。
2. 当前可以确认的结论是：`009` 已具备进入真实验证执行的卡面与闭环入口。

## 真实执行模板（基于已确认字段）

1. 结构主表：`structure.duckdb.structure_snapshot`，可直接使用字段 `has_clear_structure`、`nearest_support_price`、`nearest_resistance_price`、`available_space_pct`、`recent_breakout_type`、`recent_breakout_confirmed`。
2. 信号主表：`research_lab.duckdb.pas_formal_signal`，筛选 `pattern = 'BOF'`。
3. 交易结果表：`trade_runtime.duckdb.trade_record`，筛选 `signal_pattern = 'BOF'`。
4. 关联键优先使用 `code + signal_date`；信号/交易联结时再补 `pattern / signal_pattern = 'BOF'` 约束。
5. evidence 至少应产出三组结果：
   - 按 `has_clear_structure` 分组的表现对比
   - 按 `available_space_pct` 阈值分组的表现对比
   - 按 `recent_breakout_type / recent_breakout_confirmed` 的敏感性对比
