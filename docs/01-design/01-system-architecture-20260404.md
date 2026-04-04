# 系统架构设计 / 2026-04-04

> 取代 `01-system-architecture-20260331.md`。反映数据源口径更新、TDXQuant 不纳入、trade 层自实现决策、七库全持久化架构、backtrader 验证 oracle。

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
data → malf → structure → filter → alpha/pas → position → trade → system
```

**执行语义**：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价。

## 3. 模块边界

### 3.1 data

数据层采用**两步走架构**，**主线完全本地化（无网络依赖、无终端进程依赖）**。

#### 来源 A — TDX 导出 txt（主线，一次性全量灌入）

- 通达信软件导出的全历史 txt 文件（TSV 格式，每文件单只股票）
- 路径：`TDX_OFFLINE_DATA_ROOT` 环境变量（默认 `H:\tdx_offline_Data`）
- 同时灌入 L1（未复权 `raw_stock_daily`）和 L2（后复权 `stock_daily_adjusted`）
- **关键优势**：txt 文件包含通达信已计算好的完美复权价格，无需自行计算复权因子

#### 来源 B — TDX 本地 .day 文件（主线，日增量更新）

- 通达信软件自动同步的 `.day` 二进制文件（`vipdoc/{sh,sz,bj}/lday/`）
- 路径：`TDX_ROOT` 环境变量（默认 `H:\new_tdx64`）
- 解析器：mootdx（定位为 .day 二进制格式解析器，非数据来源）
- 回退策略：mootdx 失败时直接解析 `.day` 二进制（兜底）

#### 来源 C — TDX 本地 gbbq（主线，除权除息事件）

- 解密 `T0002/hq_cache/gbbq` 文件，解析 14 种企业行动事件
- 产出 `raw_xdxr_event`，用于增量模式下本地复权因子计算

#### 来源 D — TDXQuant 官方 API（已评估，不纳入）

- 通达信官方 Python 客户端 `tqcenter`，必须通达信终端进程在运行
- **不纳入系统设计**：主线管道为无人值守批量任务，不能依赖终端进程；且系统无实时行情消费模块
- `pyproject.toml` 不列入 `tqcenter`

#### 来源 E — tushare / baostock（辅助，仅审计）

- tushare `adj_factor` API：与本地复权因子做交叉审计
- baostock：第二校准源
- 不参与主线 L1/L2 构建

#### L1/L2 数据分层

| 层级 | 数据集 | 来源 |
| ---- | ------ | ---- |
| L1 | `raw_stock_daily` / `raw_index_daily` | txt（全量）/ .day（增量） |
| L1 | `raw_xdxr_event` | TDX gbbq（本地） |
| L1 | `raw_asset_snapshot` | tushare `stock_basic`（在线，低频，审计用） |
| L2 | `stock_daily_adjusted` | txt（全量）/ L1 本地计算（增量） |
| L2 | `stock_weekly_adjusted` / `stock_monthly_adjusted` | L2 聚合 |
| L2 | `index_daily` / `index_weekly` / `index_monthly` | L1 聚合 |

- 输入：`TDX_OFFLINE_DATA_ROOT`（txt 全量）+ `TDX_ROOT`（增量）+ `TUSHARE_TOKEN_PATH`（审计用，可选）
- 输出：`raw_market.duckdb`（L1）、`market_base.duckdb`（L2）

### 3.2 malf

- 职责：三层主轴计算（monthly_state_8 / weekly_flow_relation / surface_label）
- 输入：`market_base.duckdb`（月线、周线）
- 输出：`MalfContext` 合同对象、`malf.duckdb`（L3）

### 3.3 structure（新增）

- 职责：识别结构位（支撑/阻力/波段高低点），分类突破事件
- 输入：日线 DataFrame
- 输出：`StructureSnapshot` 合同对象，落入 `structure.duckdb`（L3，按日按股增量追加）
- 依赖：`core`（新增 duckdb 写入职责）

### 3.4 filter（新增）

- 职责：不利市场条件过滤，"不做"语言正式化（5 类 adverse conditions）
- 输入：日线数据 + `MalfContext` + 最近支撑/阻力价格（float）
- 输出：`AdverseConditionResult`，落入 `filter.duckdb`（L3，按日按股增量追加）
- 依赖：`core` + `malf`（新增 duckdb 写入职责）

### 3.5 alpha/pas

- 职责：五 trigger 探测（BOF/BPB/PB/TST/CPB）、16 格验证框架、第一 PB 追踪
- 输入：日线数据（通过过滤器的股票）+ `StructureSnapshot`
- 输出：`PasSignal` 列表，落入 `research_lab.duckdb`（L3，持久化，按信号增量追加）

### 3.6 position

- 职责：1R 头寸规划、退出合同
- 输入：`PasSignal`
- 输出：`PositionPlan` + `PositionExitPlan`

### 3.7 trade

- 职责：交易管理模板（TradeManager 5 阶段状态机）+ 执行引擎（BacktestEngine + Broker）
- 输入：`PositionPlan` + 每日 K 线
- 输出：`TradeRecord`，落入 `trade_runtime.duckdb`（L4，持久化，按交易增量追加）
- **实现方式**：BacktestEngine + Broker 自实现（~450 行），参考 backtrader 设计理念但不引入 backtrader 核心依赖
- **验证 oracle**：backtrader 列入 `[dev]` 依赖，用于独立对照验证自实现引擎的正确性
- **实盘预留**：`TradeBrokerAdapter Protocol` 接口已定义，未来可接 easytrader

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
| 交易管理模板 | 有基础合同，无生命周期管理器 | `TradeManager` 5 阶段状态机 |
| 数据灌入 | mootdx .day 逐日追补 | TDX txt 一次性全量灌入 + .day 增量 |
| 回测引擎 | 自实现 | 自实现（参考 backtrader 理念，不引入包依赖） |
| 包名 | `mlq` | `lq` |

## 5. 铁律

1. 模块间只传**结果合同**（`dataclass` 对象），不传内部中间特征
2. `structure` 先于 `alpha/pas`，不利条件过滤先于 trigger 探测
3. `BPB` / `CPB` 均为 REJECTED：三段回测未证明正收益，`system` 层禁止调用
4. `TST` 为 CONDITIONAL（辅策略，2020 后持续正收益）；`PB` 为 CONDITIONAL（边缘降权）
5. 路径/密钥禁止硬编码，统一经 `core/paths.py` 注入
6. **主线数据完全本地化**：不依赖网络 API 或终端进程
7. **不整体依赖外部回测框架**：BacktestEngine 自实现，保持架构自主权

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-03-31 | v1 | 初版系统架构 |
| 2026-04-04 | v2 | data §3.1 两步走架构；TDXQuant 不纳入；structure/filter 新增持久化库；七库全持久化；trade 自实现 + backtrader oracle；铁律增补6/7 |
