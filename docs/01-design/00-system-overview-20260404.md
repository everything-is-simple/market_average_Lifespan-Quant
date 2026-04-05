# Lifespan-Quant 系统概述 / 2026-04-04

> 取代 `00-system-overview-20260401.md`。反映五目录路径修正、数据源口径更新、开源选型终裁。

## 1. 系统定位

`Lifespan-Quant` 是面向中国 A 股的**市场平均寿命量化系统（第二代重构版）**。

- 个人项目，单开发者
- 执行模型：增量交付，每步产出可独立验证的交付物
- 文档服务实现，不追求文档完美

---

## 2. 三代血统

```
爷爷系统（EmotionQuant-gamma）
    │  2026-03 重构
    ↓
父系统（MarketLifespan-Quant）
    │  2026-03 末 重构
    ↓
本系统（Lifespan-Quant）
```

### 2.1 从爷爷系统继承

| 继承项 | 说明 |
|---|---|
| 执行语义 | `signal_date=T`，`execute_date=T+1`，成交价=`T+1` 开盘价 |
| 合同传递 | 模块间只传结果合同（dataclass/pydantic），不传内部中间特征 |
| 代码规范 | 注释中文、函数 `snake_case`、类 `PascalCase` |
| ID 构造规则 | signal_id / order_id 格式规范 |

### 2.2 从父系统继承

| 继承项 | 说明 |
|---|---|
| 5 目录纪律 | repo / data / temp / report / validated |
| 5 数据库架构 | raw_market / market_base / research_lab / malf / trade_runtime |
| MALF 三层主轴 | monthly_state_8 / weekly_flow_relation / pas_context |
| PAS 触发器治理 | BOF/PB 可用，BPB 拒绝，TST/CPB 待验证 |
| 配置机制 | 纯 env var 注入（去掉 pydantic） |
| 数据源 | 通达信本地文件（主线）+ tushare/baostock（仅审计） |

### 2.3 本系统原创新增

| 新增项 | 优先级 | 说明 |
|---|---|---|
| **structure 模块** | A1 | 统一结构位语言：波段高低点、支撑阻力位、突破事件分类 |
| **filter 模块** | A4 | 不利市场条件过滤器：5 类条件独立检测 |
| **TradeManager 状态机** | A5 | 入场后交易生命周期 5 阶段正式化 |
| **core 枚举集中化** | — | 所有跨模块枚举统一在 core.contracts |
| **TDX txt 全量灌入** | — | 通达信导出 txt 一次性灌入 L1/L2，替代逐日追补 |

---

## 3. 九模块架构

### 3.1 模块全图

```
┌──────────────────────────────────────────────────────────────────┐
│  core（合同基础层）                                               │
│  contracts + paths + 枚举 + 常量                                  │
│  ← 所有模块依赖，不参与数据流水线                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ 所有模块 import

          主线数据流水线（从上到下）
          ┌────────┐   ┌─────────┐   ┌─────────────┐
          │  data  │   │  malf   │   │  structure  │  ← 本系统新增
          │数据底座│   │三层背景 │   │ 结构位语言  │
          └───┬────┘   └────┬────┘   └──────┬──────┘
              └─────────────┼───────────────┘
                            ↓
                    ┌──────────────┐
                    │   filter     │  ← 本系统新增
                    │ 不利条件过滤 │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  alpha/pas   │
                    │ PAS 触发探测 │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  position    │
                    │  仓位规划    │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   trade      │
                    │ 执行/回测层  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   system     │
                    │  编排总控    │
                    └──────────────┘
```

### 3.2 模块职责表

| 模块 | 职责 | 数据库归属 |
|---|---|---|
| `core` | 公共类型、路径合同、跨模块枚举、常量 | 无（纯合同层） |
| `data` | 市场数据采集（TDX 本地文件）、清洗、落盘、增量更新 | raw_market / market_base |
| `malf` | 市场平均寿命框架：monthly_state_8 / weekly_flow / pas_context | malf |
| `structure` | 统一结构位合同：波段高低点、支撑阻力位、突破分类；结果按日按股持久化 | structure |
| `filter` | 不利市场条件过滤器：5 类条件检测；结果按日按股持久化 | filter |
| `alpha/pas` | 五触发器：BOF/BPB/PB/TST/CPB + 16 格验证框架 | research_lab |
| `position` | 1R 风险单位、头寸规模、退出合同 | research_lab |
| `trade` | 交易管理模板、执行 runtime、BacktestEngine（自实现） | trade_runtime |
| `system` | 编排总控、回测、治理检查、三级 runner | trade_runtime |

