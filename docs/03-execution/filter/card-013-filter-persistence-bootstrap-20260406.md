# CARD-013 filter 持久化层 bootstrap / 2026-04-06

## 目标

为 filter 模块建立全持久化 bootstrap 基础设施，实现：
1. `filter.duckdb` schema 冻结（不利条件检查结果表）
2. 从 `structure.duckdb` + `malf.duckdb` + `market_base` 读取 → `adverse.py` 计算 → 写入 `filter.duckdb`
3. 按股票批次处理，`config_hash` 跳过已有数据，checkpoint 断点续传

## 前置条件

- [ ] card-011 完成：`malf.duckdb` 已填充（`malf_context` 可读）
- [ ] card-012 完成：`structure.duckdb` 已填充（`structure_snapshot_meta` 可读）
- [ ] `src/lq/filter/adverse.py` 可调用（`check_adverse_conditions` 函数）
- [ ] `src/lq/core/config_hash.py` 已建（card-011 产出）
- [ ] `H:\Lifespan-Quant-data\filter\` 目录已创建

## 执行步骤

### P0 — schema 冻结

1. 新建 `src/lq/filter/bootstrap.py`：
   - `create_schema(conn)` — 建表：
     - `adverse_condition_result`：`(code, signal_date, config_hash, tradeable, active_conditions, notes, created_at)`
     - `active_conditions` 存 JSON 数组字符串（`AdverseConditionType` 值列表）
   - 主键：`(code, signal_date, config_hash)`
   - 索引：`(signal_date, tradeable)` — alpha 层批量读取可交易股票时用

### P1 — bootstrap runner

2. 新建 `scripts/filter/bootstrap_filter.py`：
   - 参数：`--data-root`、`--start-date`、`--end-date`、`--batch-size`（默认 100 只/批）、`--dry-run`
   - 流程：
     ```
     for code_batch in code_batches(all_codes, size=batch_size):
         for date in trading_dates(start, end):
             if is_done(conn, 'adverse_condition_result', code, date, config_hash):
                 continue
             bars = load_market_base(code, window_bars)
             malf_ctx = load_malf_context(code, date)
             snap = load_structure_snapshot(code, date)
             result = check_adverse_conditions(
                 code, date, bars, malf_ctx,
                 snap.nearest_support.price if snap else None,
                 snap.nearest_resistance.price if snap else None,
             )
             write_result(conn, result, config_hash)
         update_checkpoint(code_batch)
         del bars, malf_ctx, snap, result
     ```

### P2 — 验证

3. 抽样验证：
   - 随机抽取 100 个 `(code, date)` 组合，手动用 `check_adverse_conditions` 函数复算，结果与库中一致
   - `tradeable=True` 比率合理（预期 40~70%，过低说明参数过严）
   - 重跑验证：第二次运行 config_hash 全命中，写入行数 = 0

## 验收标准

1. `bootstrap_filter.py --dry-run` 正确打印计划
2. 全市场全历史灌入完成，无报错
3. 中断重跑正常恢复，无重复写入
4. `tradeable=True` 比率在合理区间

## 产出物

- `src/lq/filter/bootstrap.py`（新建）
- `scripts/filter/bootstrap_filter.py`（新建）
- evidence + record + conclusion（执行后补）
