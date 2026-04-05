# CARD-012 structure 持久化层 bootstrap / 2026-04-06

## 目标

为 structure 模块建立全持久化 bootstrap 基础设施，实现：
1. `structure.duckdb` schema 冻结（结构位快照 + 突破事件表）
2. 从 `market_base` 读取 → `detector.py` 计算 → 写入 `structure.duckdb`
3. 按股票批次处理，`config_hash` 跳过已有数据，checkpoint 断点续传

## 前置条件

- [ ] card-001 完成：`market_base` 已填充（`stock_daily_adjusted` 可读）
- [ ] `src/lq/structure/detector.py` 可调用（`detect_structure_levels` 函数）
- [ ] `src/lq/core/config_hash.py` 已建（card-011 产出）
- [ ] `H:\Lifespan-Quant-data\structure\` 目录已创建

## 执行步骤

### P0 — schema 冻结

1. 新建 `src/lq/structure/bootstrap.py`：
   - `create_schema(conn)` — 建以下表：
     - `structure_level`：`(code, signal_date, config_hash, level_type, price, formed_date, strength, touch_count, is_tested, created_at)`
     - `breakout_event`：`(code, signal_date, config_hash, event_date, level_price, breakout_type, penetration_pct, recovered, confirmed, created_at)`
     - `structure_snapshot_meta`：`(code, signal_date, config_hash, has_clear_structure, available_space_pct, created_at)` — 快照汇总行，供 filter 快速查
   - 主键：`(code, signal_date, config_hash)`

### P1 — bootstrap runner

2. 新建 `scripts/structure/bootstrap_structure.py`：
   - 参数：`--data-root`、`--start-date`、`--end-date`、`--batch-size`（默认 100 只/批）、`--dry-run`
   - 流程：
     ```
     for code_batch in code_batches(all_codes, size=batch_size):
         for date in trading_dates(start, end):
             if is_done(conn, 'structure_snapshot_meta', code, date, config_hash):
                 continue
             bars = load_market_base(code, window_before_date)
             snapshot = detect_structure_levels(code, date, bars)
             write_snapshot(conn, snapshot, config_hash)
         update_checkpoint(code_batch)
         del bars, snapshot
     ```
   - checkpoint 粒度：每完成一个 code_batch 写入一次 `checkpoint.json`

### P2 — 验证

3. 抽样 5 只股票 × 最近 1 年：
   - `structure_snapshot_meta.has_clear_structure` 比率合理（预期 60~85%）
   - 随机抽查 10 个日期的结构位价格，人工对照日线图确认支撑/阻力位合理
   - 重跑验证：第二次运行 < 30 秒（全部 config_hash 命中跳过）

## 验收标准

1. `bootstrap_structure.py --dry-run` 正确打印计划
2. 全市场全历史灌入完成，无报错
3. 中断重跑：第二次运行 config_hash 全命中，实际写入行数 = 0
4. `structure_snapshot_meta` 行数 = 股票数 × 交易日数

## 产出物

- `src/lq/structure/bootstrap.py`（新建）
- `scripts/structure/bootstrap_structure.py`（新建）
- evidence + record + conclusion（执行后补）
