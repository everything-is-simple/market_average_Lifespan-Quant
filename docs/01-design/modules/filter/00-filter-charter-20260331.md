# filter 模块章程 / 2026-03-31

## 1. 血统与来源

本模块是本系统（`Lifespan-Quant`）**新增核心模块**，父系统（`MarketLifespan-Quant`）无对应独立模块。

父系统在 MALF 月线背景处有隐式过滤，但未形成显式独立层。本系统将"不做"语言正式化，作为 `alpha/pas` 之前的强制准入门槛。

## 2. 模块定位

`filter` 是不利市场条件过滤层。

它负责在进入 trigger 探测之前，对候选股票施加五类不利条件检查。
任何一类条件触发，该股票当日不进入 alpha/pas 探测。

**核心理念**：先排除"不该做"，再找"能做"。

## 3. 正式输入

1. 日线 `DataFrame`（来自 `market_base.duckdb`）
2. `MalfContext`（来自 `malf` 模块，月线八态和周线顺逆）
3. `StructureSnapshot`（来自 `structure` 模块，结构位上下文）

## 4. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `AdverseConditionResult` | `dataclass`（冻结合同） | 传给 `alpha/pas`，not_filtered 才允许进入 trigger 探测 |

`AdverseConditionResult` 包含：

- `is_filtered`：是否被过滤（True = 不进入探测）
- `triggered_conditions`：触发的不利条件列表
- `filter_reason`：可读原因说明

## 5. 五类不利条件（冻结）

| 编号 | 条件 | 触发规则 |
|---|---|---|
| F1 | 月线熊市且周线逆势 | `monthly_state` 为 BEAR_* 且 `weekly_flow = against_flow` |
| F2 | 近期破位 | `StructureSnapshot` 包含 `SUPPORT_BREAK` 事件且未确认反弹 |
| F3 | 成交量萎缩 | 近 N 日成交量均值低于长期均值的阈值比例 |
| F4 | 价格处于阻力密集区 | 当前价格在强阻力位 ±X% 范围内 |
| F5 | 近期连续跌停 | 近 N 日内出现连续跌停板 |

具体阈值在 `filter/constants.py` 中定义，不硬编码在逻辑层。

## 6. 模块边界

### 6.1 负责

1. 五类不利条件的独立判断逻辑
2. `AdverseConditionResult` 合同生成
3. 多条件串联与短路逻辑（任一触发即过滤）
4. 过滤原因的可读记录

### 6.2 不负责

1. `market_base` 的拥有与构建（属于 `data`）
2. MALF 计算（属于 `malf`）
3. 结构位识别（属于 `structure`）
4. PAS trigger 探测（属于 `alpha/pas`）
5. 任何落库操作（`AdverseConditionResult` 不落库）

## 7. 铁律

1. `filter` 必须先于 `alpha/pas` 运行，不允许绕过。
2. 五类条件编号（F1-F5）冻结，新增条件需更新章程，不允许悄悄在代码里加判断。
3. `AdverseConditionResult` 是纯内存合同，不落库。
4. 过滤阈值统一在 `filter/constants.py` 管理，不允许在判断逻辑中出现魔法数字。

## 8. 成功标准

1. `AdverseConditionResult` 合同冻结
2. 五类不利条件各有独立函数和单元测试
3. `filter` 过滤后，通过率有可观测的统计指标（不能全过也不能全拒）
4. `alpha/pas` 调用时能正确接收过滤结果并跳过被过滤股票
