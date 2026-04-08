# 018. system 解释链 MALF 摘要收敛 结论

## 结论

`018` `可以` 关闭。

本轮正式结论是：

1. `system` 的 `StockScanTrace` 已收敛到以正式 MALF 摘要字段为主：`long_background_2`、`intermediate_role_2`、`malf_context_4`。
2. `monthly_state` 继续保留，但已经降级为兼容摘要字段，不再单独承担 system 层的 MALF 主摘要职责。
3. 解释链相关补丁测试与集成测试已通过，说明该收敛没有破坏现有 replay / 解释链路径。

## 当前边界

1. 本结论只覆盖 `system` 解释链合同，不覆盖 `filter` A4-5 行为迁移。
2. 本结论不覆盖 `execution_context_snapshot` 的落表与消费。
3. 本结论不覆盖 `position` 生命周期 sizing 合同。

## 后续入口

1. 下一步应回到 `filter`：先把 A4-5 的 design/spec 从旧字段主轴改到正式上下文字段，再迁移实现。
2. 再下一步是 `execution_context_snapshot` 与生命周期三轴读数，推动 `PAS / position / system` 进入 016 目标态。

## 历史化说明

1. 本轮不是移除 `monthly_state`，而是把它从 system 层的主摘要位置降到兼容位置。
2. 当下游复盘链路全部切到正式 MALF 摘要后，`monthly_state` 才有条件继续下沉或退出解释链主视图。
