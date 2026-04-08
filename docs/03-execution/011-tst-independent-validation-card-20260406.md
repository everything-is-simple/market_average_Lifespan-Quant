# CARD-011 TST 独立正式验证 / 2026-04-06

**状态**: `pending-validation`
**类型**: `alpha / validation / tst`
**模块**: `malf`, `alpha/pas`, `trade`

## 1. 定位

这张卡只解决一件事：

验证 `TST` 在当前系统里是否仍应被保留为 `CONDITIONAL` 策略，以及它真正适用的背景范围是什么。

## 2. 固定因素

1. `TST` 当前定位是 `CONDITIONAL`，本卡的目标不是“证明它一定优秀”，而是确认它是否值得保留、在哪些条件下保留。
2. 本卡若做背景拆分，只允许使用当前正式执行合同字段；旧 `surface_label`、旧 16 格只能作为历史参考，不得继续充当正式主轴。
3. 本卡不改 `TST` detector，不改 `position` sizing，不改 `trade` 执行模板。
4. 历史样本窗口可采用 `2020-2023`，但必须给出与当前仓库实现一致的筛选口径。

## 3. 输出要求

1. 统计 `TST` 全量信号的样本数、胜率、平均 `R`、净 `R`、年度净 `R`。
2. 按年度拆分，判断其是否存在“仅靠单一年份撑起整体表现”的问题。
3. 按当前正式背景合同拆分，找出 `TST` 可能成立的局部背景。
4. 必须在结论里明确给出：保留为 `CONDITIONAL`、收缩适用范围、或进一步降级观察。

## 4. 本卡回答的问题

1. `TST` 在当前系统中是否仍值得保留？
2. 它的正收益是否具有持续性，而不是偶发性？
3. 若只在少数背景有效，哪些背景才是真正应该保留的条件？

## 5. 非目标

1. 不在本卡验证 `BOF / PB / CPB`。
2. 不在本卡把 `TST` 直接升级为 `MAINLINE`。
3. 不在本卡直接修改 detector 语义。

## 6. 证据目标

1. 全量统计表：样本数、胜率、平均 `R`、净 `R`。
2. 年度拆分表：逐年样本与逐年净 `R`。
3. 正式背景拆分表：至少一组当前 MALF 背景下的有效/无效比较。
4. 对历史结论与当前结果差异的解释。

## 7. 关闭条件

1. 样本筛选口径与统计方法全部可复述。
2. evidence / record / conclusion 四件套补齐。
3. 结论能明确回答 `TST` 是否继续保留为 `CONDITIONAL`，以及其有效背景边界。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/011-tst-independent-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/011-tst-independent-validation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `011-tst-independent-validation-conclusion-YYYYMMDD.md`
