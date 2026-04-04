# trade 模块 — Broker / Engine 设计 / 2026-04-04

> 取代 `01-trade-broker-engine-design-20260401.md`。新增 §1.1 自实现决策确认和实现规模预估。原文 §2–§9 内容不变，完整保留。

## 1. 设计目标

本文定义 `trade` 模块的执行内核，包括：

1. ID 构造规则（信号 / 订单 / 成交 / 退出）
2. Order / Position / Trade 三层数据合同
3. Broker 类职责与边界
4. BacktestEngine 日循环完整伪代码
5. A 股成本模型实现细节
6. BrokerAdapter Protocol（实盘预留）

本文不回答：
- 何时接入实盘（easytrader / TDXQuant 交易接口）
- 滚动窗口回测 / benchmark 框架（父系统已有，当前不实现）

### 1.1 自实现决策确认（2026-04-04 增补）

**决策**：BacktestEngine + Broker **自实现**，参考 backtrader 设计理念但不引入任何外部回测框架包依赖。

**理由**（详见 `00-trade-charter-20260404.md` §1.3）：
- qlib：ML/AI 因子范式与 TradeManager 5阶段状态机**根本不兼容**
- backtrader：2023 年停更，Cerebro 侵入性强
- vectorbt：向量化范式不匹配逐股状态跟踪

**实现规模预估**：

| 组件 | 预估行数 | 核心职责 |
|---|---|---|
| `BacktestEngine` | ~200 | 日历循环、上下游协调、末日强平、落盘 |
| `Broker` | ~200 | 撮合、持仓管理、订单队列、账户快照 |
| `AShareCostModel` | ~50 | A 股成本计算（commission + stamp_duty + transfer_fee + slippage） |
| `SimulatedBrokerAdapter` | ~50 | 纸交易适配器（100% 成交率，T+1 开盘价） |
| 总计 | ~500 | 无外部框架依赖 |

**后悔成本**：模块边界清晰（`PositionPlan → trade → TradeRecord`），合同冻结。如将来需引入外部框架，可替换 BacktestEngine 内部实现而不影响上下游。

**质量保障**：
1. 父系统已有完整验证基线（22文件，20+表），可逐项对照
2. 单元测试覆盖 5 类退出场景（initial_stop / first_target / trailing_stop / time_stop / force_close）
3. 成本模型有典型案例验证表（见 §6.1）

---

> **以下 §2–§9 内容与 `01-trade-broker-engine-design-20260401.md` 完全一致，不重复。**
> 如需查阅 ID 构造规则、数据合同、Broker 类设计、BacktestEngine 伪代码、成本模型、BrokerAdapter Protocol，
> 请直接参考原文 `01-trade-broker-engine-design-20260401.md` §2–§9。

---

## 变更记录

| 日期 | 版本 | 变更内容 |
|---|---|---|
| 2026-04-01 | v1 | 初版 Broker/Engine 设计（ID规则、合同、伪代码、成本模型、适配器） |
| 2026-04-04 | v2（本文） | 新增 §1.1 自实现决策确认、实现规模预估、质量保障说明 |
