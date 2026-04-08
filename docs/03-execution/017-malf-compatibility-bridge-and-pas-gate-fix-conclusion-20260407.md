# 017. MALF 兼容桥接与 PAS 准入修正 结论

## 结论

`017` `可以` 关闭。

本轮正式结论是：

1. `PAS` 对 `cell_gate_check()` 的调用错位已被修正，不再把 `malf_context_4` 错当成 `monthly_state` 传入，也不再把布尔返回值误读成字符串状态。
2. `pas_formal_signal` 现已能写入与信号同日一致的 `monthly_state / weekly_flow` 兼容字段，恢复研究侧对旧 run/旧报表的追溯能力。
3. `MALF → PAS` 当前已恢复到“兼容桥接可用，但仍非 016 目标态”的状态：能正确消费旧兼容字段，但尚未升级到生命周期三轴执行接口。

## 当前边界

1. 本结论只覆盖 `alpha/pas` 的兼容桥接修复，不覆盖 `execution_context_snapshot` 落表实现。
2. 本结论不覆盖 `filter / system / position` 的进一步迁移，只记录其当前仍保留兼容字段消费。

## 后续入口

1. 若继续推进，最自然的下一步是：为 `MALF` 实现 `execution_context_snapshot`，然后把 `PAS / position / system` 逐步切到正式生命周期合同。
2. `filter / system` 可作为后续兼容清理的第二梯队入口。

## 历史化说明

1. 本轮保留 `monthly_state / weekly_flow` 不是回退 016，而是对当前实现层残留依赖做桥接修补。
2. 在生命周期三轴正式落地前，这类兼容字段仍会存在；但它们的地位已经固定为“兼容桥”，不再是正式执行主轴。
