# structure 模块章程 / 2026-03-31

## 1. 血统与来源

本模块是本系统（`Lifespan-Quant`）**新增核心模块**，父系统（`MarketLifespan-Quant`）无对应独立模块。

父系统中各 trigger 各自隐含结构判断逻辑，但分散且不统一。本系统将其提取为独立模块，作为 `filter` 和 `alpha/pas` 的共同前置层。

## 2. 模块定位

`structure` 是结构位识别引擎。

它负责在日线序列中识别支撑位、阻力位、波段高低点，并分类突破事件（BreakoutEvent），以统一合同语言向下游提供结构上下文。

本模块**不做触发信号判断**，只做结构事实识别。

## 3. 正式输入

1. 日线 `DataFrame`（来自 `market_base.duckdb`，已后复权）
2. 可选：`MalfContext`（用于背景感知的结构强度评估）

## 4. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `StructureSnapshot` | `dataclass`（冻结合同） | 传给 `filter` 和 `alpha/pas`，不落库 |

`StructureSnapshot` 包含：

- 当前支撑位 / 阻力位列表
- 最近波段高低点
- 当前 `BreakoutEvent`（若发生突破，否则为 `None`）
- 结构位强度评分（可选）

## 5. BreakoutType 枚举（冻结）

| 类型 | 含义 |
|---|---|
| `RESISTANCE_BREAK` | 向上突破阻力位 |
| `SUPPORT_BREAK` | 向下突破支撑位 |
| `FAILED_BREAK_UP` | 向上突破失败（回落） |
| `FAILED_BREAK_DOWN` | 向下突破失败（反弹） |
| `NO_BREAK` | 无有效突破 |

`BOF`（突破失败）信号直接依赖 `FAILED_BREAK_UP` 事件。

## 6. 模块边界

### 6.1 负责

1. 支撑位 / 阻力位识别（基于波段高低点）
2. 突破事件分类（BreakoutEvent + BreakoutType）
3. `StructureSnapshot` 快照生成
4. 结构位强度评估（可选字段）

### 6.2 不负责

1. `market_base` 的拥有与构建（属于 `data`）
2. MALF 三层矩阵计算（属于 `malf`）
3. 不利条件判断（属于 `filter`）
4. PAS trigger 触发（属于 `alpha/pas`）
5. 任何落库操作（`StructureSnapshot` 不落库，作为纯内存合同传递）

## 7. 铁律

1. `StructureSnapshot` 是纯内存合同，不落库，不持久化。
2. `BreakoutType` 枚举值冻结，不允许随意新增。
3. `structure` 模块必须先于 `alpha/pas` 运行，不允许绕过。
4. 结构位识别只基于价格序列事实，不引入主观判断或模型预测。

## 8. 成功标准

1. `StructureSnapshot` 合同冻结，含支撑位 / 阻力位 / BreakoutEvent 字段
2. `BreakoutType` 枚举覆盖 BOF 所需的 `FAILED_BREAK_UP` 事件
3. `filter` 和 `alpha/pas` 能正确消费 `StructureSnapshot` 并通过测试
4. 有单元测试覆盖典型突破 / 失败突破场景
