# 014. L2 后复权抽样验证 证据（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/014-l2-backward-adjust-sampling-validation-card-20260406.md`
2. 对应记录：`docs/03-execution/records/014-l2-backward-adjust-sampling-validation-record-20260408.md`
3. 对应结论：待真实执行关闭时按实际日期创建

## 文档证据

1. 已将 `014` 卡纠偏为当前系统口径的 L2 后复权抽样验证卡。
2. 已在卡内明确：本卡只做数据质量验证，不改主线数据源路线。
3. 已在卡内明确：抽样必须覆盖典型权益事件与不同市场类型，且要把问题定位到因子、事件映射或写入链路。
4. 已补入闭环文件段，明确 evidence / record / conclusion 路径。

## 合同证据

1. 本卡当前依赖 `market_base`、`adjust_factor` 以及外部参考对照。
2. 本卡当前关注的是后复权价格链与因子链的一致性，而不是新算法设计。
3. 本卡不扩展到全部 L2 衍生字段，只聚焦正式主线最关键的后复权正确性。

## 与当前 data spec 对齐的正式锚点

1. 当前正式抽样核验对象已收敛为：`raw_xdxr_event`、`raw_stock_daily`、`stock_daily_adjusted.adjustment_factor` 与后复权价格链的一致性。
2. 当前异常回溯入口已收敛为 `src/lq/data/compute/adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()`。
3. 因此，本卡的真实执行重点不是“泛泛看价格像不像”，而是把权益事件、因子累乘链与写出后的 OHLC 一起核对。

## 待执行证据

下列证据尚未生成，需在真实执行验证时补入：

1. 抽样对比表。
2. 权益事件日前后对照截图或可复述记录。
3. 因子链与价格链一致性的判断说明。
4. 对“L2 后复权是否可进入正式主线验证层”的最终判断。

## 首轮真实只读核验证据（2026-04-08）

1. 已执行只读查询，检查 `raw_market.duckdb.raw_xdxr_event` 的表结构、样本行与分类分布。
2. 查询结果显示：`raw_xdxr_event` 当前为空表，`SELECT * FROM raw_xdxr_event LIMIT 5` 返回空结果，分类统计也为空。
3. 已执行只读查询，检查 `raw_market.duckdb.raw_stock_daily` 与 `market_base.duckdb.stock_daily_adjusted`。
4. 查询结果显示：
   - `raw_stock_daily` 当前有 `18153` 行
   - `stock_daily_adjusted` 当前有 `18153` 行
   - `adjust_method` 当前全部为 `backward`
   - 首轮样本中的 `adjustment_factor` 为 `NULL`
5. 已进一步执行环境前置检查，结果显示：
   - `TDX_ROOT = H:\new_tdx64`
   - `H:\new_tdx64\T0002\hq_cache\gbbq` 文件存在
   - `src/lq/data/raw/gbbq_key.py` 不存在
   - `raw_ingest_manifest` 中没有任何 `dataset_name = 'xdxr'` 的记录
6. 已进一步执行只读查询，确认当前 `stock_daily_adjusted` 全表 `adjustment_factor` 均为空，且 `build_run_id` 仍为旧值 `txt-adj-bac-2026-04-04-85f8712d`。
7. 因此，本卡首轮真实核验已把前置阻塞收敛为：缺少 `gbbq_key.py` → 无法执行 `ingest_xdxr.py` → `raw_xdxr_event` 无数据；同时当前 `market_base` 仍停留在旧 L2 结果，尚不具备正式抽样对照条件。

## 当前结论性证据

1. 本轮已完成 `014` 的首轮真实只读核验，而不再只是卡面准备。
2. 当前可以确认的结论不是“后复权链已通过验证”，而是：本卡已暴露出两个正式前置阻塞，暂不具备创建 conclusion 的事实基础。

## 真实执行模板（基于已确认字段）

1. 原始事件表：`raw_market.duckdb.raw_xdxr_event`，关键字段已确认包括 `event_date`、`category`、`fenhong`、`peigujia`、`songzhuangu`、`peigu`。
2. 原始日线表：`raw_market.duckdb.raw_stock_daily`，用于核对事件日前最近交易日收盘价。
3. 后复权结果表：`market_base.duckdb.stock_daily_adjusted`，已确认包含 `adjust_method = 'backward'` 与 `adjustment_factor` 字段。
4. 函数入口已确认位于 `src/lq/data/compute/adjust.py`：`compute_backward_factors()` 与 `apply_backward_adjustment()`；抽样异常时应优先回溯这两个入口。
5. evidence 最终至少应落三类资产：抽样股票与事件清单、事件日前后价格/因子对照表、对因子链与价格链一致性的书面判断。

## 当前已确认的前置执行条件

1. 当前更像是环境前置未完成，而不是 `adjust.py` 最小逻辑缺失。
2. 第一前置：补齐 `src/lq/data/raw/gbbq_key.py`，使 `python scripts/data/ingest_xdxr.py` 具备可运行条件。
3. 第二前置：完成 `python scripts/data/ingest_xdxr.py`，使 `raw_xdxr_event` 产生正式入库记录。
4. 第三前置：执行 `python scripts/data/build_l2_adjusted.py`，生成带当前口径的 `stock_daily_adjusted`。
5. 只有在上述三步完成后，本卡才重新具备“事件样本抽样对照”的基础。
