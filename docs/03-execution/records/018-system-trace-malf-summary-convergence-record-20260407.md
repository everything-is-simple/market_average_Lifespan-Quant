# 018. system 解释链 MALF 摘要收敛 记录

## 对应关系

1. 对应卡：`docs/03-execution/018-system-trace-malf-summary-convergence-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/018-system-trace-malf-summary-convergence-evidence-20260407.md`

## 执行记录

1. 先复核 `filter` 与 `system` 设计文档，确认：
   - `system` 解释链可以先前移到正式 MALF 摘要字段
   - `filter` 的 A4-5 仍由当前设计文档明确绑定 `monthly_state / weekly_flow`，不能在本轮越文档直接改行为
2. 修订 `src/lq/system/orchestration.py` 中的 `StockScanTrace` 数据合同，新增 `long_background_2` 与 `intermediate_role_2`，使 system 解释链优先暴露正式 MALF 摘要。
3. 修订 `run_daily_signal_scan()` 两条写解释链路径（被过滤 / 通过过滤），确保两项正式摘要均被透传。
4. 保留 `monthly_state` 字段，但其角色收敛为兼容摘要，便于旧复盘链路继续读取。
5. 更新 `tests/patches/system/test_explain_chain.py` 与 `tests/integration/test_mainline_pipeline.py`，同步新合同并验证解释链输出。
6. 运行最小相关测试集并通过：`46 passed in 2.42s`。

## 结果摘要

1. `system` 层解释链现在不再只以 `monthly_state` 表示 MALF 摘要。
2. 正式执行层字段 `long_background_2 / intermediate_role_2 / malf_context_4` 已进入解释链主视图。
3. 本轮未改变任何过滤行为、PAS 准入行为或 position sizing 行为。

## 未完成项 / 风险

1. `filter` 的 A4-5 仍是旧字段驱动，这不是遗漏，而是当前设计文档的真实边界；若要迁移，必须先改 design/spec。
2. `execution_context_snapshot` 仍未实现，`system / position / PAS` 还未进入生命周期三轴正式接口。
3. 旧字段 `monthly_state` 仍继续出现在解释链中，当前是兼容保留而非完全移除。
