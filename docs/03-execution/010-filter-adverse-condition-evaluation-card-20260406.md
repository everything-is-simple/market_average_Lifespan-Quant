# 010. filter 不利条件过滤器效果评估 卡

**状态**: `pending-validation`
**类型**: `filter / validation / adverse-evaluation`
**模块**: `filter`, `alpha/pas`, `trade`

## 1. 定位

这张卡只解决一件事：

评估 `filter` 五类不利条件在当前主线上的净效果，确认它们是否真的提升了正式信号质量，而不是只是在减少样本。

## 2. 固定因素

1. 本卡必须基于当前正式系统链路：`data → malf → structure → filter → alpha/pas → position → trade → system`。
2. `019` 已经收敛 A4-5 的背景合同；本卡不得再把 `monthly_state / weekly_flow` 写成 filter 的正式主轴。
3. 本卡是评估卡，不在本卡直接增删 filter 条件，也不直接修改主线阈值。
4. 如果某类条件无贡献甚至负贡献，必须如实记录，并作为后续设计修订入口。

## 3. 输出要求

1. 统计五类不利条件的触发频率与组合频率。
2. 至少比较三组：通过过滤、被过滤、不过滤基线。
3. 必须拆出单条件贡献，避免只给整体结果。
4. 形成 evidence / record / conclusion 四件套。

## 4. 本卡回答的问题

1. 过滤器整体是否提升了胜率、R 倍数或净收益？
2. 被过滤掉的样本是否真的更差？
3. 五类条件中哪些有独立贡献，哪些只是重复过滤？

## 5. 非目标

1. 不在本卡直接迁移 `filter` 的设计文档。
2. 不在本卡实现生命周期三轴过滤。
3. 不在本卡修改 `PAS` gate 或 `position` sizing。

## 6. 证据目标

1. 五类条件频率表。
2. 三组对比表（通过过滤 / 被过滤 / 无过滤基线）。
3. 单条件贡献表与结论摘要。

## 7. 关闭条件

1. 已形成正式样本口径、对照组口径与统计口径。
2. evidence / record / conclusion 全部补齐。
3. 结论能够明确回答“filter 是否值得保留为主线准入层”。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/010-filter-adverse-condition-evaluation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/010-filter-adverse-condition-evaluation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `010-filter-adverse-condition-evaluation-conclusion-YYYYMMDD.md`
