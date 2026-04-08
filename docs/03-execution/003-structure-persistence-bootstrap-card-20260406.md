# 003. structure 持久化 pipeline bootstrap 卡

**状态**: `superseded`
**类型**: `structure / persistence / bootstrap`
**模块**: `structure`
**替代闭环**: `002-006-persistence-pipeline-conclusion-20260407.md`

## 1. 定位

这张卡当前保留的意义只有一件事：

把 `structure` 在七库全持久化架构中的单模块范围、输入输出边界与 runner 命名重新写清楚，作为 `002-006` 合并闭环的单卡追溯页。

## 2. 固定因素

1. 当前 authoritative 关闭结论以 `002-006-persistence-pipeline-conclusion-20260407.md` 为准。
2. `structure` 的正式落库目标是 `structure.duckdb`，Owner 仍是 `structure` 模块。
3. 当前单卡只覆盖 schema / bootstrap / batch runner / checkpoint-resume 的边界说明，不重新声明旧版依赖编号。
4. 单卡文本不得继续使用旧 `bootstrap_structure.py` 口径；当前实现入口以 `build_structure_snapshot.py` 与 `run_structure_build()` 为准。

## 3. 输出要求

1. `structure.duckdb` 的最小持久化表族、幂等 bootstrap 方式、批量构建入口必须写清楚。
2. 必须明确 `structure` 的输入来自正式市场底座，而不是临时 CSV 或研究态缓存。
3. 必须明确 checkpoint / resume / selective rebuild 的边界，不允许把 `structure` 写成全量一次性脚本。
4. 单卡文本必须与 `002-006` 合并闭环、当前仓库脚本名、当前模块职责保持一致。

## 4. 本卡回答的问题

1. `structure` 持久化层在当前系统里的最小落地范围是什么？
2. 单模块 runner、schema、断点续跑责任如何表达，才能和 `002-006` 合并闭环不冲突？

## 5. 非目标

1. 不在本卡重新进行 `structure × BOF` 联合验证。
2. 不在本卡声明新的结构位阈值研究结论。
3. 不在本卡推翻 `002-006` 已关闭的合并持久化结论。

## 6. 证据目标

1. 保留单模块范围说明，供后续追溯 `structure` 持久化边界。
2. 若后续再次复核实现，应引用 `002-006` 合并证据，而不是回到旧依赖编号。

## 7. 当前处理结论

1. 本文件已从旧脚本名、旧依赖编号、旧一次性 bootstrap 描述纠偏为当前系统可读版本。
2. `003` 不再是独立 authoritative 闭环来源；正式关闭地位由 `002-006` 合并结论承接。
