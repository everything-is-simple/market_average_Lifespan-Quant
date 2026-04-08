# 017. MALF 兼容桥接与 PAS 准入修正 记录

## 对应关系

1. 对应卡：`docs/03-execution/017-malf-compatibility-bridge-and-pas-gate-fix-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/017-malf-compatibility-bridge-and-pas-gate-fix-evidence-20260407.md`

## 执行记录

1. 复核 `alpha/pas/validation.py` 与 `alpha/pas/pipeline.py` 后确认：`cell_gate_check()` 的定义要求 `(pattern, monthly_state, weekly_flow)`，但 pipeline 实际只传了 `ctx4_label`，且还按字符串 `"rejected"` 判断返回值，形成接口漂移。
2. 修订 `src/lq/alpha/pas/pipeline.py`，把 MALF 读取从“只读 `malf_context_4`”改为“同时读取 `malf_context_4 + monthly_state + weekly_flow`”，恢复兼容桥接所需最小上下文。
3. 修订 `src/lq/alpha/pas/pipeline.py` 中的准入判断，改为用真实 `monthly_state / weekly_flow` 调用 `cell_gate_check()`，并按布尔返回值过滤不准入信号。
4. 修订 `src/lq/alpha/pas/pipeline.py` 中的 `pas_formal_signal` 写入逻辑，使其能落入触发当日的 `monthly_state / weekly_flow` 兼容字段，而不是恒为 `None`。
5. 新增 `tests/patches/alpha/test_pas_gate_bridge.py`，覆盖两条回归路径：
   - 准入格 `PB` 信号会被写入，并保留兼容字段
   - 非准入格 `PB` 信号会被拦截，不写正式信号表
6. 首次运行 pytest 时遇到环境问题：默认 basetemp 指向 `H:\Lifespan-temp\lq\pytest\default`，其上级路径不存在；随后改用显式 `--basetemp` 重跑并通过。

## 结果摘要

1. 当前 `MALF → PAS` 的兼容桥接已从“接口错位”修回到“可运行且语义一致”。
2. 本轮没有实现生命周期三轴排位，也没有把 `PAS` 迁移到 `execution_context_snapshot`。
3. 本轮只修最危险的根因问题：参数错传、返回值语义错读、兼容字段落库缺失。

## 未完成项 / 风险

1. `PAS` 当前仍以 `monthly_state / weekly_flow` 兼容字段执行精确 cell gate，尚未迁移到 016 目标态下的新生命周期读数接口。
2. `filter / system` 仍保留对旧字段的兼容消费，本轮只盘清影响点，未迁移。
3. `position` 尚未消费生命周期三轴排位，仍停留在固定名义资金桥接阶段。
