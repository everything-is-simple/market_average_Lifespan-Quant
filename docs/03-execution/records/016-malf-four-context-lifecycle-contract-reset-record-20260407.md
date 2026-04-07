# 016. MALF 四格上下文与生命周期执行合同重定向 记录

## 对应关系

1. 对应卡：`docs/03-execution/016-malf-four-context-lifecycle-contract-reset-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/016-malf-four-context-lifecycle-contract-reset-evidence-20260407.md`

## 执行记录

1. 新增 `07` 号 design / `02` 号 spec，正式写清四格上下文、生命周期三轴原始排位（amplitude/duration/new_price 的 rank_low/rank_high/rank_total）、四分位压缩、总生命区间（lifecycle_rank_low/high/total = 三轴小值/大值简单相加）、`execution_context_snapshot` 桥表、PAS 接口、position 接口。
2. 对 `02/03/05` 号 design 与 `01` 号 spec 补充"被 016 覆盖"的历史化说明，明确旧三层矩阵 / 16 格路径不再代表当前正确设计。
3. 对 `lq.malf.contracts` / `lq.alpha.pas.pipeline` / `lq.position.sizing` 中仍显式消费旧三层主轴或固定仓位的兼容实现补充中文注释，明确其当前只具历史兼容身份。
4. 更新 `00-malf-charter-20260331.md` 文档索引，补入 `07` 号文档。
5. 更新 `README.md` 卡目录，补入 `016`。

## 运行口径

1. 外部语义锚点固定为两张书图：`page_160_img-54.jpeg.png` 与 `page_345_img-57.jpeg.png`
2. 父系统对应卡号：`281`

## 结果摘要

1. 本轮完成的是合同重定向与历史化治理，不是新 runner 实装。
2. 执行四件套、design/spec 与索引已形成新的正式收口路径。
3. 尚未覆盖的新实现边界是：真正把 `execution_context_snapshot` 落表，并让 `PAS / position` 从兼容路径迁移到生命周期路径。

## 未完成项 / 风险

1. `PAS / position` 仍在消费兼容字段与固定仓位基线，实际行为尚未迁移到生命周期合同。
2. 若继续推进，后续最自然入口应是"`execution_context_snapshot` 落表 + PAS 接口迁移 + position 生命周期 sizing 迁移"。
