# CARD-012 CPB 语义收敛 + 独立正式验证 / 2026-04-06

**状态**: `historical`
**类型**: `alpha / historical-review / cpb`
**模块**: `alpha/pas`, `trade`, `system`

## 1. 定位

这张卡当前保留的意义只有一件事：

把 `CPB` 被归为 `REJECTED` 的理由、边界与未来可能重开的条件写清楚，作为历史追溯页保留，而不是作为当前待执行验证卡继续推进。

## 2. 固定因素

1. 当前系统已将 `CPB` 归为 `REJECTED`，其地位不是“待正式上线验证”，而是“已有否定结论，除非出现强证据，否则不重开”。
2. `system` 层当前不应调用 `CPB` 作为正式策略路径。
3. 本卡不是要求重新启用 `CPB`，而是要求把拒绝结论写得更清楚、更可追溯。
4. 若未来确需重开，必须先回到 design / spec 层重新立项，而不是直接沿用这张旧执行卡开做。

## 3. 历史问题定义

1. `CPB` 与 `BOF` 的语义边界长期不清，历史上存在高重叠风险。
2. 即便拆出 `CPB` 独有样本，也必须证明其有独立增益，否则不能仅凭“不同名”保留。
3. 当前主线关注的是 formal contract 与主线稳定性，不需要为 `CPB` 预留执行入口。

## 4. 非目标

1. 不在本卡启用 `CPB` detector 回灌正式库。
2. 不在本卡尝试把 `CPB` 重新升级为 `CONDITIONAL`。
3. 不在本卡为 `CPB` 编写新的 system 接入路径。

## 5. 若未来重开，必须满足

1. 先明确 `CPB` 与 `BOF` 的 detector 语义边界，并能稳定区分。
2. 能提供 `CPB` 独有样本的独立正收益证据，而不是仅在与 `BOF` 重叠部分上共享收益。
3. 能解释它为何值得占用主线复杂度预算。

## 6. 当前处理结论

1. 本卡已纠偏为历史追溯页，不再作为当前待执行验证卡推进。
2. 当前正式口径仍是：`CPB = REJECTED`。
3. 若未来重开，必须以新的 design/spec 卡重新立项，本卡只能作为历史背景引用。

## 7. 追溯文件

1. 证据：`docs/03-execution/evidence/012-cpb-semantic-convergence-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/012-cpb-semantic-convergence-validation-record-20260408.md`
3. 结论：当前处理结论以内嵌于本卡第 6 节为准；如后续需要独立历史结论，再按实际日期创建 `012-cpb-semantic-convergence-validation-conclusion-YYYYMMDD.md`
