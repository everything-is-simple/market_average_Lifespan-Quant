# 数据合同规格 / 2026-03-31

## 1. 原则

1. 模块间只传**结果合同**（不可变 `dataclass`），不传内部中间 DataFrame 或特征向量
2. 所有合同对象提供 `as_dict()` 方法，便于序列化和落库
3. 枚举值定义在 `lq.core.contracts` 中，所有模块共享同一份枚举

## 2. 核心合同一览

### 2.1 MalfContext（malf → structure/filter/alpha）

```python
@dataclass(frozen=True)
class MalfContext:
    code: str
    signal_date: date
    monthly_state: str      # MonthlyState8 值（八态）
    weekly_flow: str        # WeeklyFlowRelation 值（顺/逆流）
    surface_label: str      # SurfaceLabel 值（16格坐标）
    monthly_strength: float | None
    weekly_strength: float | None
```

### 2.2 StructureSnapshot（structure → filter/alpha）

```python
@dataclass(frozen=True)
class StructureSnapshot:
    code: str
    signal_date: date
    support_levels: tuple[StructureLevel, ...]
    resistance_levels: tuple[StructureLevel, ...]
    recent_breakout: BreakoutEvent | None
    nearest_support: StructureLevel | None
    nearest_resistance: StructureLevel | None
```

### 2.3 AdverseConditionResult（filter → alpha/system）

```python
@dataclass(frozen=True)
class AdverseConditionResult:
    code: str
    signal_date: date
    active_conditions: tuple[str, ...]   # AdverseConditionType 值列表
    tradeable: bool                       # False → 跳过该股票
    notes: str
```

### 2.4 PasSignal（alpha/pas → position）

```python
@dataclass(frozen=True)
class PasSignal:
    signal_id: str
    code: str
    signal_date: date
    pattern: str            # PasTriggerPattern 值
    surface_label: str      # 来自 MalfContext
    strength: float         # 0~1
    signal_low: float       # 用于 1R 止损计算
    entry_ref_price: float  # T+1 入场参考价
    pb_sequence_number: int | None   # A3：第几个 PB
```

### 2.5 PositionPlan（position → trade）

```python
@dataclass(frozen=True)
class PositionPlan:
    code: str
    signal_date: date
    entry_date: date
    signal_pattern: str
    signal_low: float
    entry_price: float
    initial_stop_price: float
    first_target_price: float
    risk_unit: float         # 1R = entry - stop
    lot_count: int
    notional: float
```

### 2.6 TradeRecord（trade → system/report）

```python
@dataclass(frozen=True)
class TradeRecord:
    trade_id: str
    code: str
    entry_date: date
    exit_date: date | None
    signal_pattern: str
    surface_label: str
    entry_price: float
    exit_price: float | None
    lot_count: int
    risk_unit: float
    pnl_amount: float | None
    pnl_pct: float | None
    r_multiple: float | None
    exit_reason: str | None
    lifecycle_state: str
    pb_sequence_number: int | None
```

## 3. 五数据库分层规则

| 层级 | 数据库 | 写入方 | 读取方 |
|------|--------|--------|--------|
| L1 | `raw_market` | `data` | `data`（自读自写） |
| L2 | `market_base` | `data` | `malf`、`alpha` |
| L3 | `research_lab` | `alpha/pas` | `position`、`trade` |
| L3 | `malf` | `malf` | `structure`、`filter`、`alpha` |
| L4 | `trade_runtime` | `trade` | `system`、`report` |

依赖规则：L2 只读 L1；L3 只读 L1/L2；L4 只读 L1/L2/L3。禁止反向依赖。
