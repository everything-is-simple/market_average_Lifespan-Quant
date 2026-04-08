# 规格层总入口 / 02-spec

## 用途

`02-spec/` 负责把 `01-design/` 的模块边界下沉为可执行规格。

它回答的问题是：

1. 正式合同字段是什么
2. 正式落表与写权边界是什么
3. runner / pipeline / 脚本入口的最小约束是什么
4. 哪些是正式字段，哪些只是兼容残留

## 当前状态

当前规格层处于**模块级已全覆盖**状态。

已存在的模块规格：

1. `modules/core/01-core-contracts-paths-and-resumable-spec-20260408.md`
2. `modules/data/01-data-l2-backward-adjustment-compute-spec-20260401.md`
3. `modules/malf/01-malf-four-context-lifecycle-execution-contract-spec-20260407.md`
4. `modules/alpha/01-alpha-pas-contracts-and-pipeline-spec-20260401.md`
5. `modules/structure/01-structure-snapshot-contracts-and-pipeline-spec-20260408.md`
6. `modules/filter/01-filter-adverse-conditions-and-pipeline-spec-20260408.md`
7. `modules/position/01-position-contracts-and-sizing-spec-20260408.md`
8. `modules/trade/01-trade-runtime-and-backtest-pipeline-spec-20260408.md`
9. `modules/system/01-system-orchestration-and-governance-spec-20260408.md`

根层总览文件：

1. `01-data-contracts-20260331.md` — 跨模块结果合同与七库读写边界总览

## 推荐阅读顺序

1. 先读对应模块的 `../01-design/modules/<module>/00-*-charter-*.md`
2. 再读本目录下对应模块 spec
3. 若该模块尚无 spec，再回到 design + execution 结论确认当前正式口径
4. 最后进入 `../03-execution/` 查看执行卡与真实闭环状态

## 模块覆盖状态

| 模块 | 规格文件 | 当前状态 |
|---|---|---|
| `core` | 已有 | 已覆盖 |
| `data` | 已有 | 已覆盖 |
| `malf` | 已有 | 已覆盖 |
| `structure` | 已有 | 已覆盖 |
| `filter` | 已有 | 已覆盖 |
| `alpha` | 已有 | 已覆盖 |
| `position` | 已有 | 已覆盖 |
| `trade` | 已有 | 已覆盖 |
| `system` | 已有 | 已覆盖 |

## 当前使用原则

1. 若根层总览 spec 与模块 spec 冲突，以**模块 spec** 为准
2. 若 spec 与已闭环 execution 结论冲突，应优先回看对应结论，再决定是否修 spec
3. 若模块尚无独立 spec，不得臆造正式字段或表结构，必须先以代码与已闭环结论核实
