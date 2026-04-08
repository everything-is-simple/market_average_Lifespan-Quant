# 设计层总入口 / 01-design

## 用途

`01-design/` 负责描述系统定位、主线链路、模块边界与关键架构决策。

它回答的问题是：

1. 系统是什么
2. 为什么这样分层
3. 每个模块负责什么、不负责什么
4. 当前正式主轴是什么

## 当前状态

当前设计层已经覆盖 9 个正式模块的章程与主要设计文档。

根层入口文件：

1. `00-system-overview-20260404.md` — 系统概述、主线铁律、模块索引
2. `01-system-architecture-20260404.md` — 架构分层、依赖矩阵、批处理约束

## 推荐阅读顺序

1. `00-system-overview-20260404.md`
2. `01-system-architecture-20260404.md`
3. 对应模块的 `modules/<module>/00-*-charter-*.md`
4. 对应模块的后续设计子文档
5. 再进入 `../02-spec/` 查接口与字段规格
6. 最后进入 `../03-execution/` 查卡、证据、记录与结论

## 模块覆盖状态

| 模块 | 章程 | 设计子文档 | 当前状态 |
|---|---|---|---|
| `core` | 已有 | 已有 | 已覆盖 |
| `data` | 已有 | 已有 | 已覆盖 |
| `malf` | 已有 | 已有 | 已覆盖 |
| `structure` | 已有 | 已有 | 已覆盖 |
| `filter` | 已有 | 已有 | 已覆盖 |
| `alpha` | 已有 | 已有 | 已覆盖 |
| `position` | 已有 | 已有 | 已覆盖 |
| `trade` | 已有 | 已有 | 已覆盖 |
| `system` | 已有 | 已有 | 已覆盖 |

## 当前主线提醒

1. 正式主线链路固定为：`data → malf → structure → filter → alpha/pas → position → trade → system`
2. `MALF` 当前正式执行主轴是：`long_background_2 / intermediate_role_2 / malf_context_4` + 生命周期三轴排位
3. `execution_context_snapshot` 是下游正式消费入口
4. `BPB / CPB` 不属于当前 system 主线可调用 trigger

## 与 spec / execution 的关系

1. `design` 先定义边界与原则
2. `spec` 再冻结字段、表、函数入口与 runner 合同
3. `execution` 最后记录执行闭环
