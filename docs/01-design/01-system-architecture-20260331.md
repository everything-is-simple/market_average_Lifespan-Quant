# 系统架构设计 / 2026-03-31

## 1. 系统定位

`Lifespan-Quant` 是 `MarketLifespan-Quant`（父系统）的重构版本，面向 A 股日线频率的市场平均寿命量化研究。

它在继承父系统核心能力的基础上，重点实现了以下优先级 A 研究方向：

| 优先级 | 方向 | 当前状态 |
|--------|------|---------|
| A1 | 结构位统一合同 | 已实现（`structure` 模块） |
| A2 | 突破家族语义 | 已实现（`structure.detector` + `BreakoutEvent`） |
| A3 | 二次入场 / 第一 PB 追踪 | 已实现（`alpha/pas` 中 `pb_sequence_number`） |
| A4 | 不利市场条件过滤器 | 已实现（`filter` 模块） |
| A5 | 交易管理模板 | 已实现（`trade.management` 模块） |

## 2. 主线链路

```
data → malf → structure(filter) → alpha/pas → position → trade → system
```

**执行语义**：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价。

## 3. 模块边界

### 3.1 data
- 职责：baostock 原始数据采集、复权价计算、均线/量比计算、落盘
- 输入：baostock API
- 输出：`raw_market.duckdb`（L1）、`market_base.duckdb`（L2）

### 3.2 malf
- 职责：三层主轴计算（monthly_state_8 / weekly_flow_relation / surface_label）
- 输入：`market_base.duckdb`（月线、周线）
- 输出：`MalfContext` 合同对象、`malf.duckdb`（L3）

### 3.3 structure（新增）
- 职责：识别结构位（支撑/阻力/波段高低点），分类突破事件
- 输入：日线 DataFrame
- 输出：`StructureSnapshot` 合同对象（不落库，作为 filter/alpha 的前置输入）

### 3.4 filter（新增）
- 职责：不利市场条件过滤，"不做"语言正式化
- 输入：日线数据 + `MalfContext` + `StructureSnapshot`
- 输出：`AdverseConditionResult`（无不利条件才允许进入探测）

### 3.5 alpha/pas
- 职责：五 trigger 探测（BOF/BPB/PB/TST/CPB）、16 格验证框架、第一 PB 追踪
- 输入：日线数据（通过过滤器的股票）
- 输出：`PasSignal` 列表，落入 `research_lab.duckdb`（L3）

### 3.6 position
- 职责：1R 头寸规划、退出合同
- 输入：`PasSignal`
- 输出：`PositionPlan` + `PositionExitPlan`

### 3.7 trade
- 职责：交易管理模板（初始止损 → 保护性提损 → 半仓止盈 → 跟踪 runner → 时间止损）
- 输入：`PositionPlan` + 每日 K 线
- 输出：`TradeRecord`，落入 `trade_runtime.duckdb`（L4）

### 3.8 system
- 职责：主线编排、每日信号扫描、批量回测
- 输入：所有模块
- 输出：`SystemRunSummary`

## 4. 与父系统的核心差异

| 能力 | 父系统（MarketLifespan-Quant） | 本系统（Lifespan-Quant） |
|------|-------------------------------|-------------------------|
| 结构位 | 局部 trigger 内部语义，未统一 | 独立 `structure` 模块，统一合同 |
| 突破语义 | 各 trigger 自定义 | `BreakoutType` 枚举统一分类 |
| 第一 PB 追踪 | 未实现 | `pb_sequence_number` 字段 |
| 不利条件过滤 | 部分（月线背景） | 独立 `filter` 模块，五类条件 |
| 交易管理模板 | 有基础合同，无生命周期管理器 | `TradeManager` 状态机 |
| 包名 | `mlq` | `lq` |

## 5. 铁律

1. 模块间只传**结果合同**（`dataclass` 对象），不传内部中间特征
2. `structure` 先于 `alpha/pas`，不利条件过滤先于 trigger 探测
3. `BPB` 保持拒绝主线（三年验证不通过），代码存留但 `system` 层不启用
4. `TST` / `CPB` 代码存在，业务上标记为 `PENDING`（待独立验证）
5. 路径/密钥禁止硬编码，统一经 `core/paths.py` 注入
