# 002-006 七库持久化 pipeline 合并结论 / 2026-04-07

## 结论

`002`、`003`、`004`、`005`、`006` 可以正式关闭。

本轮正式结论是：

1. **七库全持久化 pipeline 已实现**：每个模块拥有独立的 `pipeline.py`，统一遵循"批量构建 + 日增量 + 断点续传"模式。
2. **统一 bootstrap 已集成**：`scripts/data/bootstrap_storage.py` 一键幂等初始化七库 schema。
3. **入口脚本完备**：每个模块有独立 CLI 入口，支持 `--start/--end`（全量）、`--date`（日增量）、`--resume`（断点续传）三种模式。
4. **position 无需独立持久化**：纯计算层，结果经 alpha/pas 落入 `research_lab.duckdb`。
5. **trade 当前为 3 表最小实现**：完整 8 表设计需要 Broker/BacktestEngine/成本模型，已标记为 P1.5 扩展路径。
6. **全部 169 测试通过**：修复了 `detector.py` 中 Timestamp vs date 类型不一致的 bug。

## 七库持久化现状总表

| 库 | Owner | 表数 | Pipeline 函数 | 入口脚本 | 状态 |
|---|---|---|---|---|---|
| `raw_market.duckdb` | data | 既有 | data 层独立 | `scripts/data/run_tdx_*` | ✅ 已有 |
| `market_base.duckdb` | data | 既有 | data 层独立 | `scripts/data/build_l2_*` | ✅ 已有 |
| `malf.duckdb` | malf | 2 | `run_malf_build()` | `build_malf_snapshot.py` | ✅ 完成 |
| `structure.duckdb` | structure | 2 | `run_structure_build()` | `build_structure_snapshot.py` | ✅ 完成 |
| `filter.duckdb` | filter | 2 | `run_filter_build()` | `build_filter_snapshot.py` | ✅ 完成 |
| `research_lab.duckdb` | alpha/pas | 6+ | `run_pas_build()` | `build_pas_signals.py` | ✅ 完成 |
| `trade_runtime.duckdb` | trade | 3 | `run_trade_build()` | `build_trade_backtest.py` | ✅ 完成 |

## 当前边界

1. 本结论覆盖 schema 定义、bootstrap 初始化、pipeline 批量构建、入口脚本、设计文档更新。
2. 本结论不覆盖全市场数据实际填充运行（需要 data 层先完成灌库）。
3. 本结论不覆盖 trade 完整 8 表实现（需要 Broker/BacktestEngine）。

## 后续入口

1. 最自然的下一步是**执行全市场数据填充验证**：从 L1→L2→L3→L4 按顺序构建，验证七库数据完整性。
2. 验证层卡（007-015）依赖七库有数据后才能启动。
3. trade P1.5 扩展（补齐 8 表）可在 system 层编排完成后启动。

## 证据与记录落点

- 证据：`evidence/002-006-persistence-pipeline-evidence-20260407.md`
- 记录：`records/002-006-persistence-pipeline-record-20260407.md`
- 结论：本文件
