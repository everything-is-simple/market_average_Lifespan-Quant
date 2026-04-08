# 017. MALF 兼容桥接与 PAS 准入修正 卡

**状态**: `Closed`
**类型**: `malf / compatibility-bridge / pas-fix`
**模块**: `malf`

## 1. 定位

这张卡只解决一件事：

在 `016` 已冻结 design/spec/execution 合同之后，把当前实现层里最危险的兼容断裂先修平，避免 `PAS` 继续因为旧字段桥接错位而跑偏或静默失效。

## 2. 固定因素

1. `016` 已冻结正式主轴：`四格上下文 + 生命周期三轴原始排位 + 四分位辅助`。
2. 本卡不实现生命周期三轴排位，不新增 `execution_context_snapshot` 真落表。
3. 本卡允许继续保留 `monthly_state` / `weekly_flow` 作为兼容字段，但不得把它们重新抬升为正式主轴。
4. 本卡只修当前实现层的兼容桥接、参数对齐与落库透传，不重写业务治理结论。

## 2.1 性能与库复用前置检查

1. 本卡不新增正式全市场重跑。
2. 本卡不新增新的 DuckDB 表。
3. 本卡只在现有 `malf_context_snapshot` / `pas_formal_signal` / system explain chain 范围内修补接口。
4. 不新增批量 flush / checkpoint 机制。

## 3. 输出要求

本卡要求正式新增或正式变更：

1. 修正 `alpha/pas` 中 `cell_gate_check()` 的实际调用与参数来源，使其与当前定义一致。
2. 让 `PAS` 在读取 MALF 上下文时同时拿到 `malf_context_4` 与兼容字段 `monthly_state` / `weekly_flow`，并按真实上下文落入 `pas_formal_signal`。
3. 盘清 `filter / system` 对旧字段的消费位置，决定哪些保留兼容、哪些只做记录，不让它们冒充正式主轴。
4. 补齐本卡的 `evidence / record / conclusion`。

## 4. 本卡回答的问题

1. 当前实现层里，哪些地方只是“旧字段兼容存在”，哪些地方已经变成“接口调用错位或运行逻辑错误”？
2. 在不提前实现生命周期排位的前提下，怎样把 `MALF → PAS` 的桥接先修到可用且不违背 `016`？

## 5. 非目标

1. 不在本卡直接实现 `amplitude / duration / new_price` 三轴排位计算。
2. 不在本卡直接改写 `position` 的生命周期 sizing 公式。
3. 不在本卡直接把 `system / filter` 全量迁移到 `execution_context_snapshot`。

## 6. 证据目标

本卡至少要留下：

1. `PAS` 调用修正与兼容字段透传的代码修改证据。
2. 至少一组可复述的测试或编译证据。
3. 对 `system / filter / position` 当前影响边界的执行记录。

## 7. 关闭条件

1. `PAS` 不再以错误参数调用 `cell_gate_check()`。
2. `pas_formal_signal` 能写入与信号同日对应的 `monthly_state` / `weekly_flow` 兼容字段。
3. `record / evidence / conclusion` 已说明本轮修了什么、没修什么、下一步该去哪。
4. `docs/03-execution/README.md` 已回填本卡索引。
