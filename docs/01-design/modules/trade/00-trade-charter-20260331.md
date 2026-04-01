# trade 模块章程 / 2026-03-31（2026-04-01 增补）

## 1. 血统与来源

| 层代 | 系统 | 状态 | 主要吸收点 |
|---|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma\src\broker + backtest` | 思想原型已收口 | Broker/Position/Order/Trade 四层合同、日循环引擎、ID 构造规则、A股成本模型 |
| 父系统 | `G:\MarketLifespan-Quant\src\mlq\trade\` | 正式定型，22文件 | 多运行摘要合同、broker_boundary Protocol、完整 trade_runtime schema（20+表）、企业行动处理 |
| 本系统 | `G:\Lifespan-Quant\src\lq\trade\` | 继承演进 | 新增 `TradeManager` 5阶段状态机（相对父系统最大增强）、简化 schema |
| 开源参考 | backtrader / vectorbt / qlib / easytrader | 设计借鉴 | 见 §1.2 |

### 1.1 从各代系统吸收的核心结论

**爷爷系统（EQ-gamma）：**
1. `Broker` 类拥有 `portfolio dict + pending_orders + RiskManager + Matcher` 四个核心组件
2. 日循环主序：`execute_pending → expire_orders → generate_exit → select_candidates → generate_signals → process_signals → force_close_all`
3. ID 规则铁律：`signal_id = code_date_pattern`，`trade_id = order_id + _T`，退出前缀 `EXIT_`，末日强平前缀 `FC_`，ID 格式一旦固定不允许变更（历史 JOIN 依赖）
4. A股成本模型：买入方向 commission + transfer_fee，卖出方向额外加 stamp_duty
5. 订单生命周期：`PENDING → FILLED / REJECTED / EXPIRED`（EXPIRED 避免挂单无限堆积）

**父系统（MarketLifespan）：**
1. `broker_boundary.py` 的 `TradeBrokerAdapter Protocol` 是实盘适配层的正确边界设计（submit/cancel/sync）
2. 运行摘要分层：`TradeRunManifest → TradeReplaySummary → TradeBacktestSummary → TradeRollingBacktestSummary → TradeBenchmarkSummary`（渐进复杂度）
3. 完整 trade_runtime 含 20+ 表，对于 Lifespan-Quant 当前阶段过重，取最小可运行子集（见 §02 schema 文档）
4. `pas_position_bridge` 是 research_lab → trade_runtime 的唯一正式桥接通道

**本系统（Lifespan-Quant）当前实现：**
1. `TradeManagementState + TradeManager` — 5阶段有状态机，已实现，已测试
2. `TradeRecord` — 单笔交易完整结果合同，已定义
3. **待补**：Broker 类、BacktestEngine、trade_runtime schema、成本模型

### 1.2 从开源项目借鉴的关键设计

| 项目 | 借鉴点 | 取舍决策 |
|---|---|---|
| **backtrader** | Data feed / Strategy / Broker 三层分离原则 | ✅ 采用：data(market_base) → TradeManager(strategy) → Broker(execution) 三层 |
| **backtrader** | Cerebro 引擎、Analyzer 框架 | ❌ 不采用：过重；用简单 BacktestEngine 替代 |
| **vectorbt** | 向量化 signal→fill→equity curve | ❌ 不采用：BOF 交易需要个股独立状态跟踪，不适合纯向量化 |
| **qlib** | Executor 与信号生成解耦 | ✅ 采用：Broker 只执行，信号来自上游 |
| **qlib** | DataHandler / Factor model | ❌ 不采用：信号来自 PAS detectors，非 ML 因子 |
| **easytrader** | 标准化券商适配器接口（submit/cancel/query） | ✅ 采用：`TradeBrokerAdapter Protocol`（继承自父系统）为实盘预留 |
| **backtesting.py** | 简洁的 Strategy 类（buy/sell/position） | ✅ 部分采用：TradeManager 的 `update(bar)` 接口风格与此类似 |

---

## 2. 模块定位

`trade` 是**执行层 + 回测引擎**，是系统的最终价值交付点。

**三层架构**：
```
TradeManager（策略层）
    ↓ 每日 bar 更新，输出动作信号