### 3.3 模块依赖矩阵

```
core（基础层，所有模块依赖）
  ↑
data   → core
malf   → core, data
structure → core
filter → core, malf
alpha  → core, data, malf, structure, filter
position → core, data, alpha
trade  → core, data, position
system → core, data, malf, alpha, position, trade
```

**禁止反向依赖**：下游模块不得 import 上游模块的内部实现。

---

## 4. 主线链路

```
data → malf → structure → filter → alpha/pas → position → trade → system
```

**执行语义**：`signal_date=T`，`execute_date=T+1`，成交价=`T+1` 开盘价。

### 4.1 与父系统的主线差异

| 父系统（MarketLifespan） | 本系统（Lifespan-Quant） |
|---|---|
| data → malf → alpha/pas → position → trade → system | data → malf → **structure → filter** → alpha/pas → position → trade → system |

**新增两层**：
- `structure`：在 malf 之后，为 filter 和 alpha 提供统一的结构位语言
- `filter`：在 alpha 之前，先通过不利条件过滤才进入 trigger 检测

---

## 5. 五目录纪律

| 目录 | 实际路径 | 用途 | 禁止存放 |
|---|---|---|---|
| repo | `H:\Lifespan-Quant` | 代码、文档、测试、治理 | 数据库、日志、缓存 |
| data | `H:\Lifespan-Quant-data` | 正式七数据库（全持久化 DuckDB） | 代码、临时文件 |
| temp | `H:\Lifespan-temp` | 临时产物、pytest、benchmark | 正式代码/数据库 |
| report | `H:\Lifespan-Quant-report` | 人读报告、图表、导出物 | 代码 |
| validated | `H:\Lifespan-Quant-Validated` | 跨版本验证资产快照 | 普通临时产物 |

---

## 6. 七数据库架构（全持久化）

**核心原则**：历史一旦发生就是永恒的瞬间——绝不重算。磁盘空间换内存，小批量断点续传。

| # | 数据库 | 路径 | Owner | 内容 | 增量策略 |
|---|---|---|---|---|---|
| L1 | raw_market | `data/raw/` | data | TDX 导出 txt（全量）+ .day（增量）+ gbbq | 按日追加 |
| L2 | market_base | `data/base/` | data | 复权价、周月线聚合、均线、量比 | 只算新日期 |
| L3 | malf | `data/malf/` | malf | MALF 三层主轴快照 | 新月/新周 |
| L3 | structure | `data/structure/` | structure | 结构位快照（支撑/阻力/突破） | 按日按股追加 |
| L3 | filter | `data/filter/` | filter | 不利条件检查结果 | 按日按股追加 |
| L3 | research_lab | `data/research/` | alpha+position | PAS 信号 + 仓位计划 | 按信号追加 |
| L4 | trade_runtime | `data/trade/` | trade/system | 交易记录 + 权益曲线 | 按交易追加 |

**内存控制**：按日期区间分批处理，每批读→算→写→释放，checkpoint 标记完成，中断后从断点恢复。
**参数变更**：每行带 `config_hash`，参数冻结则跳过已有数据；参数变更则 selective rebuild 受影响行。

### 6.1 设计决策备忘：七库的来由（空间换时间）

> 本节记录 2026-04-05 的架构审查结论，供后续开发者和 AI 代理理解"为什么"。

**硬件约束**：个人项目，单机 AMD 5800H / **32G 内存** / 2×512G SSD。32G 是硬上限——全市场 5000 只股票 × 10 年历史 × 多层特征若不分批落盘，单次主线回测必然触发内存耗尽和系统换页，性能断崖。

**父系统（v0.01）的真实教训**：

v0.01 的五个库技术上全是磁盘文件，但 `research_lab` 和 `trade_runtime` 是**名义持久化、行为临时化**——每次回测生成新 `run_id`，旧结果积累但不复用，下次回测仍从 `malf` 之后全链重算。后果：
- 1000 只股票 × 10 年全链回测耗时 **5–7 小时**
- 中间层（PAS 信号、仓位计划）反复计算后丢弃，毫无积累

