# 016. MALF 四格上下文与生命周期执行合同重定向 证据

## 文档证据

1. 新增 design：`docs/01-design/modules/malf/07-malf-four-context-and-lifecycle-ranking-charter-20260407.md`
2. 新增 spec：`docs/02-spec/modules/malf/02-malf-four-context-lifecycle-execution-contract-spec-20260407.md`
3. 历史化标记 design `02`：`docs/01-design/modules/malf/02-malf-three-layer-matrix-frozen-contract-20260331.md`
4. 历史化标记 design `03`：`docs/01-design/modules/malf/03-malf-monthly-state-8-frozen-definition-20260331.md`
5. 历史化标记 design `05`：`docs/01-design/modules/malf/05-malf-pipeline-and-contracts-frozen-design-20260331.md`
6. 历史化标记 spec `01`：`docs/02-spec/modules/malf/01-malf-three-layer-matrix-spec-20260401.md`

## 代码证据

1. 兼容注释 `src/lq/malf/contracts.py`：顶部补充历史兼容说明
2. 兼容注释 `src/lq/alpha/pas/pipeline.py`：顶部补充历史兼容说明
3. 兼容注释 `src/lq/position/sizing.py`：顶部补充历史兼容说明

## 测试 / 运行证据

1. 执行命令：`python -m py_compile src/lq/malf/contracts.py`
2. 执行命令：`python -m py_compile src/lq/alpha/pas/pipeline.py`
3. 执行命令：`python -m py_compile src/lq/position/sizing.py`
4. 结果摘要：所有修改过的 Python 文件编译通过

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
