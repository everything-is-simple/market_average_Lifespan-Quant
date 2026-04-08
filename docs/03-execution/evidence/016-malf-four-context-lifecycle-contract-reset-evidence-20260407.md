# 016. MALF 四格上下文与生命周期执行合同重定向 证据

## 文档证据

1. 修订 design：`docs/01-design/modules/malf/00-malf-charter-20260331.md`
2. 修订 design：`docs/01-design/modules/malf/01-malf-full-cycle-layering-frozen-design-20260331.md`
3. 修订 design：`docs/01-design/modules/malf/02-malf-month-background-2-definition-20260331.md`
4. 修订 design：`docs/01-design/modules/malf/03-malf-weekly-flow-relation-frozen-definition-20260331.md`
5. 修订 design：`docs/01-design/modules/malf/04-malf-day-three-axis-definition-20260407.md`
6. 修订 design：`docs/01-design/modules/malf/05-malf-four-context-and-lifecycle-ranking-charter-20260407.md`
7. 修订 spec：`docs/02-spec/modules/malf/01-malf-four-context-lifecycle-execution-contract-spec-20260407.md`
8. 修订 execution：`docs/03-execution/016-malf-four-context-lifecycle-contract-reset-card-20260407.md`
9. 修订 execution：`docs/03-execution/016-malf-four-context-lifecycle-contract-reset-conclusion-20260407.md`
10. 修订 execution：`docs/03-execution/evidence/016-malf-four-context-lifecycle-contract-reset-evidence-20260407.md`
11. 修订 execution：`docs/03-execution/records/016-malf-four-context-lifecycle-contract-reset-record-20260407.md`

## 代码证据

1. `src/lq/malf/contracts.py` 当前已具备正式字段与兼容字段并存的合同框架，可与本轮 design/spec 对照验证。
2. `src/lq/malf/pipeline.py` 当前仍保留 `monthly_state`、`weekly_flow` 与日线旧命名，构成本轮 execution 记录中的待迁移边界证据。
3. `src/lq/alpha/pas/validation.py` 当前仍以旧 cell gate 依赖 `monthly_state_8` 与 `weekly_flow`，构成本轮后续代码迁移入口证据。

## 测试 / 运行证据

1. 本轮未进行代码实现改动，因此无新增 Python 编译证据。
2. 本轮证据以 design/spec/execution 文档修订与仓库现状比对为主。

## 书义锚点证据

1. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_160_img-54.jpeg.png`
2. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_345_img-57.jpeg.png`
3. 本轮 design/spec 明确把两张图解释为：同标的历史中级波段经验分布上的当前位置读数，而不是 `scene quartile` 或 `16-cell` 上下文标签

## 父系统对应证据

1. 父系统卡：`G:\MarketLifespan-Quant\docs\03-execution\281-malf-four-context-lifecycle-contract-reset-card-20260407.md`
2. 父系统 design：`G:\MarketLifespan-Quant\docs\01-design\modules\malf\28-malf-four-context-and-lifecycle-ranking-charter-20260407.md`
3. 父系统 spec：`G:\MarketLifespan-Quant\docs\02-spec\modules\malf\28-malf-four-context-lifecycle-execution-contract-spec-20260407.md`

## 结论性证据

1. `MALF` 已重新形成"`四格上下文 + 生命周期三轴历史排名 + 四分位执行合同`"的正式 design/spec 基线。
2. 旧 `monthly_state_8 / weekly_flow_relation_to_monthly / scene_id / quartile / 16-cell` 主线解释已被明确降级为历史兼容与诊断层。
3. `PAS / position` 的实际行为迁移尚未在本卡实施；本轮只完成合同重定向与历史化标记。
