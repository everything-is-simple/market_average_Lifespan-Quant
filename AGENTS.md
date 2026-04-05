# AGENTS.md — Lifespan-Quant

## 系统定位

`Lifespan-Quant` 是面向中国 A 股的**市场平均寿命量化系统（第二代重构版）**。

- 个人项目，单开发者
- 执行模型：增量交付，每步产出可独立验证的交付物
- 文档服务实现，不追求文档完美
- **系统概述**：`docs/01-design/00-system-overview-20260404.md`

---

## 三代血统

```
爷爷系统（EmotionQuant-gamma）→ 父系统（MarketLifespan-Quant）→ 本系统（Lifespan-Quant）
```

**从爷爷继承**：执行语义（T+1 Open）、合同传递模式、代码规范

**从父系统继承**：5 目录纪律、数据库架构（本系统扩展为七库全持久化）、MALF 三层主轴、PAS 触发器治理、mootdx 数据源

**父系统冻结口径**（`2026-04-03`）：研究验证版主线基本闭环，可持续日更、可复跑、可审计；非正式上线。
详见：`docs/04-reference/battle-tested-lessons-core-data-malf-from-v001-20260403.md`

**本系统新增**：`structure` 模块（结构位语言）、`filter` 模块（不利条件过滤）、`TradeManager` 5 阶段状态机、`core` 枚举集中化

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
| `trade` | 交易管理模板、执行 runtime、TradeManager | trade_runtime |
| `system` | 编排总控、回测、治理检查 | trade_runtime |

---

## 主线铁律

1. **主线链路**：`data → malf → structure → filter → alpha/pas → position → trade → system`
2. **执行语义**：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价
3. **模块间只传结果合同**，不传内部中间特征（`dataclass` / `pydantic`）
4. **路径/密钥禁止硬编码**，统一经 `core/paths.py` 注入或环境变量
5. **structure 模块是新增核心**，统一结构位语言后才能扩充 trigger 语义
6. **filter 模块是准入门槛**，先通过不利条件过滤才进入 trigger 检测
7. **BPB 永久拒绝**：system 层任何路径不得调用 BPB 触发器
8. **PAS 触发器状态**：BOF=MAINLINE，TST=CONDITIONAL，PB=CONDITIONAL，BPB=REJECTED，CPB=REJECTED

---

## 代码规范

- 代码注释使用**中文**
- 函数/方法命名：`snake_case`
- 类命名：`PascalCase`
- 模块包名：`lq`（短名，Lifespan-Quant）
- 枚举统一在 `core.contracts`，禁止各模块自定义重复枚举

---

## 五目录纪律（强制）

| 目录 | 用途 | 禁止存放 |
|------|------|----------|
| `H:\Lifespan-Quant` | 代码、文档、测试、治理 | 数据库、日志、缓存 |
| `H:\Lifespan-Quant-data` | 正式七数据库（全持久化） | 代码、临时文件 |
| `H:\Lifespan-temp` | 临时文件、pytest、中间产物 | 正式代码/数据库 |
| `H:\Lifespan-Quant-report` | 报表、图表、正式导出 | 代码 |
| `H:\Lifespan-Quant-Validated` | 跨版本验证资产快照 | 普通临时产物 |

---

## 七数据库（全持久化 DuckDB）

**核心原则**：历史一旦发生就是永恒的瞬间——绝不重算。磁盘空间换内存，小批量断点续传。

| DB | 路径 | Owner | 内容 | 增量策略 |
|----|------|-------|------|----------|
| `raw_market` | `data/raw/` | data | TDX 本地 .day + gbbq 除权除息 | 按日追加 |
| `market_base` | `data/base/` | data | 复权价、均线、量比 | 只算新日期 |
| `malf` | `data/malf/` | malf | MALF 三层主轴输出 | 新月/新周 |
| `structure` | `data/structure/` | structure | 结构位快照（支撑/阻力/突破） | 按日按股追加 |
| `filter` | `data/filter/` | filter | 不利条件检查结果 | 按日按股追加 |
| `research_lab` | `data/research/` | alpha+position | PAS 信号 + 仓位计划 | 按信号追加 |
| `trade_runtime` | `data/trade/` | trade/system | 交易记录 + 权益曲线 | 按交易追加 |

**硬件约束（设计依据）**：单机 AMD 5800H / **32G 内存** / 2×512G SSD。32G 是硬上限，全市场多层计算必须分批落盘（读→算→写→释放）。父系统 v0.01 的 `research_lab`/`trade_runtime` 虽是磁盘文件，但每次回测生成新 `run_id` 不复用旧结果，1000 只×10 年需 **5–7 小时**。v0.1 改为 `config_hash` 增量跳过：同一 `(code, date, config_hash)` 已存在则直接跳过，不重算。详见 `docs/01-design/00-system-overview-20260404.md §6.1`。

---

## 模块依赖矩阵

```
core（基础层，所有模块依赖）
data      → core
malf      → core, data
structure → core
filter    → core, malf
alpha     → core, data, malf, structure, filter
position  → core, data, alpha
trade     → core, data, position
system    → core, data, malf, alpha, position, trade
```

**禁止反向依赖**：下游模块不得 import 上游模块的内部实现。

---

## 测试目录规范

```
tests/
  unit/<module>/        单元测试
  integration/<module>/ 集成测试
  patches/<module>/     回归/补丁测试
```

---

## 开发命令

```bash
python -m pip install -e .[dev]
pytest tests/unit -q
python scripts/data/bootstrap_storage.py
```

---

## 仓库远端

- `origin`: `https://github.com/everything-is-simple/market_average_Lifespan-Quant`
- 推送策略：同时推送到所有活跃远端
