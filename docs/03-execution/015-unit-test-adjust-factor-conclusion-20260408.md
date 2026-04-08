# 015. 复权因子单测补全 结论 / 2026-04-08

## 1. 对应关系

1. 对应卡：`docs/03-execution/015-unit-test-adjust-factor-card-20260406.md`
2. 对应证据：`docs/03-execution/evidence/015-unit-test-adjust-factor-evidence-20260408.md`
3. 对应记录：`docs/03-execution/records/015-unit-test-adjust-factor-record-20260408.md`

## 2. 关闭判断

本卡已关闭。

关闭结论：

1. `src/lq/data/compute/adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()` 已具备最小关键路径单测保护。
2. 本轮新增 `tests/unit/data/test_adjust_factor.py`，覆盖无事件、单一分红、单一复合事件、多事件累乘，以及 `apply_backward_adjustment()` 的输出校验。
3. 执行 `python -m pytest tests/unit/data/test_adjust_factor.py -q`，结果为 `5 passed in 2.17s`。

## 3. 本卡回答的问题

### 3.1 哪些复权因子计算路径最需要最小稳定测试保护？

本轮已覆盖的最小关键路径为：

1. 无事件时因子全为 `1.0`
2. 单一权益事件时 `factor_i` 计算正确
3. 多事件场景下因子按事件链累乘
4. `apply_backward_adjustment()` 能正确写出 `adjustment_factor`，同步调整 OHLC，并过滤停牌日

### 3.2 `014` 若发现抽样异常，是否可以用这些单测快速复现？

可以作为第一层离线复现入口。

1. 若 `014` 发现单事件样本异常，可先在本卡单测框架中复现同类事件口径。
2. 若 `014` 发现多事件样本异常，可优先检查事件链累乘逻辑。
3. 若 `014` 发现写出结果异常，可优先检查 `apply_backward_adjustment()` 对 OHLC 与 `adjustment_factor` 的同步写出。

### 3.3 当前复权因子实现是否还缺关键边界测试？

仍有后续可补边界，但不阻塞本卡关闭。

当前未覆盖但后续可按需要补充：

1. 更复杂的跨市场样本差异
2. 异常事件数据缺失或分母异常的跳过路径
3. 更多真实权益事件组合与日期边界

## 4. 对主线的意义

1. `015` 已为 `014` 提供最小离线兜底。
2. data 模块在后复权链路上不再完全依赖人工抽样判断。
3. 本卡关闭后，data 方向下一张最自然应推进的卡变为 `014`：真实抽样验证后复权价格链与因子链的一致性。

## 5. 后续动作

1. 保持 `015` 为已闭环状态，不再回退为 pending。
2. 将 `014` 作为 data 方向下一张优先执行卡。
3. 若 `014` 发现异常，再围绕具体异常补充更细测试场景，而不是重新打开本卡的最小保护结论。
