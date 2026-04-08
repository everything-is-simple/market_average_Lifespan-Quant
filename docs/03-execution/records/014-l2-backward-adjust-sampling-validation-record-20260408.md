# 014. L2 后复权抽样验证 记录（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/014-l2-backward-adjust-sampling-validation-card-20260406.md`
2. 对应证据：`docs/03-execution/evidence/014-l2-backward-adjust-sampling-validation-evidence-20260408.md`

## 本轮执行记录

1. 复核并重写了 `014` 卡，将其收敛为当前系统口径的后复权抽样验证卡。
2. 在卡内固定了问题边界：本卡只验证正式市场底座的后复权价格链与因子链正确性，不改 data 主线路线。
3. 在卡内明确：抽样必须覆盖典型权益事件与不同市场类型，不能只抽“干净样本”。
4. 在卡内补入闭环文件段，明确 evidence / record / conclusion 的路径约定。
5. 创建了本次 evidence 文档，用于记录当前已完成的 execution 准备动作与待补抽样证据。
6. 已把当前正式核验锚点收敛到 `raw_xdxr_event`、`raw_stock_daily`、`stock_daily_adjusted.adjustment_factor` 与 `adjust.py` 两个关键函数。
7. 已明确本卡与 `015` 的配套关系：`014` 负责抽样发现问题，`015` 负责提供最小单测兜底与复现入口。
8. 已执行首轮真实只读核验，检查 `raw_xdxr_event`、`raw_stock_daily` 与 `stock_daily_adjusted` 的可用样本情况。
9. 核验结果显示：`raw_xdxr_event` 当前为空表；`raw_stock_daily` 与 `stock_daily_adjusted` 当前各有 `18153` 行；`stock_daily_adjusted` 当前样本中的 `adjustment_factor` 为 `NULL`。
10. 因此，本轮没有进入“事件日前后价格链抽样对照”阶段，而是在前置盘点阶段识别出正式阻塞项。
11. 已继续执行环境前置检查，确认 `TDX_ROOT/T0002/hq_cache/gbbq` 文件存在，但 `src/lq/data/raw/gbbq_key.py` 缺失，且 `raw_ingest_manifest` 中没有任何 `xdxr` 入库记录。
12. 已继续执行 `market_base` 只读核查，确认 `stock_daily_adjusted` 当前全表 `adjustment_factor` 为空，`build_run_id` 仍为旧值 `txt-adj-bac-2026-04-04-85f8712d`。

## 当前运行口径

1. 本卡属于 `pending-validation`，尚未转为 closed。
2. 本卡当前不产出抽样通过结论，不宣告 L2 后复权链已经完成正式验证。
3. 当前阻塞已经收敛为：缺少 `gbbq_key.py`、没有 `xdxr` ingest 记录、`market_base` 仍停留在旧 L2 结果。
4. 因此，本卡尚不具备创建 conclusion 的事实基础。
5. 正式关闭前，必须先解除上述阻塞，再补齐抽样对照、事件前后验证、因子链一致性判断与结论文档。

## 未完成项

1. 补齐 `src/lq/data/raw/gbbq_key.py`。
2. 执行 `python scripts/data/ingest_xdxr.py`，确认 `raw_xdxr_event` 与 `raw_ingest_manifest(dataset_name='xdxr')` 有正式记录。
3. 执行 `python scripts/data/build_l2_adjusted.py`，生成新的 `stock_daily_adjusted` 与 `adjustment_factor`。
4. 在上述阻塞解除后，重新确认抽样名单、外部对照来源与误差容忍规则。
5. 执行权益事件样本核验，并形成因子链与价格链一致性判断。
6. 满足事实基础后再创建 conclusion 文件。

## 当前后续判断

1. 结合代码与数据现状，当前阻塞更像环境前置未执行完成，而不是 `adjust.py` 最小计算路径缺失。
2. 已确认的前置脚本入口有两个：
   - `python scripts/data/ingest_xdxr.py`
   - `python scripts/data/build_l2_adjusted.py`
3. 因此，本卡下一步不是直接写 conclusion，也不是先改 `adjust.py`，而是先确认上述前置是否需要在当前环境补跑。
