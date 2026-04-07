# 002-006 七库持久化 pipeline 合并执行记录 / 2026-04-07

## 覆盖卡

002（malf）、003（structure）、004（filter）、005（research_lab/alpha/pas）、006（trade_runtime）

## 执行时间线

### 阶段 1：malf pipeline 重写（2026-04-06）

- 重写 `malf/pipeline.py`，从旧的单次全量计算改为分批构建 + 断点续传 + 日增量模式
- 实现 `run_malf_build()` 按日期逐日处理，每日内按 `batch_size` 分批
- 提交：`aecde46 feat(malf): 重写 pipeline 支持分批构建+断点续传+日增量更新`

### 阶段 2：structure + filter pipeline（2026-04-07 上午）

- 新增 `structure/pipeline.py`：schema（`structure_snapshot` + `structure_build_manifest`）、`bootstrap_structure_storage()`、`run_structure_build()`
- 新增 `filter/pipeline.py`：schema（`filter_snapshot` + `filter_build_manifest`）、`bootstrap_filter_storage()`、`run_filter_build()`
- 新增入口脚本 `scripts/structure/build_structure_snapshot.py` 和 `scripts/filter/build_filter_snapshot.py`
- 集成到 `bootstrap_storage.py`
- 端到端验证通过

### 阶段 3：alpha/pas + trade pipeline（2026-04-07 下午）

- 调研现有代码：alpha/pas 已有 `bootstrap.py`（schema）和 `pipeline.py`（单日逻辑），但缺少多日期批量封装
- alpha/pas：新增 `run_pas_build()` 多日期批量包装 + 断点续传，复用 `run_pas_batch()` 单日逻辑
- 新增入口脚本 `scripts/alpha/build_pas_signals.py`
- trade：新增 `pipeline.py`（schema 3 表 + `bootstrap_trade_storage()` + `run_trade_build()`）
- 新增入口脚本 `scripts/trade/build_trade_backtest.py`
- 集成 trade bootstrap 到 `bootstrap_storage.py`
- position 模块确认为纯计算层，无独立持久化需求

### 阶段 4：设计文档更新（2026-04-07 下午）

- 更新 7 份设计文档，新增持久化 pipeline 章节
- 在 system 编排设计中新增七库总览和全链路构建顺序

### 阶段 5：bugfix + 闭环（2026-04-07 下午）

- 修复 `detector.py` 中 `classify_breakout_event` 的 date 列类型不一致问题
- 全量测试 169 passed, 0 failed
- 补齐执行四件套

## 遇到的问题

### P1：列名不匹配

`market_base` 存的是 `open/high/low/close`，而 `detector` 和 `filter` 期望 `adj_high/adj_low/adj_close`。
**解决**：在 pipeline 层读取数据后做列名映射（rename）。

### P2：Timestamp vs date 类型不匹配

DuckDB 返回 `datetime64[us]`，测试传入 `datetime.date`，pandas 不能直接比较。
**解决**：在 `classify_breakout_event` 中用 `pd.to_datetime()` 统一 date 列类型。

### P3：trade schema 设计取舍

原设计 8 张表（`02-trade-runtime-schema-design`），当前实现只需 3 张表（`trade_record` + `trade_run_summary` + `trade_build_manifest`）即可支撑最小可运行回测。
**决策**：先实现 3 表，Broker/BacktestEngine/成本模型完成后再扩展到 8 表（标记为 P1.5）。

## 未完成项

1. **trade 8 表完整实现**：需要 Broker 类 + BacktestEngine + 成本模型（P1.5 扩展路径）
2. **全市场实际数据验证**：当前只验证了导入和单测，未做全市场数据填充
3. **config_hash 跳过机制**：pipeline 框架已支持，但 alpha/pas 和 trade 的 config_hash 参数域尚未精确定义