Broker（执行层）
    ↓ 撮合、成本计算、账户状态
BacktestEngine（引擎层）
    ↓ 驱动日历循环，协调上下游
trade_runtime.duckdb（持久化层）
```

**核心职责**：消费来自 `position` 模块的 `PositionPlan / PositionExitPlan`，在 A 股历史数据上完整执行交易生命周期，输出可审计、可追溯的 `TradeRecord` 与统计摘要。

---

## 3. 正式输入

1. `PositionPlan`（来自 `position` 模块）— 入场计划
2. `PositionExitPlan`（来自 `position` 模块）— 退出计划
3. `market_base.stock_daily_adjusted`（T+1 开盘价、每日 OHLCV）
4. `raw_market.raw_xdxr_event`（除权除息事件，用于持仓股本调整）

---

## 4. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `TradeRecord` | `dataclass`（冻结合同） | `trade_runtime.duckdb` L4 |
| `TradeRunSummary` | `dataclass` | `trade_runtime.duckdb` L4 |
| 权益曲线 | DuckDB 表 | `trade_runtime.duckdb` L4 |
| `BrokerOrderInstruction` | `dataclass` | 实盘适配器（当前纸交易） |

---

## 5. 交易管理模板（五阶段，冻结）

```
PENDING_ENTRY
    │ BUY FILLED (T+1 open)
    ▼
ACTIVE_INITIAL_STOP
    │ low ≤ stop_price              → HIT_INITIAL_STOP   → CLOSED_LOSS
    │ high ≥ first_target_price     → HIT_FIRST_TARGET   → FIRST_TARGET_HIT
    ▼
FIRST_TARGET_HIT
    │ r_multiple ≥ 0.5R             → BREAKEVEN_TRIGGERED → TRAILING_RUNNER
    ▼
TRAILING_RUNNER
    │ low ≤ trailing_stop           → TRAILING_STOP_TRIGGERED → CLOSED_WIN
    │ hold_days ≥ MAX_HOLD_DAYS     → TIME_STOP_TRIGGERED  → CLOSED_TIME
```

| 阶段 | 触发条件 | 动作 |
|---|---|---|
| 初始止损 | `today_low ≤ current_stop_price` | 全仓平仓 → CLOSED_LOSS |
| 第一目标止盈 | `today_high ≥ first_target_price` | 半仓止盈，剩余进入 runner |
| 保护性提损 | `r_multiple ≥ 0.5R` | 止损提至成本价（只升不降） |
| 跟踪 runner | `today_low ≤ highest × (1-trailing_pct)` | 清空剩余 → CLOSED_WIN |
| 时间止损 | `hold_days ≥ MAX_HOLD_DAYS` | 强制平仓 → CLOSED_TIME |

**默认参数**（已在 `management.py` 固定）：

| 参数 | 值 | 说明 |
|---|---|---|
| `TRAILING_ACTIVATION_R` | 1.0 | 盈利超过 1R 后激活跟踪 |
| `TRAILING_STEP_PCT` | 0.06 | 最高点回撤 6% 触发 |
| `BREAKEVEN_TRIGGER_R` | 0.5 | 盈利超过 0.5R 提损到成本 |
| `MAX_HOLD_DAYS` | 20 | 时间止损上限（交易日） |
| `FAST_FAILURE_DAYS` | 3 | 快速失效判断窗口 |

---

## 6. A股成本模型（冻结）

```python
# 买入成本
commission_buy  = max(notional * 0.0003, 5.0)   # 万3，最低5元
transfer_fee    = shares / 1000 * 0.001           # 过户费（沪市，深市免）
cost_buy        = commission_buy + transfer_fee

# 卖出成本
commission_sell = max(notional * 0.0003, 5.0)   # 万3，最低5元
stamp_duty      = notional * 0.001               # 印花税（仅卖出）
transfer_fee    = shares / 1000 * 0.001           # 过户费
cost_sell       = commission_sell + stamp_duty + transfer_fee