v0.1 专门新增了 `structure` 和 `filter` 两层，如果不给这两层建持久化库，每次主线回测就要重算这两层昂贵的历史扫描，完全抵消父系统三个磁盘库的积累价值。

**七库的空间换时间逻辑**：

| 阶段 | 如果不持久化，每次重算什么 | 代价 |
|---|---|---|
| raw→base | 重解析 TDX .day 二进制 + 重跑复权因子链 | 高（gbbq 累乘路径敏感） |
| malf | 重跑六层流水线（全市场一遍 8–10 小时） | 极高 |
| structure | 重扫历史 OHLCV 识别 pivot 点 / 支撑阻力位 | 高 |
| filter | 重对每股每日做五类不利条件检查 | 中 |
| research_lab | 重跑 trigger 探测（BOF/TST/PB 历史信号扫描） | 高 |
| trade_runtime | 重跑交易模拟、R 倍数计算、权益曲线 | 中 |

**`config_hash` 增量跳过机制**：每行携带输入参数的哈希。同一 `(code, date, config_hash)` 组合已存在 → 直接跳过，不重算。参数变更 → selective rebuild 只重算受影响行。

**理想运行模式**：七库首次填充完成后，日常增量更新只触碰最新日期的行。主线回测直接读库，不触发任何已有历史行的重计算。普通个人硬件 = 可接受的量化研究效率。

---

## 7. PAS 触发器治理状态

| 触发器 | 状态 | 说明 |
|---|---|---|
| BOF | **MAINLINE** | 主策略，保留确定（保留段胜率 56.5%，净收益 511万） |
| TST | CONDITIONAL | 辅策略，保留（2020 后持续正收益，保留段 108万） |
| PB | CONDITIONAL | 边缘策略，降权保留（量大质弱，保留段仅 15万） |
| BPB | **REJECTED** | 永久拒绝，system 层禁止调用 |
| CPB | **REJECTED** | 剔除冻结（最弱，保留段 -33万） |

---

## 8. 与三代系统的核心差异

### 8.1 与爷爷系统（EQ-gamma）的差异

| 差异点 | EQ-gamma | Lifespan-Quant |
|---|---|---|
| 模块数 | 6 个 | 9 个 |
| 数据源 | TuShare API（在线依赖） | 通达信本地文件（离线主线） |
| 数据库 | 单库 L1-L4 分层 | 5 库独立文件 |
| 配置 | pydantic Settings | 纯 env var |
| 结构位 | 无独立层 | structure 模块 |
| 过滤器 | 无独立层 | filter 模块 |
| 交易管理 | Broker 简单状态机 | TradeManager 5 阶段 |
| 回测引擎 | 自实现 Cerebro-like | 自实现轻量 BacktestEngine |

### 8.2 与父系统（MarketLifespan）的差异

| 差异点 | MarketLifespan | Lifespan-Quant |
|---|---|---|
| 模块数 | 7 个 | 9 个（+structure/filter） |
| 主线链路 | 无 structure/filter | 有 structure/filter |
| 结构位语言 | 内嵌在 alpha/pas | 独立 structure 模块 |
| 不利条件过滤 | 内嵌在 alpha/pas | 独立 filter 模块 |
| 交易管理 | 执行层 | +TradeManager 5 阶段状态机 |
| core 枚举 | 各模块自定义 | 统一在 core.contracts |
| 数据灌入 | mootdx .day 逐日追补 | TDX txt 一次性全量灌入 + .day 增量 |
| 执行纪律 | 四件套（card/evidence/record/conclusion） | 简化版增量交付 |

---

## 9. 开源选型决策（2026-04-04 终裁）

### 9.1 选型原则

> 系统的原创价值在于 **malf + structure + filter + alpha/pas + TradeManager** 五层理论实现。
> 数据采集和回测引擎是"管道"，不是价值核心。对管道层：
> - 能用**成熟的上市公司产品**（通达信）就用
> - 但不为了引入某个框架**牺牲系统架构自主权**

### 9.2 data 层：通达信本地文件主线，TDXQuant 备选预留

