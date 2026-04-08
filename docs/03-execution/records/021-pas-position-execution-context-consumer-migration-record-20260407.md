# 021. PAS / position execution_context_snapshot 消费迁移 记录

## 对应关系

1. 对应卡：`docs/03-execution/021-pas-position-execution-context-consumer-migration-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/021-pas-position-execution-context-consumer-migration-evidence-20260407.md`

## 执行记录

1. 先复核 `alpha/pas` 与 `position` 设计/规格，确认当前正式口径应切到 `execution_context_snapshot`，而 `monthly_state / weekly_flow` 只能保留为 gate 兼容字段。
2. 修订 `PAS` 设计与 spec，把 `PasSignal` 的正式字段定义收敛为：
   - `long_background_2 / intermediate_role_2 / malf_context_4`
   - 三轴原始排位与生命周期总区间
   - 四分位辅助
   - `monthly_state / weekly_flow` 仅兼容
3. 修订 `position` 章程，明确 `PasSignal` 可以携带正式生命周期字段，但当前 sizing 公式不得因这些字段改变。
4. 扩展 `PasSignal` dataclass，并更新 `as_dict()` 输出。
5. 扩展 `pas_formal_signal` schema 与 migration，保证 research_lab 可持久化这些正式字段。
6. 将 `run_pas_batch()` 的正式读取源切到 `execution_context_snapshot`；同时保留对 `malf_context_snapshot` 的左连接，只为 gate 兼容字段服务。
7. 更新 `system / trade / integration test` 中的 `PasSignal` 构造点，避免中央合同升级后下游仍停留在旧形态。
8. 补跑 `PAS bridge`、`position unit` 与 `mainline integration` 测试，确认主线未断。

## 结果摘要

1. `PAS` 的正式消费入口已经切到 `execution_context_snapshot`。
2. `position` 已经能无侵入接收生命周期字段，但 sizing 公式保持不变。
3. `pas_formal_signal` 现在可落正式生命周期字段，不再只保存 `malf_context_4 + 兼容字段`。

## 未完成项 / 风险

1. `cell_gate_check()` 仍依赖 `monthly_state / weekly_flow`，这是兼容路径，后续若要正式收口需另开卡。
2. 生命周期字段当前仍可能是 bridge table 的第一版镜像值，不代表真实 ranking 算法已经完成。
3. `trade` 目前只是兼容接收这些字段，尚未基于其做执行决策。
