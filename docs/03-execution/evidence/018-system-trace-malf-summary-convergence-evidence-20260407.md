# 018. system 解释链 MALF 摘要收敛 证据

## 文档证据

1. 新增执行卡：`docs/03-execution/018-system-trace-malf-summary-convergence-card-20260407.md`
2. 新增执行证据：`docs/03-execution/evidence/018-system-trace-malf-summary-convergence-evidence-20260407.md`
3. 新增执行记录：`docs/03-execution/records/018-system-trace-malf-summary-convergence-record-20260407.md`
4. 新增执行结论：`docs/03-execution/018-system-trace-malf-summary-convergence-conclusion-20260407.md`

## 代码证据

1. 修订 `src/lq/system/orchestration.py`
   - `StockScanTrace` 新增 `long_background_2` 与 `intermediate_role_2`
   - `as_dict()` 新增两项正式 MALF 摘要输出
   - `run_daily_signal_scan()` 在过滤路径与通过路径都透传两项正式摘要
2. 修订 `tests/patches/system/test_explain_chain.py`
   - 更新 `StockScanTrace` 构造
   - 补充 `as_dict()` 对正式 MALF 摘要字段的断言
3. 修订 `tests/integration/test_mainline_pipeline.py`
   - 更新解释链构造夹具
   - 验证解释链优先输出 `long_background_2 / intermediate_role_2`

## 测试证据

命令：

```bash
pytest tests/patches/system/test_explain_chain.py tests/integration/test_mainline_pipeline.py -q --basetemp H:\Lifespan-temp\pytest_system_trace
```

结果：

```text
46 passed in 2.42s
```

## 边界证据

1. `filter` 的 A4-5 设计文档当前仍明确绑定 `monthly_state / weekly_flow`，因此本卡未改其行为实现。
2. `monthly_state` 在 `system` 解释链中仍保留，但已降级为兼容摘要字段，不再是唯一 MALF 摘要。
