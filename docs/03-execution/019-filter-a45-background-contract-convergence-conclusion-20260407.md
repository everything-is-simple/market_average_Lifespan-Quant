# 019. filter A4-5 背景合同收敛 结论

## 结论

`019` `可以` 关闭。

本轮正式结论是：

1. `filter` A4-5 的正式背景合同已经收敛到 `long_background_2 / intermediate_role_2 / malf_context_4` 这一组 MALF 正式摘要。
2. `monthly_state / weekly_flow` 没有被粗暴删除，而是降级为兼容细粒度来源，用于保留 `BEAR_FORMING / BEAR_PERSISTING` 这类阶段差异。
3. 相关补丁测试已通过，说明这次收敛没有放松当前的保守过滤语义。

## 当前边界

1. 本结论只覆盖 `filter` A4-5，不覆盖其他 adverse 条件。
2. 本结论不覆盖生命周期三轴过滤。
3. 本结论不覆盖 `execution_context_snapshot`。

## 后续入口

1. 下一步最自然的方向是：实现 `execution_context_snapshot`，让 `PAS / position / system / filter` 都能开始消费统一的生命周期执行读数。
2. 若继续沿兼容清理线推进，可回看 `MalfContext` 合同本身，决定旧字段何时继续下沉。

## 历史化说明

1. 本轮不是删除旧字段，而是把旧字段从 A4-5 的正式主轴位置降到兼容细粒度位置。
2. 在全仓正式执行合同完全落地前，这类兼容字段仍会存在，但不再应被当成 filter 的正式背景主轴。
