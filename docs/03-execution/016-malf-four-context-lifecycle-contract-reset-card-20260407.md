# 016. MALF 四格上下文与生命周期执行合同重定向 卡

**状态**: `Closed`
**类型**: `malf / design-reset / lifecycle-contract`
**模块**: `malf`

## 1. 定位

这张卡只解决一件事：

把 `MALF` 从已经跑偏的"`8态月线 x 2态周线 x PAS` 三层矩阵主轴"重新冻结回"`四格上下文 + 同标的历史中级波段三轴排名 + 四分位执行合同`"。

> 父系统对应卡：`G:\MarketLifespan-Quant\docs\03-execution\281-malf-four-context-lifecycle-contract-reset-card-20260407.md`

## 2. 固定因素

1. `LONG / INTERMEDIATE / SHORT` 的层级分工不推翻，其中 `INTERMEDIATE` 仍是正式寿命统计对象。
2. 现有 `malf_context_snapshot / 16-cell` 产物为了兼容既有 run 与结论，可以保留但不能继续冒充正确设计。
3. 本轮固定以两张书图为权威语义锚点：`page_160_img-54.jpeg.png` 与 `page_345_img-57.jpeg.png`，目标是让计算机复刻其经验分布读数，而不是继续手工解释。

## 2.1 性能与库复用前置检查

1. 本卡只做设计/规格/兼容治理，不新增正式全市场重跑。
2. 现有七库表族与 pipeline 暂不改动；本轮先冻结后续应新增的 `execution_context_snapshot` 合同。
3. 不适用当前性能瓶颈分析。
4. 不适用当前内存瓶颈分析。
5. 不新增批量 flush / checkpoint 行为。
6. 不新增全量导出。

## 3. 输出要求

本卡要求正式新增或正式变更：

1. 修订现有 `00-05` 号 design / `01` 号 spec，正式冻结 `MALF` 的四格上下文与生命周期三轴排名合同。
2. 对 design、spec 以及相关实现代码中的旧三层矩阵、月线八态主轴、旧 quartile 命名补齐"历史兼容/放弃原因"标记。

## 4. 本卡回答的问题

1. `MALF` 的"趋势生命"到底体现在哪里，正式该如何定义、如何数、如何落库？
2. 现有哪些设计文档和实现代码已经跑偏，为什么保留、又为什么明确放弃其"当前正确设计"地位？

## 5. 非目标

1. 不在本卡直接改写 `PAS / position` 的实际业务行为或仓位公式。
2. 不在本卡直接重跑历史 `16-cell` 正式结论。

## 6. 证据目标

本卡至少要留下：

1. design/spec/code/doc 的修改证据。
2. 对"哪些口径被 016 覆盖、放弃原因是什么"的正式结论文档。

## 7. 关闭条件

1. `00-05` 号 design / `01` 号 spec 已形成一致口径，且明确写清字段、表、runner、PAS 接口、position 接口。
2. 相关设计文档、规格文档与实现代码已形成显式历史化说明。
3. `evidence / record / conclusion` 已补齐。
4. 相关执行索引已回填。
