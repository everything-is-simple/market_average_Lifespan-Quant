# 019. filter A4-5 背景合同收敛 卡

**状态**: `Closed`
**类型**: `filter / design-reset / background-contract`
**模块**: `filter`

## 1. 定位

这张卡只解决一件事：

把 `filter` 模块 A4-5（背景不支持）从当前文档与实现里对 `monthly_state / weekly_flow` 的直接主轴依赖，收敛到以正式 MALF 上下文字段为主、旧字段只作为兼容细粒度补充的口径。

## 2. 固定因素

1. `016` 已冻结正式 MALF 主轴：`long_background_2 + intermediate_role_2 + malf_context_4 + 生命周期三轴排位`。
2. `017` 已修复 `PAS` 的兼容桥接；`018` 已把 `system` 解释链收敛到正式 MALF 摘要。
3. 本卡只处理 `filter` 的 A4-5，不改 A4-1 / A4-2 / A4-3 / A4-4。
4. 本卡允许在实现层继续读取 `monthly_state / weekly_flow` 作为兼容细粒度字段，但不得再把它们表述为 filter 的正式主轴。

## 2.1 性能与库复用前置检查

1. 本卡不新增数据库表。
2. 本卡不新增全市场重跑。
3. 本卡只涉及 `filter` design / execution / 相关实现与测试。

## 3. 输出要求

1. 修订 `filter` 设计文档中 A4-5 的正式表述，明确 `long_background_2 / intermediate_role_2 / malf_context_4` 是正式摘要，`monthly_state / weekly_flow` 仅为兼容细粒度来源。
2. 若实现迁移发生，必须保持当前保守过滤语义不放松。
3. 补齐本卡的 evidence / record / conclusion。

## 4. 本卡回答的问题

1. A4-5 的正式背景过滤，到底依赖哪些 MALF 字段？
2. 在不丢失 BEAR_FORMING / BEAR_PERSISTING 细粒度差异的前提下，如何让 filter 的文档和实现不再继续把旧字段当正式主轴？

## 5. 非目标

1. 不实现生命周期三轴过滤。
2. 不改 PAS gate 逻辑。
3. 不改 position sizing。

## 6. 证据目标

1. `filter` 设计/实现修改证据。
2. 至少一组 A4-5 相关测试证据。
3. 对“为什么本卡仍保留旧字段兼容读取”的边界说明。

## 7. 关闭条件

1. `filter` 的 A4-5 设计口径已与 016 保持一致。
2. 若实现发生修改，则测试已通过。
3. 本卡四件套与 README 索引已补齐。
