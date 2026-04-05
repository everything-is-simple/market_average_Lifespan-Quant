# CARD-011 malf 六层流水线持久化 bootstrap / 2026-04-06

## 目标

为 malf 模块建立全持久化 bootstrap 基础设施，实现：
1. `malf.duckdb` schema 冻结（六层输出表结构）
2. 从 `market_base` 读取 → 六层流水线计算 → 写入 `malf.duckdb`
3. 按月份批次处理，`config_hash` 跳过已有数据，checkpoint 断点续传
4. 全市场一遍抽样验证（与 v0.01 malf 输出对比）

## 前置条件

- [ ] card-001 完成：`raw_market` + `market_base` 已填充
- [ ] `src/lq/malf/pipeline.py` 六层流水线可调用（`monthly.py` / `weekly.py` / `daily.py` 已有）
- [ ] `H:\Lifespan-Quant-data\malf\` 目录已创建

## 执行步骤

### P0 — schema 冻结

1. 新建 `src/lq/malf/bootstrap.py`：
   - `create_schema(conn)` — 建六层输出表（继承 v0.01 的 22 张表设计，核心：`monthly_state`、`weekly_flow`、`malf_context`）
   - 每表必须包含 `(code, period_end_date, config_hash, created_at)` 字段

2. 确认 v0.01 `malf.duckdb` 22 张表结构（参考 `G:\MarketLifespan-Quant\src\mlq\malf\`），选取 v0.1 必需的核心表子集

### P1 — config_hash 工具

3. 在 `src/lq/core/` 新建或复用 `config_hash.py`：
   - `make_config_hash(params: dict) -> str` — SHA256 前 16 位
   - `is_done(conn, table, code, date, config_hash) -> bool` — 单行跳过检查

### P2 — bootstrap runner

4. 新建 `scripts/malf/bootstrap_malf.py`：
   - 参数：`--data-root`、`--start-month`、`--end-month`、`--batch-size`（默认 3 个月）、`--dry-run`
   - 流程：
     ```
     for month_batch in month_batches:
         codes = load_all_codes(market_base)
         for code_batch in code_batches(codes, size=200):
             data = load_market_base(code_batch, month_batch)
             result = pipeline.run_six_layers(data)
             write_to_malf_db(result, config_hash)
             update_checkpoint(month_batch, code_batch)
             del data, result
     ```
   - 中断后从 `checkpoint.json` 恢复，跳过已完成月份+股票批次

### P3 — 验证

5. 抽样 10 只股票 × 最近 3 年：
   - `monthly_state` 序列与 v0.01 `malf.duckdb` 同标的同期对比一致
   - `weekly_flow` 顺逆关系与 v0.01 一致
   - `malf_context.surface_label` 16 格坐标与 v0.01 一致

## 验收标准

1. `bootstrap_malf.py --dry-run` 正确打印计划（批次数、股票数）
2. 全市场灌入完成，无报错，checkpoint 正常标记
3. 中断重跑：第二次运行 < 10 秒（全部 config_hash 命中跳过）
4. 抽样 10 只股票月线状态序列与 v0.01 一致

## 产出物

- `src/lq/malf/bootstrap.py`（新建）
- `src/lq/core/config_hash.py`（新建，供后续各卡复用）
- `scripts/malf/bootstrap_malf.py`（新建）
- evidence + record + conclusion（执行后补）
