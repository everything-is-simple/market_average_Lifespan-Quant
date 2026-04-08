# 006. trade_runtime 持久化 pipeline bootstrap 卡

**状态**: `superseded`
**类型**: `trade / persistence / bootstrap`
**模块**: `trade`, `system`
**替代闭环**: `002-006-persistence-pipeline-conclusion-20260407.md`

## 1. 定位

这张卡当前保留的意义只有一件事：

把 `trade_runtime.duckdb` 在当前系统中的最小实现范围重新写清楚，作为 `002-006` 合并闭环的单卡追溯页。

## 2. 固定因素

1. 当前 authoritative 关闭结论以 `002-006-persistence-pipeline-conclusion-20260407.md` 为准。
2. 当前 `trade_runtime` 是最小可运行实现，不是最终 8 表完整版。
3. `trade_runtime` 的上游正式输入来自 `research_lab` 与正式市场底座。
4. 单卡文本不得继续使用旧 `bootstrap_trade_runtime.py` 口径；当前实现入口以 `build_trade_backtest.py` 与 `run_trade_build()` 为准。
5. 当前最小实现应与 `TradeManager` 路径一致，不得把尚未实现的 Broker / BacktestEngine 扩展写成既成事实。

## 3. 输出要求

1. `trade_runtime.duckdb` 的最小表族、幂等 bootstrap、批量 runner、equity curve 写法必须与现仓库实现一致。
2. 必须明确当前 trade 是最小持久化实现，完整 8 表属于后续扩展，而不是本卡已完成内容。
3. 必须明确 `trade` 不拥有 `research_lab` 的写权。
4. 单卡文本必须与 `002-006` 合并闭环的 trade 边界一致。

## 4. 本卡回答的问题

1. 当前 `trade_runtime` 最小可用实现到底包括什么，不包括什么？
2. 怎样在保留单模块说明的同时，不再让旧版脚本名和旧实现想象误导后续工作？

## 5. 非目标

1. 不在本卡补齐 trade 完整 8 表实现。
2. 不在本卡引入 Broker / BacktestEngine / 成本模型。
3. 不在本卡声明回测表现结论。

## 6. 证据目标

1. 保留 `trade_runtime` 单模块范围追溯页。
2. 若后续继续扩展 trade，应以当前代码与 `002-006` 合并闭环为起点，而不是回到旧脚本假设。

## 7. 当前处理结论

1. 本文件已从旧脚本名、旧 8 表完成假设、旧依赖编号纠偏为当前系统可读版本。
2. `006` 不再承担独立 authoritative 关闭职责；正式关闭地位由 `002-006` 合并结论承接。
