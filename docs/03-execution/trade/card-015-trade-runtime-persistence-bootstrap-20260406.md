# CARD-015 trade_runtime 持久化 bootstrap / 2026-04-06

## 目标

为 trade 模块建立全持久化 bootstrap 基础设施，实现：
1. `trade_runtime.duckdb` schema 冻结（交易记录 + 权益曲线表）
2. 从 `research_lab.duckdb`（PositionPlan）+ `market_base`（后续 K 线）读取 → TradeManager 模拟 → 写入 `trade_runtime.duckdb`
3. 按信号批次处理，`config_hash` 跳过已有数据，checkpoint 断点续传

## 前置条件

- [ ] card-014 完成：`research_lab.duckdb` 已填充（`position_plan` 可读）
- [ ] card-001 完成：`market_base` 已填充（后续 K 线可读）
- [ ] `src/lq/trade/management.py`（TradeManager 5 阶段状态机）可调用
- [ ] `src/lq/core/config_hash.py` 已建（card-011 产出）
- [ ] `H:\Lifespan-Quant-data\trade\` 目录已创建

## 执行步骤

### P0 — schema 冻结

1. 新建 `src/lq/trade/bootstrap.py`：
   - `create_schema(conn)` — 建表：
     - `trade_record`：`(trade_id, signal_id, code, entry_date, exit_date, config_hash, entry_price, exit_price, initial_stop_price, peak_price, r_multiple, pnl, exit_reason, lifecycle_state, created_at)`
     - `equity_curve`：`(run_id, config_hash, date, equity, drawdown, trade_count, created_at)`
     - `batch_run_meta`：`(run_id, config_hash, start_date, end_date, patterns, capital_base, created_at)` — 批次元信息
   - 主键：`trade_record(trade_id, config_hash)`
   - 索引：`trade_record(code, entry_date)`、`trade_record(config_hash, exit_reason)`

### P1 — config_hash 参数域定义

2. 确定 `config_hash` 覆盖的参数集：
   - 退出管理参数（`trail_stop_atr_mult`、`time_stop_bars`、`profit_target_r`）
   - 资金合同参数（与 card-014 中的 `position_plan` config_hash 对应）
   - `capital_base`（初始资金，影响复利模式下的仓位大小）
   - 以上任意变更 → 新 `config_hash` → selective rebuild

### P2 — bootstrap runner

3. 新建 `scripts/trade/bootstrap_trade_runtime.py`：
   - 参数：`--data-root`、`--start-date`、`--end-date`、`--batch-size`（默认 200 个信号/批）、`--dry-run`
   - 流程：
     ```
     run_id = generate_run_id(config_hash, start_date, end_date)
     plans = load_position_plans(research_lab, start_date, end_date)
     for plan_batch in batches(plans, size=batch_size):
         not_done = [p for p in plan_batch
                     if not is_done(conn, 'trade_record', p.signal_id, config_hash)]
         if not not_done:
             continue
         for plan in not_done:
             future_bars = load_market_base(plan.code, plan.entry_date, +250)
             manager = TradeManager(plan, trade_config)
             record = manager.simulate(future_bars)
             write_trade_record(conn, record, run_id, config_hash)
         update_checkpoint(plan_batch)
         del future_bars, record
     write_equity_curve(conn, run_id, config_hash)
     ```

### P3 — 验证

4. 抽样验证：
   - 随机抽取 20 条 `trade_record`，对照 `position_plan` + 日线图，确认入场/出场价、R 倍数计算正确
   - `r_multiple` 分布（均值 > 0 为基本合格；与 v0.01 同期 BOF 数据对比量级一致）
   - `exit_reason` 分布合理（time_stop / trail_stop / profit_target 均有出现）
   - 中断重跑：第二次运行写入行数 = 0

## 验收标准

1. `bootstrap_trade_runtime.py --dry-run` 正确打印计划（信号总数 + 批次数）
2. 全历史灌入完成，`trade_record` 行数 = `position_plan` 行数
3. 中断重跑正常恢复，无重复写入
4. `r_multiple` 均值与 v0.01 同期 BOF 对比误差 < 5%（验证 TradeManager 逻辑正确）

## 产出物

- `src/lq/trade/bootstrap.py`（新建）
- `scripts/trade/bootstrap_trade_runtime.py`（新建）
- evidence + record + conclusion（执行后补）
