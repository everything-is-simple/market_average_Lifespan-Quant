# CARD-014 research_lab 持久化 bootstrap（alpha/pas + position）/ 2026-04-06

## 目标

为 alpha/pas + position 模块建立全持久化 bootstrap 基础设施，实现：
1. `research_lab.duckdb` schema 冻结（PAS 信号表 + 仓位计划表）
2. 从 `filter.duckdb`（tradeable=True）+ `structure.duckdb` + `market_base` 读取 → trigger 探测 + 仓位规划 → 写入 `research_lab.duckdb`
3. 按股票批次处理，`config_hash` 跳过已有数据，checkpoint 断点续传

## 前置条件

- [ ] card-013 完成：`filter.duckdb` 已填充（`adverse_condition_result.tradeable` 可读）
- [ ] card-012 完成：`structure.duckdb` 已填充（`StructureSnapshot` 可重建）
- [ ] card-001 完成：`market_base` 已填充
- [ ] `src/lq/alpha/pas/detectors.py` 可调用（BOF/TST/PB 三个 MAINLINE/CONDITIONAL trigger）
- [ ] `src/lq/alpha/pas/pipeline.py` 可调用
- [ ] `src/lq/core/config_hash.py` 已建（card-011 产出）
- [ ] `H:\Lifespan-Quant-data\research\` 目录已创建

## 执行步骤

### P0 — schema 冻结

1. 新建 `src/lq/alpha/pas/db_bootstrap.py`：
   - `create_schema(conn)` — 建表：
     - `pas_signal`：`(signal_id, code, signal_date, config_hash, pattern, surface_label, strength, signal_low, entry_ref_price, pb_sequence_number, created_at)`
     - `position_plan`：`(signal_id, code, signal_date, entry_date, config_hash, signal_pattern, signal_low, entry_price, initial_stop_price, first_target_price, risk_unit, lot_count, notional, created_at)`
   - 主键：`pas_signal(signal_id, config_hash)`；`position_plan(signal_id, config_hash)`
   - 索引：`pas_signal(code, signal_date)`、`pas_signal(pattern, surface_label)`

### P1 — config_hash 参数域定义

2. 确定 `config_hash` 覆盖的参数集：
   - trigger 启用列表（`enabled_patterns: list[str]`）
   - 每个 trigger 的阈值参数（如 BOF 的 `min_false_break_pct`）
   - 资金合同参数（`capital_base`, `fixed_notional`）
   - 更改任意一个 → 新 `config_hash` → 新行写入，旧行保留

### P2 — bootstrap runner

3. 新建 `scripts/alpha/bootstrap_research_lab.py`：
   - 参数：`--data-root`、`--start-date`、`--end-date`、`--patterns`（默认 BOF,TST,PB）、`--batch-size`（默认 50 只/批）、`--dry-run`
   - 流程：
     ```
     tradeable_index = load_tradeable_codes_by_date(filter_db)
     for date in trading_dates(start, end):
         codes_today = tradeable_index[date]
         for code_batch in batches(codes_today, size=batch_size):
             if all already_done(code_batch, date, config_hash):
                 continue
             bars = load_market_base(code_batch, window_bars)
             snapshots = load_structure_snapshots(code_batch, date)
             malf_ctxs = load_malf_contexts(code_batch, date)
             signals = detect_signals(bars, snapshots, malf_ctxs, enabled_patterns)
             plans = plan_positions(signals, capital_config)
             write_signals_and_plans(conn, signals, plans, config_hash)
         update_checkpoint(date)
         del bars, snapshots, malf_ctxs, signals, plans
     ```

### P3 — 验证

4. 抽样验证：
   - 随机抽取 2020-2023 年 BOF 信号，对照日线图确认信号形态合理
   - `surface_label` 分布符合预期（BULL_MAINSTREAM 占比与 v0.01 对比）
   - `risk_unit`（1R）值域合理（通常为入场价的 1~5%）
   - 中断重跑：第二次运行写入行数 = 0

## 验收标准

1. `bootstrap_research_lab.py --dry-run` 正确打印计划（可交易日×批次数）
2. 全历史灌入完成，`pas_signal` + `position_plan` 行数一致
3. 中断重跑正常恢复
4. BOF 信号数量与 v0.01 `research_lab.duckdb` 同期数量量级一致（±20%）

## 产出物

- `src/lq/alpha/pas/db_bootstrap.py`（新建）
- `scripts/alpha/bootstrap_research_lab.py`（新建）
- evidence + record + conclusion（执行后补）
