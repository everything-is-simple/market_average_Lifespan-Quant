# Lifespan-Quant

`Lifespan-Quant` 是面向中国 A 股的**市场平均寿命量化系统（第二代重构版）**。

---

## 三代血统

```
爷爷系统（EmotionQuant-gamma）→ 父系统（MarketLifespan-Quant）→ 本系统
```

| 继承来源 | 继承内容 |
|----------|----------|
| 爷爷系统 | 执行语义（T+1 Open）、合同传递模式、代码规范 |
| 父系统 | 5 目录纪律、数据库架构（本系统扩展为七库全持久化）、MALF 三层主轴、PAS 触发器治理、mootdx 数据源 |
| **本系统新增** | `structure` 模块（结构位语言）、`filter` 模块（不利条件过滤）、`TradeManager` 5 阶段状态机 |

---

## 九模块架构

| 模块 | 职责 | 数据库 |
|------|------|--------|
| `core` | 公共类型、路径合同、跨模块枚举 | 无 |
| `data` | 市场数据采集（mootdx）、清洗、落盘 | raw_market / market_base |
| `malf` | 市场平均寿命框架：monthly_state_8 / weekly_flow | malf |
| `structure` | 统一结构位合同：波段高低点、突破分类 **（新增）** | structure |
| `filter` | 不利市场条件过滤器：5 类条件检测 **（新增）** | filter |
| `alpha/pas` | 五触发器：BOF/BPB/PB/TST/CPB + 16 格验证 | research_lab |
| `position` | 1R 风险单位、头寸规模、退出合同 | research_lab |
| `trade` | 交易管理模板、执行 runtime、TradeManager **（增强）** | trade_runtime |
| `system` | 编排总控、回测、治理检查 | trade_runtime |

---

## 主线链路

```
data → malf → structure → filter → alpha/pas → position → trade → system
```

**执行语义**：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价

**与父系统差异**：新增 `structure → filter` 两层（在 malf 之后、alpha 之前）

---

## 五目录纪律

| 目录 | 用途 | 禁止存放 |
|------|------|----------|
| `H:\Lifespan-Quant` | 代码、文档、测试、治理 | 数据库、日志、缓存 |
| `H:\Lifespan-Quant-data` | 正式七数据库（全持久化） | 代码、临时文件 |
| `H:\Lifespan-temp` | 临时产物、pytest、benchmark | 正式代码/数据库 |
| `H:\Lifespan-Quant-report` | 人读报告、图表、导出物 | 代码 |
| `H:\Lifespan-Quant-Validated` | 跨版本验证资产快照 | 普通临时产物 |

---

## 七数据库（全持久化）

**核心原则**：历史一旦发生就是永恒的瞬间——绝不重算。磁盘空间换内存，小批量断点续传。

| DB | 路径 | Owner | 内容 | 增量策略 |
|----|------|-------|------|----------|
| raw_market | data/raw/ | data | TDX 本地 .day + gbbq 除权除息 | 按日追加 |
| market_base | data/base/ | data | 复权价、均线、量比 | 只算新日期 |
| malf | data/malf/ | malf | MALF 三层主轴输出 | 新月/新周 |
| structure | data/structure/ | structure | 结构位快照（支撑/阻力/突破） | 按日按股追加 |
| filter | data/filter/ | filter | 不利条件检查结果 | 按日按股追加 |
| research_lab | data/research/ | alpha+position | PAS 信号 + 仓位计划 | 按信号追加 |
| trade_runtime | data/trade/ | trade/system | 交易记录 + 权益曲线 | 按交易追加 |

---

## PAS 触发器状态

| 触发器 | 状态 | 说明 |
|--------|------|------|
| BOF | **MAINLINE** | 主策略，保留确定（保留段胜率 56.5%，净收益 511万） |
| TST | CONDITIONAL | 辅策略，保留（2020 后持续正收益，保留段 108万） |
| PB | CONDITIONAL | 边缘策略，降权保留（量大质弱，保留段仅 15万） |
| BPB | **REJECTED** | 永久拒绝（三年验证不通过） |
| CPB | **REJECTED** | 剔除冻结（最弱，保留段 -33万） |

---

## 快速开始

```bash
python -m pip install -e .[dev]
pytest tests/unit -q
python scripts/data/bootstrap_storage.py
```

---

## 文档入口

- **系统概述**：`docs/01-design/00-system-overview-20260404.md`
- **模块设计**：`docs/01-design/modules/<module>/`
- **代理规则**：`AGENTS.md`

---

## 参考来源

- 父系统：`G:\MarketLifespan-Quant`（MALF 三层主轴、PAS 触发器验证、BOF/PB 三年数据）
- 爷爷系统：`G:\。backups\EmotionQuant-gamma`（执行语义、合同传递模式）
- 理论来源：YTC（Lance Beggs）— 结构位语言、不利条件过滤
