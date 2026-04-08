# CARD-008 BOF 在 BULL_MAINSTREAM 格的独立三年验证 / 2026-04-06

**状态**: `pending-validation`
**类型**: `alpha / validation / bof-mainline`
**模块**: `malf`, `structure`, `filter`, `alpha/pas`, `trade`

## 1. 定位

这张卡只解决一件事：

验证 `BOF` 作为当前主线策略，在三年样本窗口内是否仍具备稳定、可复述、可解释的正收益特征。

标题中的 `BULL_MAINSTREAM` 只保留为历史命名；当前正式分组必须以 `016-021` 之后的执行合同为准，不再把旧 `surface_label` 当作 authoritative 主轴。

## 2. 固定因素

1. `BOF` 在当前系统中的定位是 `MAINLINE`，本卡验证的是“是否维持该定位”，不是预设其必然成立。
2. 若需要按背景拆分，只允许使用当前正式字段，如 `execution_context_snapshot`、`malf_context_4` 及相关生命周期合同；旧 `surface_label` 只能作为历史对照注记。
3. 本卡只验证 `BOF` 表现，不在本卡改 detector、改 `position` sizing、改 `trade` 执行模板。
4. 验证窗口以三年样本为主，可沿用 `2020-2022` 作为历史对照窗口，但必须保证样本筛选口径可复述。

## 3. 输出要求

1. 以正式 `BOF` 信号、正式仓位计划与正式交易结果作为样本来源。
2. 统计信号数、可执行率、胜率、平均 `R`、中位数 `R`、净 `R`、最大连续亏损等核心指标。
3. 至少做两类拆分：按年度拆分、按当前正式 MALF 背景拆分。
4. 必须解释与历史版本结论的差异来源，不能只给“比旧版好/差”的结论。

## 4. 本卡回答的问题

1. `BOF` 是否仍然配得上 `MAINLINE` 定位？
2. 三年窗口内的正收益是否具有年度稳定性，而不是由单一年份拉动？
3. 在当前正式背景合同下，`BOF` 最稳定的背景区域是什么？

## 5. 非目标

1. 不在本卡验证 `TST / PB / CPB`。
2. 不在本卡回退到旧 `surface_label` 体系作为正式准入门槛。
3. 不在本卡直接输出参数调优方案。

## 6. 证据目标

1. 三年总表：样本数、胜率、平均 `R`、净 `R`、最大回撤或最大连亏。
2. 年度拆分表：逐年样本、逐年净 `R`、逐年胜率。
3. 正式背景拆分表：至少一组当前 MALF 正式背景分组比较。
4. record / conclusion 中明确写出“维持 MAINLINE / 降级观察 / 暂不成立”的判断。

## 7. 关闭条件

1. 样本来源、筛选口径、统计口径全部可复述。
2. evidence / record / conclusion 四件套补齐。
3. 结论能明确回答 `BOF` 的主线定位是否被当前系统继续支持。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/008-bof-bull-mainstream-three-year-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/008-bof-bull-mainstream-three-year-validation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `008-bof-bull-mainstream-three-year-validation-conclusion-YYYYMMDD.md`
