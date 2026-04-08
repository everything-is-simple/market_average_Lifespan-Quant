# 004. filter 持久化 pipeline bootstrap 卡

**状态**: `superseded`
**类型**: `filter / persistence / bootstrap`
**模块**: `filter`
**替代闭环**: `002-006-persistence-pipeline-conclusion-20260407.md`

## 1. 定位

这张卡当前保留的意义只有一件事：

把 `filter` 持久化层在七库架构中的单模块范围、输入输出合同与 batch runner 边界重新收口，作为 `002-006` 合并闭环的单卡追溯页。

## 2. 固定因素

1. 当前 authoritative 关闭结论以 `002-006-persistence-pipeline-conclusion-20260407.md` 为准。
2. `filter` 的正式落库目标是 `filter.duckdb`，Owner 仍是 `filter` 模块。
3. `filter` 读取的是正式市场底座与正式上游结果合同，不允许回退到研究态手工样本脚本。
4. 单卡文本不得继续使用旧 `bootstrap_filter.py` 口径；当前实现入口以 `build_filter_snapshot.py` 与 `run_filter_build()` 为准。

## 3. 输出要求

1. `filter.duckdb` 的表族、幂等 bootstrap、批量 runner、resume 语义必须与现仓库实现一致。
2. 必须明确 `filter` 是正式准入层，不是一次性统计脚本。
3. 必须明确 `filter` 的持久化结果服务于下游 `alpha/pas`，而不是反向驱动 `malf / structure`。
4. 单卡文本必须与 `019` 之后的背景合同收敛口径兼容，不继续把旧字段写成 filter 正式主轴。

## 4. 本卡回答的问题

1. `filter` 持久化层在当前系统中的最小持久化责任是什么？
2. 怎样表达 `filter` 的 runner 边界，才能与合并持久化结论和后续验证卡一致？

## 5. 非目标

1. 不在本卡声明五类 adverse condition 的效果结论。
2. 不在本卡直接重写 `019` 已关闭的背景合同纠偏。
3. 不在本卡新增生命周期三轴过滤。

## 6. 证据目标

1. 保留 `filter` 持久化层的单模块追溯页。
2. 若后续再次复核实现，应以 `002-006` 合并证据和当前代码为主，不再引用旧依赖编号。

## 7. 当前处理结论

1. 本文件已从旧依赖图、旧 runner 命名、旧一次性脚本描述纠偏为当前系统可读版本。
2. `004` 不再承担独立 authoritative 关闭职责；正式关闭地位由 `002-006` 合并结论承接。
