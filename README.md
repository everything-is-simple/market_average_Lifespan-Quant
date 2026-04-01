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
| 父系统 | 5 目录纪律、5 数据库架构、MALF 三层主轴、PAS 触发器治理、mootdx 数据源 |
| **本系统新增** | `structure` 模块（结构位语言）、`filter` 模块（不利条件过滤）、`TradeManager` 5 阶段状态机 |

---

## 九模块架构

| 模块 | 职责 | 数据库 |
|------|------|--------|
| `core` | 公共类型、路径合同、跨模块枚举 | 无 |
| `data` | 市场数据采集（mootdx）、清洗、落盘 | raw_market / market_base |
| `malf` | 市场平均寿命框架：monthly_state_8 / weekly_flow | malf |
| `structure` | 统一结构位合同：波段高低点、突破分类 **（新增）** | 无 |
| `filter` | 不利市场条件过滤器：5 类条件检测 **（新增）** | 无 |
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
| `G:\Lifespan-Quant` | 代码、文档、测试、治理 | 数据库、日志、缓存 |
| `G:\Lifespan-data` | 正式数据库与数据产物 | 代码、临时文件 |
| `G:\Lifespan-temp` | 临时产物、pytest、benchmark | 正式代码/数据库 |
| `G:\Lifespan-report` | 人读报告、图表、导出物 | 代码 |
| `G:\Lifespan-Validated` | 跨版本验证资产快照 | 普通临时产物 |

---

## 五数据库

| DB | 路径 | Owner | 内容 |
|----|------|-------|------|
| raw_market | Lifespan-data/raw/ | data | mootdx 本地 .day + gbbq 除权除息 |
| market_base | Lifespan-data/base/ | data | 复权价、均线、量比 |
| research_lab | Lifespan-data/research/ | alpha | PAS 信号、选中 trace |
| malf | Lifespan-data/malf/ | malf | MALF 三层主轴输出 |
| trade_runtime | Lifespan-data/trade/ | trade/system | 执行合同、回测结果 |

---

## PAS 触发器状态

| 触发器 | 状态 | 说明 |
|--------|------|------|
| BOF | MAINLINE | 主线可用 |
| PB | CONDITIONAL | 条件格准入 |
| BPB | **REJECTED** | 永久拒绝 |
| TST | PENDING | 待独立验证 |
| CPB | PENDING | 待独立验证 |

---

## 快速开始

```bash
python -m pip install -e .[dev]
pytest tests/unit -q
python scripts/data/bootstrap_storage.py
```

---

## 文档入口

- **系统概述**：`docs/01-design/00-system-overview-20260401.md`
- **模块设计**：`docs/01-design/modules/<module>/`
- **代理规则**：`AGENTS.md`

---

## 参考来源

- 父系统：`G:\MarketLifespan-Quant`（MALF 三层主轴、PAS 触发器验证、BOF/PB 三年数据）
- 爷爷系统：`G:\。backups\EmotionQuant-gamma`（执行语义、合同传递模式）
- 理论来源：YTC（Lance Beggs）— 结构位语言、不利条件过滤
