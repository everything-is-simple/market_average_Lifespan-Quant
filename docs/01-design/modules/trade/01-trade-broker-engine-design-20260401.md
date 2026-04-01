# trade 模块 — Broker / Engine 设计 / 2026-04-01

## 1. 设计目标

本文定义 `trade` 模块的执行内核，包括：

1. ID 构造规则（信号 / 订单 / 成交 / 退出）
2. Order / Position / Trade 三层数据合同
3. Broker 类职责与边界
4. BacktestEngine 日循环完整伪代码
5. A 股成本模型实现细节
6. BrokerAdapter Protocol（实盘预留）

本文不回答：
- 何时接入实盘（easytrader）
- 滚动窗口回测 / benchmark 框架（父系统已有，当前不实现）

---

## 2. ID 构造规则（全局冻结）

ID 是跨表 JOIN 的基础，格式一旦固定不允许变更。

```python
# 信号 ID（primary key of signal domain）
signal_id = f"{code}_{signal_date.isoformat()}_{pattern}"
# 例：000001_2024-03-15_BOF

# 买入订单 ID（与 signal_id 同构）
buy_order_id = signal_id

# 成交 ID
trade_id = f"{order_id}_T"
# 例：000001_2024-03-15_BOF_T

# 退出订单 ID（按退出原因分类）
exit_order_id = f"EXIT_{signal_id}_{reason.lower()}"
# 例：EXIT_000001_2024-03-15_BOF_trailing_stop

# 末日强平 ID（FC_ 前缀供 origin 解析识别）
force_close_id = f"FC_{code}_{trade_date.isoformat()}"
# 例：FC_000001_2024-04-30

# partial-exit 腿 ID（腿序号 L01/L02）
exit_leg_id = f"{exit_order_id}_L{seq:02d}"
```

### 2.1 origin 解析规则

```python
def resolve_order_origin(order_id: str) -> str:
    if order_id.startswith("FC_"):       return "FORCE_CLOSE"
    if "_trailing_stop" in order_id:     return "EXIT_TRAILING_STOP"
    if "_stop_loss" in order_id:         return "EXIT_STOP_LOSS"
    if order_id.startswith("EXIT_"):     return "EXIT_OTHER"
    return "UPSTREAM_SIGNAL"
```

---

## 3. 数据合同三层结构

### 3.1 Order（订单意图层）

```python
@dataclass
class Order:
    order_id: str           # 订单唯一 ID
    signal_id: str          # 关联的信号 ID
    code: str
    action: str             # "BUY" | "SELL"
    quantity: int           # 计划数量（股）
    execute_date: date      # 计划执行日（T+1）
    pattern: str            # PAS pattern
    status: str             # PENDING | FILLED | REJECTED | EXPIRED
    # 退出语义扩展（SELL 专用）
    exit_reason_code: str | None = None
    is_partial_exit: bool = False
    position_id: str | None = None
    exit_plan_id: str | None = None
    exit_leg_id: str | None = None
    exit_leg_seq: int | None = None
    exit_leg_count: int | None = None
    remaining_qty_before: int | None = None
    target_qty_after: int | None = None
```

### 3.2 Trade（成交层）

```python
@dataclass(frozen=True)
class Fill:
    fill_id: str            # = order_id + _F
    order_id: str
    code: str
    fill_date: date         # 实际成交日
    action: str             # "BUY" | "SELL"
    fill_price: float       # 实际成交价（含滑点）
    fill_shares: int        # 实际成交数量
    fill_notional: float    # fill_price × fill_shares
    commission: float
    stamp_duty: float
    transfer_fee: float
    slippage_cost: float
    total_cost: float       # 所有费用合计
    # 退出语义
    exit_reason_code: str | None = None
    is_partial_exit: bool = False
    remaining_qty_after: int | None = None
    position_id: str | None = None
```

### 3.3 Position（持仓层，可变状态）

```python
@dataclass
class Position:
    position_id: str        # = buy order_id（稳定身份）
    code: str
    entry_date: date
    entry_price: float      # T+1 开盘成交价
    initial_quantity: int   # 初始股数
    remaining_quantity: int # 当前剩余股数
    current_price: float    # 每日收盘价更新
    max_price_seen: float   # 持仓期最高价
    pattern: str
    state: str              # OPEN | PARTIAL_EXIT_PENDING | OPEN_REDUCED | FULL_EXIT_PENDING | CLOSED
    # TradeManager 关联
    manager: TradeManager | None = None
```

---

## 4. Broker 类设计

### 4.1 核心属性

```python
class Broker:
    cash: float                           # 当前可用资金
    portfolio: dict[str, Position]         # code → Position
    pending_orders: list[Order]            # 待执行订单队列
    trade_records: list[TradeRecord]       # 已完成交易记录
    cost_model: AShareCostModel            # A 股成本计算
    adapter: TradeBrokerAdapter            # 实盘适配器（默认 Simulated）
    run_id: str
    initial_cash: float
```

