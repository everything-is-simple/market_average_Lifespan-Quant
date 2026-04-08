# 009. structure 与 BOF 联合验证 卡

**状态**: `pending-validation`
**类型**: `structure / validation / bof-joint`
**模块**: `structure`, `alpha/pas`, `trade`

## 1. 定位

这张卡只解决一件事：

在当前系统正式主线下，验证 `structure` 模块输出的结构位信息，是否对 `BOF` 信号质量具有可复述的正向区分力。

## 2. 固定因素

1. `016-021` 已冻结并实现了当前 MALF 正式消费主线；本卡不得回退到旧三层矩阵口径。
2. 本卡如果需要按背景分组，只允许使用当前正式字段，如 `malf_context_4`；不得再把旧 `surface_label` 写成正式主轴。
3. 本卡只做验证，不在本卡直接改 `structure` 阈值、`BOF` 检测器或 `trade` 执行模板。
4. 若结果显示无区分力，必须接受“structure 对 BOF 增益不足”的结论，不得为保留模块而美化结果。

## 3. 输出要求

1. 以正式 `BOF` 信号、正式结构位快照、正式交易结果为样本源。
2. 至少比较两组：有明确结构优势 vs 结构不明确或空间不足。
3. 对 `available_space_pct` 等关键阈值做有限敏感性比较，但不在本卡直接下调主线阈值。
4. 形成 evidence / record / conclusion 四件套。

## 4. 本卡回答的问题

1. `structure` 对 `BOF` 的区分力是否真实存在？
2. 如果存在，主要体现在命中率、胜率、R 倍数还是回撤控制？
3. 如果不存在，后续应保留 `structure` 的哪类功能，放弃哪类主线预期？

## 5. 非目标

1. 不验证 `TST / PB / CPB` 与结构位的联合效果。
2. 不在本卡修改 `BOF` detector 形态定义。
3. 不在本卡重写 `structure` 模块设计章程。

## 6. 证据目标

1. 分组对比表：胜率、平均 R、净收益、样本数。
2. 至少一轮阈值敏感性对比。
3. 对结果是否具有稳定统计意义的解释。

## 7. 关闭条件

1. 已形成可复述的样本筛选口径与分组方法。
2. 证据表、执行记录、结论全部补齐。
3. 结论能明确回答“structure 是否提升 BOF 质量”，不能只给描述性截图。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/009-structure-bof-joint-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/009-structure-bof-joint-validation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `009-structure-bof-joint-validation-conclusion-YYYYMMDD.md`
