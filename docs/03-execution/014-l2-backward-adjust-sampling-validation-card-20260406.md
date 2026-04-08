# 014. L2 后复权抽样验证 卡

**状态**: `pending-validation`
**类型**: `data / validation / backward-adjust`
**模块**: `data`

## 1. 定位

这张卡只解决一件事：

验证 `market_base` 中后复权价格链在当前系统里的正确性，确保正式市场底座可被后续 `malf / structure / filter / alpha` 继续信任。

## 2. 固定因素

1. 本卡只做数据质量验证，不改主线数据源路线。
2. 本卡必须对照当前系统实际使用的数据链路与字段命名，不再引用早期临时导入脚本口径。
3. 抽样必须覆盖典型权益事件与不同市场类型，不能只抽“干净样本”。
4. 如果发现后复权链错误，本卡应把问题定位到因子、事件映射或写入链路，而不是只记录“价格不一致”。

## 3. 输出要求

1. 抽样覆盖沪市 / 深市 / 北交所，以及含分红、送股、配股等权益事件的样本。
2. 对照正式外部参考，如通达信，核验后复权价连续性与事件日前后价格行为。
3. 同时核验 `adjust_factor` 因子链是否与价格链一致。
4. 形成 evidence / record / conclusion 四件套。

### 3.1 当前正式核验锚点

1. 原始事件表：`raw_market.duckdb.raw_xdxr_event`。
2. 原始日线表：`raw_market.duckdb.raw_stock_daily`。
3. 后复权结果表：`market_base.duckdb.stock_daily_adjusted`，正式关注 `adjust_method = 'backward'` 与 `adjustment_factor`。
4. 计算入口：`src/lq/data/compute/adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()`。

### 3.2 首轮真实核验发现的前置阻塞（2026-04-08）

1. 当前环境中 `raw_market.duckdb.raw_xdxr_event` 为空表。
2. 当前环境中 `market_base.duckdb.stock_daily_adjusted` 虽有 `backward` 数据，但首轮抽样显示 `adjustment_factor` 为 `NULL`。
3. 当前机器上 `TDX_ROOT/T0002/hq_cache/gbbq` 文件存在，但 `src/lq/data/raw/gbbq_key.py` 不存在。
4. `raw_ingest_manifest` 中当前也没有任何 `dataset_name = 'xdxr'` 的入库记录。
5. 在上述前置问题未澄清前，本卡只能保持 `pending-validation`，不能创建结论性关闭文件。

## 4. 本卡回答的问题

1. 当前 `L2` 后复权价链是否可作为正式市场底座继续信任？
2. 如果有误差，误差来自事件处理、因子累乘链还是写入精度？
3. 哪类权益事件最容易出错，是否需要单独补测试？

## 5. 非目标

1. 不在本卡实现新的复权算法。
2. 不在本卡改写 data 全链路 bootstrap 方案。
3. 不在本卡扩展到所有 L2 衍生字段的全面质量审计。

## 6. 证据目标

1. 抽样对比表。
2. 至少若干个权益事件日前后对照截图或可复述记录。
3. 对因子链与价格链一致性的书面判断。

## 7. 关闭条件

1. 抽样覆盖范围、对照方法、误差容忍规则已明确。
2. evidence / record / conclusion 全部补齐。
3. 结论能明确回答“L2 后复权是否可进入正式主线验证层”。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/014-l2-backward-adjust-sampling-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/014-l2-backward-adjust-sampling-validation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `014-l2-backward-adjust-sampling-validation-conclusion-YYYYMMDD.md`
