# 020. MALF execution_context_snapshot bootstrap 卡

**状态**: `Closed`
**类型**: `malf / bridge-table / bootstrap`
**模块**: `malf`

## 1. 定位

这张卡只解决一件事：

把 `execution_context_snapshot` 从 design/spec 中的“已定义未实现”状态推进到“桥表已存在、可由现有 `malf_context_snapshot` 物化第一版”的状态。

## 2. 固定因素

1. 本卡不实现历史 active wave 样本池与真实三轴排名算法。
2. 本卡允许先把 `execution_context_snapshot` 做成 `malf_context_snapshot` 的执行桥镜像表。
3. 本卡只保证正式字段、桥表 schema、基础落盘链路存在；不要求下游本轮立刻全量切换消费者。
4. 对当前无法计算的字段，必须显式落 `NULL` 或稳定占位，不得伪造业务含义。

## 2.1 性能与库复用前置检查

1. 本卡不新增全市场重跑任务。
2. 本卡只改 `malf` schema / writer / 测试 / 执行文档。
3. 不引入额外数据库。

## 3. 输出要求

1. `malf.duckdb` 中新增 `execution_context_snapshot`。
2. 现有 MALF snapshot 写入完成后，能同步写入 bridge table。
3. 桥表至少包含 spec 中定义的正式最小列；暂不可算字段显式为 `NULL` 或稳定值。
4. 补齐本卡的 evidence / record / conclusion。

## 4. 本卡回答的问题

1. 在三轴真实评分未落地前，`execution_context_snapshot` 最小可用形态是什么？
2. 桥表与 `malf_context_snapshot` 的关系应如何定义，才能让后续 PAS / position 平滑切换？

## 5. 非目标

1. 不实现 active wave 识别算法。
2. 不实现 historical sample pool ranking。
3. 不在本卡直接把 PAS / position 改成强依赖桥表。

## 6. 证据目标

1. `malf` schema / 写入链路修改证据。
2. 至少一组 bridge table 落盘测试证据。
3. 对暂未实现字段如何占位的说明。

## 7. 关闭条件

1. `execution_context_snapshot` 已建表并能落第一版镜像数据。
2. 相关测试已通过。
3. 本卡四件套与 README 索引已补齐。
