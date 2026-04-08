# 011. TST 独立正式验证 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/011-tst-independent-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/011-tst-independent-validation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `011` 卡纠偏为当前系统口径的 `TST` 验证卡。
2. 已在卡内明确 `TST` 当前定位是 `CONDITIONAL`，本卡目标是确认其是否值得保留及其有效背景边界。
3. 已在卡内明确：旧 `surface_label`、旧 16 格只能作为历史参考，不得再作为正式主轴。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖正式 `TST` 信号与正式交易结果。
2. 若做背景拆分，应使用当前正式执行合同字段，而非旧 `surface_label` 主轴。
3. 本卡当前不要求改 detector、position sizing 或 trade 执行模板。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. 全量统计表：样本数、胜率、平均 `R`、净 `R`。
2. 年度拆分表：逐年样本与逐年净 `R`。
3. 正式背景拆分表：至少一组当前背景下的有效/无效比较。
4. 对历史结论与当前结果差异的解释。

## 当前结论性证据

1. 本轮完成的是 execution 卡面纠偏与闭环准备，不是 `TST` 统计验证本身。
2. 当前可以确认的结论是：`011` 已具备进入真实验证执行的卡面与闭环入口。

## 真实执行模板（基于已确认字段）

1. 样本主表：`research_lab.duckdb.pas_formal_signal`，筛选 `pattern = 'TST'`。
2. 交易结果表：`trade_runtime.duckdb.trade_record`，筛选 `signal_pattern = 'TST'`。
3. 若要做正式背景拆分，优先读取 `pas_formal_signal` 中已落入的 `long_background_2`、`intermediate_role_2`、`malf_context_4` 与各类 rank / quartile 字段；不足时再回查 `malf.duckdb.execution_context_snapshot`。
4. 信号/交易联结键优先使用 `code + signal_date + pattern` 对 `code + signal_date + signal_pattern`。
5. evidence 最终至少应落三张表：全量统计表、年度拆分表、按 `malf_context_4` 或等价正式背景字段的分组表。