### 4.2 核心方法

```python
def execute_pending_orders(self, trade_date: date) -> list[Fill]:
    """T+1 开盘撮合所有 PENDING 订单。"""
    # 1. 读取 T 日（trade_date）开盘价
    # 2. BUY：open_price * (1 + slippage)
    # 3. SELL：open_price * (1 - slippage)
    # 4. 计算成本、扣减现金、更新持仓
    # 5. 订单状态 → FILLED

def expire_orders(self, trade_date: date) -> None:
    """过期超过 1 日仍未执行的 PENDING 订单。"""
    # 超过 execute_date 仍未撮合的订单 → EXPIRED
    # 避免挂单无限堆积（A 股 T+1 语义下不应出现跨日挂单）

def update_positions(self, trade_date: date, ohlcv: dict[str, BarData]) -> None:
    """每日 bar 更新所有持仓的 TradeManager 状态。"""
    for code, pos in self.portfolio.items():
        if pos.state != "OPEN":
            continue
        bar = ohlcv.get(code)
        if bar is None:
            continue
        pos.current_price = bar.close
        pos.max_price_seen = max(pos.max_price_seen, bar.high)
        actions = pos.manager.update(bar.high, bar.low, bar.close, trade_date)
        self._dispatch_actions(pos, actions, trade_date)

def generate_exit_orders(self, trade_date: date) -> list[Order]:
    """根据 TradeManager 动作生成退出订单（次日执行）。"""
    # HIT_INITIAL_STOP   → EXIT_STOP_LOSS 全平订单
    # TRAILING_STOP_TRIGGERED → EXIT_TRAILING_STOP 全平（或 partial 腿）
    # TIME_STOP_TRIGGERED → FC_ 强平订单
    # HIT_FIRST_TARGET  → EXIT_FIRST_TARGET 半仓 SELL 订单

def submit_entry_order(self, plan: PositionPlan) -> Order:
    """把 PositionPlan 转化为 BUY 订单加入 pending 队列。"""

def force_close_all(self, trade_date: date) -> list[Fill]:
    """末日强平所有剩余持仓（收盘价撮合，带 FC_ 前缀）。"""
```

### 4.3 账户状态快照

```python
@dataclass(frozen=True)
class AccountState:
    trade_date: date
    cash_balance: float
    market_value: float          # portfolio 按收盘价估值
    total_equity: float          # cash + market_value
    realized_pnl: float
    unrealized_pnl: float
    exposure_ratio: float        # market_value / total_equity
```

---

## 5. BacktestEngine 日循环（完整伪代码）

```python
class BacktestEngine:
    def __init__(
        self,
        plans: list[PositionPlan],         # 来自 position 模块
        exit_plans: dict[str, PositionExitPlan],
        market_db: DuckDBConnection,
        initial_cash: float = 1_000_000,
        run_id: str | None = None,
    ): ...

    def run(self, start: date, end: date) -> BacktestSummary:
        broker = Broker(initial_cash, run_id=self.run_id)

        # 建立 signal_date → plans 索引
        plan_index = _build_plan_index(self.plans)

        # 遍历交易日
        trade_days = _fetch_trade_calendar(self.market_db, start, end)

        equity_curve: list[AccountState] = []

        for trade_date in trade_days:

            # Step 1: 撮合昨日挂单（T+1 开盘）
            broker.execute_pending_orders(trade_date)

            # Step 2: 更新每日 bar → TradeManager
            ohlcv = _fetch_daily_bar(self.market_db, trade_date, broker.portfolio.keys())
            broker.update_positions(trade_date, ohlcv)

            # Step 3: 生成退出订单（加入 pending，次日撮合）
            broker.generate_exit_orders(trade_date)

            # Step 4: 当日信号 → 入场订单（次日撮合）
            today_plans = plan_index.get(trade_date, [])
            for plan in today_plans:
                if _can_enter(broker, plan):
                    broker.submit_entry_order(plan)

            # Step 5: 记录权益曲线
            equity_curve.append(broker.snapshot_account_state(trade_date, ohlcv))

        # 末日强平
        broker.force_close_all(trade_days[-1])

        # 落盘
        _write_trade_records(broker.trade_records, self.runtime_db)
        _write_equity_curve(equity_curve, self.runtime_db)

        return _build_summary(broker, equity_curve, self.run_id)
```

### 5.1 入场准入条件（_can_enter）

```python
def _can_enter(broker: Broker, plan: PositionPlan) -> bool:
    if plan.code in broker.portfolio:
        return False                     # 已持仓，不重复开仓
    if broker.cash < plan.notional * 1.02:
        return False                     # 现金不足（含预估成本）
    if len(broker.portfolio) >= MAX_POSITIONS:
        return False                     # 超过最大持仓数
    return True

MAX_POSITIONS = 10   # 默认最大同时持仓只数
```

