# 018. system 解释链 MALF 摘要收敛 卡

**状态**: `Closed`
**类型**: `system / compatibility-cleanup / trace-contract`
**模块**: `system`

## 1. 定位

这张卡只解决一件事：

把 `system` 层解释链 `StockScanTrace` 中的 MALF 摘要从“以 `monthly_state` 为主”收敛到“以正式执行字段为主、旧字段仅作兼容补充”。

## 2. 固定因素

1. `016` 已冻结正式 MALF 主轴：`long_background_2 + intermediate_role_2 + malf_context_4 + 生命周期三轴排位`。
2. `017` 已修复 `MALF → PAS` 的兼容桥接问题。
3. 本卡不改 `filter` 的 A4-5 行为，因为当前 `filter` 设计文档仍明确依赖 `monthly_state / weekly_flow`。
4. 本卡不实现生命周期三轴，也不新增数据库表。

## 2.1 性能与库复用前置检查

1. 本卡不新增全市场重跑。
2. 本卡不改 DuckDB schema。
3. 本卡只改 `system/orchestration.py` 及其测试，属于解释链合同收敛。

## 3. 输出要求

1. `StockScanTrace` 应显式携带 `long_background_2` 与 `intermediate_role_2`。
2. `monthly_state` 若继续保留，必须降级为兼容摘要字段，不能再代表 system 层正式主轴。
3. 对应补丁测试要覆盖新字段输出。
4. 补齐本卡的 evidence / record / conclusion。

## 4. 本卡回答的问题

1. system 解释链中，哪些 MALF 字段才应被视为正式摘要？
2. 如何在不破坏现有 replay/复盘能力的前提下，把旧字段降级为兼容补充？

## 5. 非目标

1. 不改 filter A4-5 过滤逻辑。
2. 不改 PAS/position 生命周期合同。
3. 不改 trade/system 的回测主逻辑。

## 6. 证据目标

1. `system/orchestration.py` 的解释链合同修改证据。
2. 至少一组相关测试通过证据。
3. 对 `filter` 为何未在本卡迁移的边界说明。

## 7. 关闭条件

1. `StockScanTrace` 已输出 `long_background_2` 与 `intermediate_role_2`。
2. 现有测试已更新并通过。
3. 本卡四件套与 README 索引已补齐。
