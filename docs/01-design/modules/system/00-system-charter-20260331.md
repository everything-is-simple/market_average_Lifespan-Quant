# system 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\system\` | 正式定型 |
| 本系统 | `G:\Lifespan-Quant\src\lq\system\` | 继承父系统编排理念，主线链路新增 structure / filter 层 |

## 2. 模块定位

`system` 是主线编排层。

它是唯一被允许依赖所有其他模块的模块，负责驱动完整的每日信号扫描流程和批量回测。

**`system` 只做编排，不做计算。** 所有业务逻辑必须在对应模块中实现。

## 3. 主线链路（冻结）

```
data → malf → structure(filter) → alpha/pas → position → trade → system
```

每个环节的职责固定，`system` 只负责按序调用各模块接口，收集 `SystemRunSummary`。

## 4. 正式输入

1. 运行日期（`run_date`）
2. 各模块已构建的数据库（`raw_market.duckdb`、`market_base.duckdb`、`malf.duckdb`）
3. 运行模式（`SCAN` 每日扫描 / `BACKTEST` 历史回测）

## 5. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `SystemRunSummary` | `dataclass`（冻结合同） | 落入 `trade_runtime.duckdb`（L4），可生成报告 |

`SystemRunSummary` 包含：run_id、run_date、信号数、过滤数、触发数、错误摘要。

## 6. BPB 禁止主线

`BPB` trigger 在 `system` 层永久禁止启用。无论测试参数如何，`system` 层编排不得调用 BPB 信号路径。

## 7. 模块边界

### 7.1 负责

1. 主线链路编排（按序调用各模块）
2. 每日信号扫描 runner
3. 批量历史回测 runner
4. `SystemRunSummary` 生成与落库
5. 运行日志与错误捕获

### 7.2 不负责

1. 任何业务计算（属于各业务模块）
2. 数据库 schema 创建（属于各模块 bootstrap）
3. 报告生成（属于独立报告脚本）

## 8. 铁律

1. `system` 是唯一允许同时依赖所有模块的模块，其他模块禁止互相横向依赖。
2. 主线链路顺序冻结，不允许跳过 `filter` 直接进入 `alpha/pas`。
3. `BPB` 在 `system` 层永久禁止，代码注释必须标明原因。
4. `system` 层不允许包含业务计算逻辑，只能调用其他模块的公开接口。
5. 每次 runner 运行必须生成可追溯的 `run_id`。

## 9. 成功标准

1. 每日扫描 runner 能端到端运行，覆盖主线全链路
2. 批量回测 runner 能在三年历史窗口正确推进
3. `BPB` 在任何 system 调用路径中均不出现
4. `SystemRunSummary` 落库并可被报告脚本消费
5. 运行失败时有可读错误摘要，不会静默失败