---

## 6. A 股成本模型（正式实现）

```python
class AShareCostModel:
    commission_rate: float = 0.0003    # 万3
    min_commission: float = 5.0        # 最低5元
    stamp_duty_rate: float = 0.001     # 千1（仅卖出）
    transfer_fee_rate: float = 0.000001 # 过户费：1元/千股
    slippage_bps: float = 10           # 默认10bps滑点

    def calc_buy_cost(self, price: float, shares: int) -> CostBreakdown:
        notional = price * shares
        commission = max(notional * self.commission_rate, self.min_commission)
        transfer_fee = shares / 1000 * (self.transfer_fee_rate * 1000)
        slippage = notional * self.slippage_bps / 10000
        fill_price = price * (1 + self.slippage_bps / 10000)
        return CostBreakdown(
            fill_price=fill_price,
            commission=commission,
            stamp_duty=0.0,
            transfer_fee=transfer_fee,
            slippage_cost=slippage,
            total_cost=commission + transfer_fee,
        )

    def calc_sell_cost(self, price: float, shares: int) -> CostBreakdown:
        notional = price * shares
        commission = max(notional * self.commission_rate, self.min_commission)
        stamp_duty = notional * self.stamp_duty_rate
        transfer_fee = shares / 1000 * (self.transfer_fee_rate * 1000)
        slippage = notional * self.slippage_bps / 10000
        fill_price = price * (1 - self.slippage_bps / 10000)
        return CostBreakdown(
            fill_price=fill_price,
            commission=commission,
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            slippage_cost=slippage,
            total_cost=commission + stamp_duty + transfer_fee,
        )
```

### 6.1 典型成本示例

| 场景 | 价格 | 股数 | 名义金额 | 总成本 |
|---|---|---|---|---|
| 买入 10 万 | 10.00 | 10,000 | 100,000 | ≈ 35 元（commission 30 + transfer 10）|
| 卖出 10 万 | 11.00 | 10,000 | 110,000 | ≈ 143 元（commission 33 + stamp 110 + transfer 10）|
| 滑点 10bps 买入 | 10.00 | — | 100,000 | 额外 10 元 |

---

## 7. BrokerAdapter Protocol（实盘预留）

```python
class TradeBrokerAdapter(Protocol):
    """broker 适配层最小接口（来自父系统 broker_boundary.py）。"""
    adapter_name: str

    def submit_order(self, instruction: BrokerOrderInstruction) -> str:
        """提交订单，返回适配层状态字符串。"""

    def cancel_order(self, instruction: BrokerOrderInstruction) -> str:
        """撤单，返回适配层状态字符串。"""

    def sync_account_state(self, state: BrokerAccountState) -> str:
        """同步账户状态，返回适配层状态字符串。"""
```

### 7.1 当前实现：SimulatedBrokerAdapter

```
特性：
- 100% 成交率（无流动性拒绝）
- T+1 开盘价撮合
- 完整 A 股成本扣除
- 无实盘 API 调用

适用场景：回测、纸交易研究
```

### 7.2 未来扩展：EasyTraderBrokerAdapter

```
接入 easytrader 提供的：
- submit_order() → easytrader.buy / sell
- cancel_order() → easytrader.cancel
- sync_account_state() → easytrader.balance + easytrader.position

注意：仅在研究结论冻结、系统稳定后才实施；
当前不实现，但接口已通过 Protocol 预留。
```

---

## 8. 与 TradeManager 的职责边界

| 职责 | 归属 |
|---|---|
| 判断止损是否触发 | `TradeManager.update()` |
| 判断第一目标是否达到 | `TradeManager.update()` |
| 维护持仓最高价 | `TradeManager.state.highest_price_seen` |
| 生成退出订单对象 | `Broker.generate_exit_orders()` |
| 实际扣减现金 / 股数 | `Broker.execute_pending_orders()` |
| 计算 PnL / R-multiple | `TradeManager.to_trade_record()` |
| 落盘 TradeRecord | `BacktestEngine._write_trade_records()` |

铁律：**TradeManager 只感知价格，不感知现金**；**Broker 只执行订单，不判断交易策略**。

---

## 9. 禁止操作

1. Broker 直接读取 `PasSignal` 内部字段（必须通过 `PositionPlan` 桥接）
2. TradeManager 直接写 DuckDB（只生成事件，由 Engine 写库）
3. 在 T 日收盘价撮合 T 日信号（必须 T+1 开盘）
4. 把滑点和成本设为 0（即使测试也必须走成本模型，否则结果不可比）
5. 跨持仓共享 TradeManager 实例（每只股票 / 每笔交易必须独立实例）
6. 末日不 force_close（回测必须清仓以保证成交对配对）