# 滑点
slippage_pct    = 0.001   # 默认0.1%（10bps），买入价上浮，卖出价下浮
```

---

## 7. BacktestEngine 日循环主序

```
初始化 Broker（初始资金、空组合）
for trade_date in trade_days:
    1. execute_pending_orders(trade_date)     # T+1 开盘撮合
    2. update_positions(trade_date)            # 每日 bar → TradeManager.update()
    3. generate_exit_orders(trade_date)        # TradeManager 动作 → SELL 订单
    4. generate_entry_orders(trade_date)       # PositionPlan → BUY 订单（下一日执行）
force_close_all(trade_days[-1])               # 末日强平所有持仓
write_trade_records()                          # 落盘 trade_runtime
generate_summary()                            # 生成 BacktestSummary
```

---

## 8. BrokerAdapter Protocol（实盘预留）

```python
class TradeBrokerAdapter(Protocol):
    adapter_name: str
    def submit_order(self, instruction: BrokerOrderInstruction) -> str: ...
    def cancel_order(self, instruction: BrokerOrderInstruction) -> str: ...
    def sync_account_state(self, state: BrokerAccountState) -> str: ...
```

当前实现：`SimulatedBrokerAdapter`（纸交易，100% 成交率，T+1 开盘价）  
未来扩展：`EasyTraderBrokerAdapter`（接 easytrader 实盘）

---

## 9. 模块边界

### 9.1 负责

1. `TradeManager` 5阶段状态机（已实现）
2. `Broker` 类：撮合、持仓管理、成本计算、账户状态
3. `BacktestEngine`：日历循环 + 上下游协调
4. A股成本模型（commission + stamp_duty + transfer_fee + slippage）
5. `trade_runtime.duckdb` 写入（L4）
6. `BrokerAdapter Protocol`（实盘适配预留）

### 9.2 不负责

1. 信号生成（属于 `alpha/pas`）
2. 仓位规划计算（属于 `position`）
3. 市场数据基础库（属于 `data`）
4. 全局系统编排（属于 `system`）
5. MSS / IRS 参与交易决策（Lifespan-Quant 当前主线不引入）
6. 企业行动（除权除息）broker 层处理（数据层已后复权，broker 层免）

---

## 10. 铁律

1. **T+1 开盘执行**：`signal_date=T`，`execute_date=T+1`，成交价 = T+1 开盘价，禁止用 T 日收盘价撮合
2. **止损只升不降**：`current_stop_price` 只能向对持仓有利方向移动（多头只能上移）
3. **硬全平不可绕过**：`STOP_LOSS / FORCE_CLOSE` 触发时立即全平，不走 partial-exit
4. **ID 格式冻结**：`signal_id / trade_id / exit_order_id` 格式一旦固定不允许变更，历史 JOIN 依赖于此
5. **trade_runtime 写权**：`trade` 只写 `trade_runtime.duckdb`（L4），禁止写 `research_lab / market_base`
6. **Broker 不直接读 PasSignal**：Broker 只消费 `PositionPlan / PositionExitPlan`，不绕过 position 模块
7. **成本模型不可跳过**：即使回测，也必须扣除完整成本（commission + stamp_duty + transfer_fee + slippage）

---

## 11. 成功标准

1. `TradeManager` 5阶段状态机正确顺序触发，有单元测试覆盖五类退出场景
2. `Broker` 类实现：T+1 撮合 + A股成本 + 持仓账户状态
3. `BacktestEngine` 日循环可跑通至少 1 年历史数据
4. `TradeRecord` 落盘，可按 `trade_id / code / signal_date` 追溯
5. `trade_runtime.duckdb` 4 张核心表 bootstrap 完成
6. `BrokerAdapter Protocol` 有 `SimulatedBrokerAdapter` 实现

---

## 12. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-trade-charter-20260331.md`（本文） | 模块章程、血统、架构、铁律 |
| `01-trade-broker-engine-design-20260401.md` | Broker/Engine 设计：ID 规则、订单生命周期、成本计算、日循环伪代码 |
| `02-trade-runtime-schema-design-20260401.md` | trade_runtime.duckdb 最小 schema、表职责、写权边界 |
