# Lifespan-Quant 系统概述 / 2026-04-01

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
| 数据源 | mootdx 本地通达信（主）+ tushare（审计） |

### 2.3 本系统原创新增

| 新增项 | 优先级 | 说明 |
|---|---|---|
| **structure 模块** | A1 | 统一结构位语言：波段高低点、支撑阻力位、突破事件分类 |
| **filter 模块** | A4 | 不利市场条件过滤器：5 类条件独立检测 |
| **TradeManager 状态机** | A5 | 入场后交易生命周期 5 阶段正式化 |
| **core 枚举集中化** | — | 所有跨模块枚举统一在 core.contracts |

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
| `data` | 市场数据采集（mootdx）、清洗、落盘、增量更新 | raw_market / market_base |
| `malf` | 市场平均寿命框架：monthly_state_8 / weekly_flow / pas_context | malf |
| `structure` | 统一结构位合同：波段高低点、支撑阻力位、突破分类 | 无（纯计算层） |
| `filter` | 不利市场条件过滤器：5 类条件检测 | 无（纯计算层） |
| `alpha/pas` | 五触发器：BOF/BPB/PB/TST/CPB + 16 格验证框架 | research_lab |
| `position` | 1R 风险单位、头寸规模、退出合同 | research_lab |
| `trade` | 交易管理模板、执行 runtime、TradeManager 状态机 | trade_runtime |
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

| 目录 | 用途 | 禁止存放 |
|---|---|---|
| `G:\Lifespan-Quant` | 代码、文档、测试、治理 | 数据库、日志、缓存 |
| `G:\Lifespan-data` | 正式数据库与数据产物 | 代码、临时文件 |
| `G:\Lifespan-temp` | 临时产物、pytest、benchmark | 正式代码/数据库 |
| `G:\Lifespan-report` | 人读报告、图表、导出物 | 代码 |
| `G:\Lifespan-Validated` | 跨版本验证资产快照 | 普通临时产物 |

---

## 6. 五数据库架构

| 数据库 | 路径 | Owner | 内容 |
|---|---|---|---|
| raw_market | Lifespan-data/raw/ | data | mootdx 本地 .day 文件 + gbbq 除权除息 |
| market_base | Lifespan-data/base/ | data | 复权价、均线、量比 |
| research_lab | Lifespan-data/research/ | alpha | PAS 信号、选中 trace |
| malf | Lifespan-data/malf/ | malf | MALF 三层主轴输出 |
| trade_runtime | Lifespan-data/trade/ | trade/system | 执行合同、回测结果 |

---

## 7. PAS 触发器治理状态

| 触发器 | 状态 | 说明 |
|---|---|---|
| BOF | MAINLINE | 主线可用，已验证 |
| PB | CONDITIONAL | 条件格准入，已验证 |
| BPB | **REJECTED** | 永久拒绝，system 层禁止调用 |
| TST | PENDING | 待独立验证 |
| CPB | PENDING | 待独立验证 |

---

## 8. 与三代系统的核心差异

### 8.1 与爷爷系统（EQ-gamma）的差异

| 差异点 | EQ-gamma | Lifespan-Quant |
|---|---|---|
| 模块数 | 6 个 | 9 个 |
| 数据源 | TuShare API | mootdx 本地通达信 |
| 数据库 | 单库 L1-L4 分层 | 5 库独立文件 |
| 配置 | pydantic Settings | 纯 env var |
| 结构位 | 无独立层 | structure 模块 |
| 过滤器 | 无独立层 | filter 模块 |
| 交易管理 | Broker 简单状态机 | TradeManager 5 阶段 |

### 8.2 与父系统（MarketLifespan）的差异

| 差异点 | MarketLifespan | Lifespan-Quant |
|---|---|---|
| 模块数 | 7 个 | 9 个（+structure/filter） |
| 主线链路 | 无 structure/filter | 有 structure/filter |
| 结构位语言 | 内嵌在 alpha/pas | 独立 structure 模块 |
| 不利条件过滤 | 内嵌在 alpha/pas | 独立 filter 模块 |
| 交易管理 | 执行层 | +TradeManager 5 阶段状态机 |
| core 枚举 | 各模块自定义 | 统一在 core.contracts |
| 执行纪律 | 四件套（card/evidence/record/conclusion） | 简化版增量交付 |

---

## 9. 设计文档索引

| 模块 | 章程 | 设计文档 |
|---|---|---|
| core | `docs/01-design/modules/core/00-core-charter-20260401.md` | contracts设计 + paths设计 |
| data | `docs/01-design/modules/data/00-data-charter-*.md` | — |
| malf | `docs/01-design/modules/malf/00-malf-charter-*.md` | — |
| structure | `docs/01-design/modules/structure/00-structure-charter-20260401.md` | detector设计 |
| filter | `docs/01-design/modules/filter/00-filter-charter-20260401.md` | adverse conditions设计 |
| alpha | `docs/01-design/modules/alpha/00-alpha-charter-*.md` | — |
| position | `docs/01-design/modules/position/00-position-charter-*.md` | — |
| trade | `docs/01-design/modules/trade/00-trade-charter-*.md` | runtime schema设计 |
| system | `docs/01-design/modules/system/00-system-charter-20260331.md` | orchestration设计 + governance设计 |

---

## 10. 铁律总览

1. **主线链路冻结**：`data → malf → structure → filter → alpha/pas → position → trade → system`
2. **执行语义固定**：`signal_date=T`，`execute_date=T+1`，成交价=`T+1` 开盘价
3. **模块间只传结果合同**，不传内部中间特征
4. **路径/密钥禁止硬编码**，统一经 `core/paths.py` 注入或环境变量
5. **BPB 永久拒绝**：system 层任何路径不得调用 BPB 触发器
6. **五目录纪律强制**：代码不混数据，临时不混正式
7. **枚举格式冻结**：已发布枚举值不允许变更
