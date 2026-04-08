# 005. research_lab 持久化 pipeline bootstrap 卡

**状态**: `superseded`
**类型**: `alpha-position / persistence / bootstrap`
**模块**: `alpha/pas`, `position`
**替代闭环**: `002-006-persistence-pipeline-conclusion-20260407.md`

## 1. 定位

这张卡当前保留的意义只有一件事：

把 `research_lab.duckdb` 在当前系统中的单模块范围重新写清楚，明确它服务于 `alpha/pas + position` 的正式落库，而不是旧版一次性研究库脚本。

## 2. 固定因素

1. 当前 authoritative 关闭结论以 `002-006-persistence-pipeline-conclusion-20260407.md` 为准。
2. `research_lab.duckdb` 是 `alpha/pas + position` 的正式持久化库，Owner 不是 `trade`。
3. `position` 当前没有独立数据库；其结果合同由 `research_lab` 承接。
4. 单卡文本不得继续使用旧 `bootstrap_research_lab.py` 口径；当前实现入口以 `build_pas_signals.py` 与 `run_pas_build()` 为准。
5. `021` 之后，`PasSignal` 已开始承载 `execution_context_snapshot` 的正式字段；旧字段只能写成兼容来源。

## 3. 输出要求

1. `research_lab` 的正式表族、幂等 bootstrap、批量构建入口必须与现仓库实现一致。
2. 必须明确 `pas_formal_signal` 是正式信号承载表，而不是研究态临时表。
3. 必须明确 `position` 在当前阶段只接入生命周期字段，不在本卡声明 sizing 公式升级。
4. 单卡文本不得继续把 `surface_label`、旧 `monthly_state` 主轴写成 research_lab 的正式合同中心。

## 4. 本卡回答的问题

1. `research_lab` 在当前系统里到底承接哪些正式输出合同？
2. `alpha/pas` 与 `position` 的持久化边界如何写，才能与 `021` 和当前代码一致？

## 5. 非目标

1. 不在本卡声明 trigger 有效性研究结论。
2. 不在本卡声明新的 sizing family 结论。
3. 不在本卡单独关闭 `021` 之后的生命周期消费迁移问题。

## 6. 证据目标

1. 保留 `research_lab` 单模块范围说明，供后续追溯。
2. 若再次复核实现，应优先引用 `002-006` 合并闭环与 `021` 的 consumer migration 结论。

## 7. 当前处理结论

1. 本文件已从旧脚本名、旧字段中心、旧依赖编号纠偏为当前系统可读版本。
2. `005` 不再承担独立 authoritative 关闭职责；正式关闭地位由 `002-006` 合并结论承接。
