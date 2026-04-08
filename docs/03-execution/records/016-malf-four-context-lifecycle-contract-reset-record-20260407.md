# 016. MALF 四格上下文与生命周期执行合同重定向 记录

## 对应关系

1. 对应卡：`docs/03-execution/016-malf-four-context-lifecycle-contract-reset-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/016-malf-four-context-lifecycle-contract-reset-evidence-20260407.md`

## 执行记录

1. 修订 `00-05` 号 design，统一把 `MALF` 收口为“先四格上下文分类，再做波幅 / 时间 / 新价结构三轴原始历史排位，四分位只作辅助表达”。
2. 在 `00-05` 号 design 中显式补入历史化说明，明确 `monthly_state_8`、`weekly_flow`、三层矩阵、`scene quartile` 等概念只保留诊断 / 兼容 / 追溯地位。
3. 修订 `01-malf-four-context-lifecycle-execution-contract-spec-20260407.md`，明确正式最小字段、兼容残留字段边界、runner 输入、PAS 输入与 position 输入不得回退到旧主轴。
4. 修订 `016` 卡 / 结论 / 证据 / 记录，使 execution 四件套与当前真实 design/spec 文件编号保持一致。

## 运行口径

1. 外部语义锚点固定为两张书图：`page_160_img-54.jpeg.png` 与 `page_345_img-57.jpeg.png`
2. 父系统对应卡号：`281`

## 结果摘要

1. 本轮完成的是 design / spec / execution 层的合同重定向与历史化治理，不是新 runner 实装。
2. 当前正式收口路径已经统一为：`四格上下文 + 生命周期三轴原始排位 + 四分位辅助`。
3. 尚未覆盖的新实现边界是：真正把 `execution_context_snapshot` 落表，并让 `PAS / position` 从兼容路径迁移到生命周期路径。

## 未完成项 / 风险

1. `PAS / position` 仍在消费兼容字段与固定仓位基线，实际行为尚未迁移到生命周期合同。
2. `pipeline / contracts / orchestration` 等实现层仍保留 `monthly_state`、`weekly_flow`、`is_new_high_today` 等旧命名，需要后续代码迁移时统一收敛。
3. 若继续推进，后续最自然入口应是"`execution_context_snapshot` 落表 + PAS 接口迁移 + position 生命周期 sizing 迁移"。
