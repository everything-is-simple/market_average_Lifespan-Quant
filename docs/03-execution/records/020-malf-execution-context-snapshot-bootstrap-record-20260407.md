# 020. MALF execution_context_snapshot bootstrap 记录

## 对应关系

1. 对应卡：`docs/03-execution/020-malf-execution-context-snapshot-bootstrap-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/020-malf-execution-context-snapshot-bootstrap-evidence-20260407.md`

## 执行记录

1. 重新盘点 `execution_context_snapshot` 的现状后确认：
   - design/spec 已有明确桥表定义
   - 代码侧此前只有口头目标，没有 schema、没有 writer、没有 reader
2. 为 `malf` 新增 `EXECUTION_CONTEXT_CONTRACT_VERSION`，把桥表也纳入显式合同版本管理。
3. 在 `src/lq/malf/pipeline.py` 中补上 `execution_context_snapshot` schema，并保持与 spec 最小正式列对齐。
4. 新增 `_build_execution_context_df()`，将当前 `malf_context_snapshot` 的正式执行字段镜像到 bridge table：
   - 上下文：`long_background_2 / intermediate_role_2 / malf_context_4`
   - 生命周期区间与四分位：直接镜像当前已有列
   - 暂不可算字段：`active_wave_id / historical_sample_count` 先落 `NULL`
   - `ranking_asof_date = signal_date`
5. 在 `_flush_batch()` 中新增 bridge table 的幂等写入：同日同股先删后插，与主 snapshot 保持一致刷新边界。
6. 新增补丁测试，验证 bridge table 能建表并落入第一版镜像数据。

## 结果摘要

1. `execution_context_snapshot` 已不再是“仅存在于设计文档中的桥表”。
2. 当前 `malf` 已能在写 `malf_context_snapshot` 的同时，落一份正式执行桥镜像。
3. 本轮没有提前伪造 active wave / 样本池 / 历史排名算法。

## 未完成项 / 风险

1. `active_wave_id`、`historical_sample_count`、真实排名状态仍未实现。
2. `PAS / position` 当前尚未消费 `execution_context_snapshot`，后续仍需迁移。
3. 当前 bridge table 的生命周期字段仍来自 `MalfContext` 现有列；当真实 ranking 算法落地后，需要验证桥表写入逻辑是否随之升级。