| 方案 | 结论 | 理由 |
|---|---|---|
| **TDX 本地文件（txt 全量 + .day 增量）** | ✅ 主线 | 完全离线、无终端依赖、已有成熟管道、精度与通达信软件一致 |
| **TDXQuant 官方 API (`tqcenter`)** | 📌 备选预留 | 官方维护、支持 VSCode/任意 IDE、内置复权+行情+财务+交易函数；需 TDX 终端进程在运行 |
| **mootdx** | ✅ 保留 | 定位为 .day 二进制格式解析器（非数据来源），格式20年稳定 |
| **tushare** | ⚠️ 仅审计 | 个人项目，HTTP API，仅用于复权因子交叉校验 |
| **baostock** | ⚠️ 仅审计 | 个人项目，仅用于第二校准源 |

**关键澄清**：mootdx 不是"数据来源"，是"格式解析器"。系统的数据来源始终是通达信本地文件——上市公司（财富趋势）维护，20年格式稳定。mootdx 只是读取这些文件的 Python 工具，即使 mootdx 停更，.day 二进制格式有兜底解析器。

**TDXQuant 评估（基于官方文档 help.tdx.com.cn/quant）**：

TDXQuant（`tqcenter`）是通达信官方 Python 量化 API，由深圳市财富趋势科技股份有限公司研发。它是标准 Python 包（`from tqcenter import tq`），**完全支持在 VSCode / 任意 IDE 中运行**，不限制在通达信自己的编程环境。前提条件：通达信终端进程需在运行（终端常开可以接受）。

API 能力概览：

| 能力 | API | 本系统潜在用途 |
|---|---|---|
| 历史 K 线 + 内置复权 | `tq.get_market_data()` | data 层：可作为 L2 复权数据的官方交叉校验源（代替 tushare） |
| 板块成份股 | `tq.get_stock_list_in_sector()` | alpha 层：行业轮动 / 概念筛选 |
| 自定义板块回写 | `tq.send_user_block()` | system 层：把 PAS 信号结果推回通达信客户端显示 |
| 实时行情订阅 | `tq.subscribe()` | 未来：实时监控模块（当前无消费方） |
| 交易函数（买/卖） | 交易函数接口 | trade 层：未来实盘对接（优于 easytrader，因为是官方接口） |
| 回测 + 模拟交易 | 内置回测引擎 | 可作为 BacktestEngine 的第二验证 oracle |
| 财务数据 | `tq.get_financial_data()` | 未来：基本面筛选因子 |

**当前决策（v0.1）**：

1. **主线不变**：TDX 本地文件（txt 全量 + .day 增量）仍为数据主管道，因为已完备且完全离线
2. **备选预留**：`tqcenter` 列入 `pyproject.toml` 的 `[project.optional-dependencies]` 下的 `tdx` 组，不进核心依赖
3. **近期可探索**：用 `tq.get_market_data()` 作为 L2 复权数据的官方交叉校验源（代替 tushare/baostock）
4. **未来实盘**：交易函数可作为 `TradeBrokerAdapter` 的官方实现（优于 easytrader）
5. **不用其回测引擎**：本系统 BacktestEngine 自实现，保持架构自主权

### 9.3 trade 层：BacktestEngine 自实现，不整体依赖外部框架

| 框架 | Stars | 结论 | 理由 |
|---|---|---|---|
| **qlib**（Microsoft） | 15k | ❌ 不引入 | ML/AI 导向，Strategy 层假设"每日根据因子重新分配组合"——与 TradeManager 5阶段逐股状态机根本不兼容 |
| **backtrader** | 14k | ✅ `[dev]` 验证 oracle | 不作为核心依赖；列入 `[dev]` 依赖，用于独立对照验证自实现引擎的 PnL/R-multiple 正确性 |
| **vectorbt** | 17k | ❌ 不引入 | 向量化范式，BOF 交易需要逐股独立状态跟踪，不适合纯向量化 |
| **backtesting.py** | 1.8k | 📌 备选 | 轻量单文件库，侵入性最小；如果自实现遇到困难可作为底层引入 |
| **easytrader** | — | ✅ 实盘预留 | 标准化券商适配器；TDXQuant 交易函数也可作为官方替代方案 |

