# 021. PAS / position execution_context_snapshot 消费迁移 卡

**状态**: `Closed`
**类型**: `alpha-position / consumer-migration / execution-contract`
**模块**: `alpha/pas`, `position`

## 1. 定位

这张卡只解决一件事：

在 `execution_context_snapshot` 已落地后，把 `PAS / position` 的正式消费入口从 `malf_context_snapshot` 迁到 `execution_context_snapshot`，并让 `PasSignal` 合同开始携带正式生命周期字段。

## 2. 固定因素

1. 本卡不实现新的生命周期评分算法。
2. 本卡不修改 `cell_gate_check()` 的业务矩阵，只迁移其读取入口。
3. 本卡不修改 position 的 sizing 公式；position 只接入新合同字段，不据此改变仓位计算。
4. 兼容字段可暂时继续保留，但不得继续被表述为正式主字段。

## 2.1 性能与库复用前置检查

1. 本卡不新增数据库。
2. 本卡允许修改 `research_lab` 表 schema，以承接 `PasSignal` 的新正式字段。
3. 本卡只改 `alpha/pas`、`position`、相关测试与执行文档。

## 3. 输出要求

1. `PAS` 从 `execution_context_snapshot` 读取正式执行上下文。
2. `PasSignal` 合同补齐正式生命周期字段。
3. `position` 能接收这些字段，但本卡不改变 sizing 决策。
4. 补齐本卡的 evidence / record / conclusion。

## 4. 本卡回答的问题

1. 在桥表可用后，`PAS` 的正式读取源应是什么？
2. `PasSignal` 至少需要携带哪些生命周期字段，才能让 position 后续平滑升级？

## 5. 非目标

1. 不改 sizing family 公式。
2. 不改 trade 执行。
3. 不实现 active wave / 历史样本池。

## 6. 证据目标

1. `alpha/pas` 读取桥表的实现证据。
2. `PasSignal` 合同升级证据。
3. 相关测试通过证据。

## 7. 关闭条件

1. `PAS` 已从 `execution_context_snapshot` 读取正式字段。
2. `PasSignal` 已携带正式生命周期字段并通过测试。
3. 本卡四件套与 README 索引已补齐。
