# 017. MALF 兼容桥接与 PAS 准入修正 证据

## 文档证据

1. 新增执行卡：`docs/03-execution/017-malf-compatibility-bridge-and-pas-gate-fix-card-20260407.md`
2. 新增执行证据：`docs/03-execution/evidence/017-malf-compatibility-bridge-and-pas-gate-fix-evidence-20260407.md`
3. 新增执行记录：`docs/03-execution/records/017-malf-compatibility-bridge-and-pas-gate-fix-record-20260407.md`
4. 新增执行结论：`docs/03-execution/017-malf-compatibility-bridge-and-pas-gate-fix-conclusion-20260407.md`

## 代码证据

1. 修订 `src/lq/alpha/pas/pipeline.py`：
   - 从 `malf_context_snapshot` 同时读取 `malf_context_4`、`monthly_state`、`weekly_flow`
   - 修正 `cell_gate_check()` 的调用参数为 `(pattern, monthly_state, weekly_flow)`
   - 修正准入判断语义为 `False = 不准入`
   - 写入 `pas_formal_signal` 时透传 `monthly_state` / `weekly_flow`
2. 新增补丁测试：`tests/patches/alpha/test_pas_gate_bridge.py`

## 测试 / 运行证据

1. 初次命令：`pytest tests/patches/alpha/test_pas_gate_bridge.py -q`
   - 结果：失败
   - 原因：pytest 默认临时目录基座 `H:\Lifespan-temp\lq\pytest\default` 不存在
2. 修正后命令：`pytest tests/patches/alpha/test_pas_gate_bridge.py -q --basetemp H:\Lifespan-temp\pytest_pas_gate_bridge`
   - 结果：`2 passed in 1.72s`

## 影响边界证据

1. `src/lq/filter/pipeline.py` 当前仍从 `malf_context_snapshot` 读取 `monthly_state` / `weekly_flow` 以构造兼容 `MalfContext`，本轮未改。
2. `src/lq/system/orchestration.py` 当前解释链 `StockScanTrace` 仍记录 `monthly_state` 摘要字段，本轮未改。
3. `src/lq/position/sizing.py` 已有 016 后的历史兼容说明，但尚未迁移到生命周期 sizing，本轮未改。