**核心决策**：trade 模块已完成最难的部分（TradeManager 5阶段状态机）。缺少的 BacktestEngine 是一个 ~400 行的日历循环驱动器——为此引入 qlib（15k 行 + ML 依赖）或 backtrader（Cerebro 全家桶）得不偿失。

**backtrader 验证 oracle**：backtrader 列入 `[dev]` 依赖，不进核心依赖。用相同输入数据+相同逻辑跑 backtrader，比对两者的 PnL、胜率、最大回撤，若误差在可接受范围内则验证通过。验证脚本放 `tests/integration/trade/`。

**自实现范围**（参考 backtrader 设计理念，不引入 backtrader 包依赖）：
- `BacktestEngine`：日历循环 + 上下游协调（~200 行）
- `Broker`：撮合 + 持仓管理 + A 股成本模型（~200 行）
- `SimulatedBrokerAdapter`：纸交易适配器（~50 行）
- 总计 ~450 行，无外部框架依赖

### 9.4 边界风险警告

| 风险 | 说明 | 防线 |
|---|---|---|
| mootdx 停更 | .day 解析器无人维护 | 已有二进制兜底解析器（`tdx_local.py`），格式20年稳定 |
| TDX 格式变更 | 通达信改变 .day 文件格式 | 概率极低（20年未变）；txt 导出格式更稳定 |
| TDXQuant 终端依赖 | `tqcenter` 需 TDX 终端进程在运行 | 终端常开可接受；主线仍为本地文件（离线兜底） |
| BacktestEngine 自实现 bug | 撮合逻辑、成本计算有误 | backtrader 作为独立验证 oracle（`[dev]` 依赖）；单元测试覆盖5类退出场景 |
| 实盘对接时机 | 过早实盘 = 真金白银烧 bug | `TradeBrokerAdapter Protocol` 已预留，但不在 v0.1 实施 |
| qlib/backtrader 后悔 | 将来发现确实需要 | 模块边界清晰，trade 层可随时替换底层引擎；`PositionPlan → TradeRecord` 合同不变 |

---

## 10. 设计文档索引

| 模块 | 章程 | 设计文档 |
|---|---|---|
| core | `modules/core/00-core-charter-20260401.md` | contracts设计 + paths设计 + checkpoint设计 |
| data | `modules/data/00-data-charter-20260404.md` | L2 后复权设计 + TDX txt 灌入设计 |
| malf | `modules/malf/00-malf-charter-20260331.md` | 三层主轴冻结设计（6个子文档） |
| structure | `modules/structure/00-structure-charter-20260401.md` | detector设计 |
| filter | `modules/filter/00-filter-charter-20260401.md` | adverse conditions设计 |
| alpha | `modules/alpha/00-alpha-charter-20260331.md` | PAS 五触发器 + 16格准入 + 输出治理 |
| position | `modules/position/00-position-charter-20260331.md` | sizing家族设计 + partial exit设计 |
| trade | `modules/trade/00-trade-charter-20260404.md` | broker/engine设计 + runtime schema设计 |
| system | `modules/system/00-system-charter-20260331.md` | orchestration设计 + governance设计 |

---

## 11. 铁律总览

1. **主线链路冻结**：`data → malf → structure → filter → alpha/pas → position → trade → system`
2. **执行语义固定**：`signal_date=T`，`execute_date=T+1`，成交价=`T+1` 开盘价
3. **模块间只传结果合同**，不传内部中间特征
4. **路径/密钥禁止硬编码**，统一经 `core/paths.py` 注入或环境变量
5. **BPB 永久拒绝**：system 层任何路径不得调用 BPB 触发器
6. **五目录纪律强制**：代码不混数据，临时不混正式；data 目录放七个持久化库
7. **枚举格式冻结**：已发布枚举值不允许变更
8. **主线数据完全本地化**：L1/L2 数据不依赖任何网络 API 或终端进程
9. **不整体依赖外部回测框架**：BacktestEngine 自实现，保持系统架构自主权；设计理念可借鉴，包依赖不引入

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-04-01 | v1 | 初版系统概述 |
| 2026-04-04 | v2 | 路径修正；数据源口径更新；TDXQuant 不纳入；§9 开源选型决策；七库全持久化架构（新增 structure.duckdb + filter.duckdb）；backtrader 验证 oracle；铁律增补8/9/10 |
