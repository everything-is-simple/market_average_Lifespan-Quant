# core 模块 — contracts 设计 / 2026-04-01

## 1. 设计目标

本文定义 `core/contracts.py` 的完整内容设计，包括：

1. 四组枚举的设计依据与分组逻辑
2. 每个枚举值的业务含义与使用规则
3. 五类常量的来源与约束
4. `PAS_TRIGGER_STATUS` 治理字典的使用规范
5. 与父/爷爷系统的继承取舍说明

---

## 2. 枚举分组设计

`contracts.py` 按主线链路的层次组织，共四组枚举：

```
第一组：背景层枚举（MALF）
    MonthlyState8      — 月线八态（MALF 计算层诊断状态，执行层收敛为 BULL/BEAR）
    WeeklyFlowRelation — 周线顺衰关系（MALF 计算层，执行层映射为 MAINSTREAM/COUNTERTREND）
    MalfContext4       — 四格上下文（MALF 执行层主轴）

第二组：触发层枚举（PAS）
    PasTriggerPattern  — 五触发模式
    PasTriggerStatus   — 触发器治理状态
    PAS_TRIGGER_STATUS — 当前治理状态字典（冻结）

第三组：结构位枚举（structure/filter）← 本系统新增
    StructureLevelType — 结构位类型
    BreakoutType       — 突破事件类型
    AdverseConditionType — 不利条件类型

第四组：交易管理枚举（trade）← 本系统新增
    TradeLifecycleState — 交易生命周期状态机
```

### 2.1 设计原则

- 每个枚举值使用 `str` 基类（`class X(str, Enum)`），可直接序列化为字符串，无需 `.value`
- 枚举值字符串一旦发布不允许变更（历史记录和数据库中已有该字符串）
- 新增枚举值向后兼容；废弃枚举值保留 3 个版本后才能删除

---

## 3. 第一组：背景层枚举（MALF）

### 3.1 MonthlyState8 — 月线八态

来源：EQ-gamma `MonthlyState8` + MarketLifespan `monthly_state_8` → 本系统提升到 `core` 层。

| 状态值 | 含义 | 背景特征 |
|---|---|---|
| BULL_FORMING | 牛市形成中 | 价格突破长期阻力，月线转头向上 |
| BULL_PERSISTING | 牛市持续中 | 月线持续上行，主趋势明确 |
| BULL_EXHAUSTING | 牛市衰竭中 | 上涨动能减弱，月线开始钝化 |
| BULL_REVERSING | 牛市反转中 | 月线出现顶部特征，向熊市转变 |
| BEAR_FORMING | 熊市形成中 | 价格跌破长期支撑，月线转头向下 |
| BEAR_PERSISTING | 熊市持续中 | 月线持续下行，主趋势明确 |
| BEAR_EXHAUSTING | 熊市衰竭中 | 下跌动能减弱，月线开始钝化 |
| BEAR_REVERSING | 熊市反转中 | 月线出现底部特征，向牛市转变 |

**辅助属性（已实现）**：
- `is_bull` — 判断是否牛市阶段
- `is_bear` — 判断是否熊市阶段
- `is_trending` — 仅 FORMING/PERSISTING 才算趋势主体（EXHAUSTING/REVERSING 不算）

### 3.2 WeeklyFlowRelation — 周线顺衰关系

| 值 | 含义 |
|---|---|
| `with_flow` | 周线与月线同向（顺势） |
| `against_flow` | 周线与月线反向（逆势） |

**注意**：值用小写下划线格式（历史兼容），与其他枚举的全大写风格不同，不允许修改。

### 3.3 MalfContext4 — 四格上下文

由 `long_background_2`（BULL/BEAR）+ `intermediate_role_2`（MAINSTREAM/COUNTERTREND）组合生成，是 MALF 执行层的主分类维度。

| 值 | long_background_2 | intermediate_role_2 |
|---|---|---|
| BULL_MAINSTREAM | BULL | MAINSTREAM |
| BULL_COUNTERTREND | BULL | COUNTERTREND |
| BEAR_MAINSTREAM | BEAR | MAINSTREAM |
| BEAR_COUNTERTREND | BEAR | COUNTERTREND |

**`from_monthly_weekly()` 方法**（已实现）：根据月线状态和周线顺衰自动推导四格上下文。

---

## 4. 第二组：触发层枚举（PAS）

### 4.1 PasTriggerPattern — 五触发模式

| 值 | 全名 | 语义 |
|---|---|---|
| BOF | Bar-Of-Failure | 假跌破后收回（多头陷阱反转） |
| BPB | Breakout-Pullback | 突破后回踩（顺势二次入场） |
| PB | Pullback | 普通回踩（趋势延续） |
| TST | Test | 测试支撑（价格触达支撑后反弹） |
| CPB | Compression-Pullback | 压缩后突破（动能积累） |

### 4.2 PasTriggerStatus — 触发器治理状态

| 值 | 含义 | 系统行为 |
|---|---|---|
| MAINLINE | 主线可用 | 默认启用，参与 `run_daily_signal_scan` |
| CONDITIONAL | 条件格准入 | 在特定背景格下可用，默认不排除 |
| REJECTED | 已验证但拒绝 | **system 层永久禁止**，任何路径不得调用 |
| PENDING | 待独立验证 | 代码存在但不参与主线 runner |

### 4.3 PAS_TRIGGER_STATUS — 当前治理状态（冻结字典）

```python
PAS_TRIGGER_STATUS = {
    PasTriggerPattern.BOF: PasTriggerStatus.MAINLINE,      # ← 主策略
    PasTriggerPattern.TST: PasTriggerStatus.CONDITIONAL,    # ← 辅策略（2020后持续正收益）
    PasTriggerPattern.PB:  PasTriggerStatus.CONDITIONAL,    # ← 边缘降权（量大质弱）
    PasTriggerPattern.BPB: PasTriggerStatus.REJECTED,       # ← 永久拒绝
    PasTriggerPattern.CPB: PasTriggerStatus.REJECTED,       # ← 剔除冻结（保留段负收益）
}
```

**使用规范**：
```python
# 正确：通过 PAS_TRIGGER_STATUS 过滤
enabled = [
    p for p, status in PAS_TRIGGER_STATUS.items()
    if status in (PasTriggerStatus.MAINLINE, PasTriggerStatus.CONDITIONAL)
]

# 禁止：直接比较字符串
if pattern == "BPB":   # ← 禁止魔法字符串
```

---

## 5. 第三组：结构位枚举（本系统新增）

来自 Lifespan-Quant 相对父/爷爷系统最大的架构创新：`structure` 模块引入统一结构位语言。

### 5.1 StructureLevelType — 结构位类型

| 值 | 含义 | 典型形成场景 |
|---|---|---|
| SUPPORT | 水平支撑位 | 多次测试未跌破的水平区间 |
| RESISTANCE | 水平阻力位 | 多次冲击未突破的水平区间 |
| PIVOT_LOW | 波段低点 | 明显的价格摆动低点 |
| PIVOT_HIGH | 波段高点 | 明显的价格摆动高点 |
| POST_BREAKOUT_SUPPORT | 突破后新支撑 | 原阻力突破后翻转为支撑（BPB/CPB 场景） |
| POST_BREAKDOWN_RESISTANCE | 跌破后新阻力 | 原支撑跌破后翻转为阻力 |
| TEST_POINT | 测试点 | 回踩到支撑位但未跌破（TST 场景） |

**辅助属性（在 StructureLevel dataclass 中实现）**：
- `is_support`：SUPPORT / PIVOT_LOW / POST_BREAKOUT_SUPPORT / TEST_POINT 均为支撑性
- `is_resistance`：RESISTANCE / PIVOT_HIGH / POST_BREAKDOWN_RESISTANCE 均为阻力性

### 5.2 BreakoutType — 突破事件分类

| 值 | 含义 | 典型 PAS 关联 |
|---|---|---|
| VALID_BREAKOUT | 有效突破 | BPB 前提 / 旧阻力变新支撑 |
| FALSE_BREAKOUT | 假突破（已收回） | BOF 触发的核心识别 |
| TEST | 测试（触达未穿越） | TST 触发场景 |
| PULLBACK_CONFIRMATION | 突破后回踩确认 | BPB / CPB 场景 |
| UNKNOWN | 尚未分类 | 默认初始值，不用于正式合同传递 |

### 5.3 AdverseConditionType — 不利市场条件

| 值 | 含义 | 过滤参数 |
|---|---|---|
| COMPRESSION_NO_DIRECTION | 压缩且无方向 | 近 10 日振幅 < 长期振幅 50% + 均线斜率 < 0.5% |
| STRUCTURAL_CHAOS | 结构混乱 | 15 日内方向切换 > 4 次 |
| INSUFFICIENT_SPACE | 空间不足 | 支撑到阻力的空间 < 5% |
| SIGNAL_CONFLICT | 多重信号冲突 | 跨周期背离（当前实现） |
| BACKGROUND_NOT_SUPPORTING | 背景不支持 | 月线 BEAR_PERSISTING 屏蔽做多 |

---

## 6. 第四组：交易管理枚举（本系统新增）

### 6.1 TradeLifecycleState — 交易生命周期状态机

对应 `TradeManager` 5 阶段状态机的完整状态集合：

| 值 | 阶段 | 转入条件 |
|---|---|---|
| PENDING_ENTRY | 等待入场 | PositionPlan 生成，BUY 订单挂出 |
| ACTIVE_INITIAL_STOP | 初始止损保护 | BUY 成交（T+1 开盘） |
| FIRST_TARGET_HIT | 第一目标已达 | high ≥ first_target_price |
| TRAILING_RUNNER | 跟踪止损 runner | r_multiple ≥ 0.5R（保本触发后） |
| CLOSED_WIN | 盈利平仓 | 跟踪止损触发 |
| CLOSED_LOSS | 亏损止损 | 初始止损触发 |
| CLOSED_TIME | 时间止损平仓 | hold_days ≥ MAX_HOLD_DAYS |
| CANCELLED | 已取消 | 信号失效未能入场 |

**状态转移规则**：
```
PENDING_ENTRY
  → ACTIVE_INITIAL_STOP（BUY 成交）
  → CANCELLED（订单 EXPIRED）

ACTIVE_INITIAL_STOP
  → CLOSED_LOSS（止损触发）
  → FIRST_TARGET_HIT（第一目标达到）

FIRST_TARGET_HIT（+ BREAKEVEN_TRIGGERED 内部标志）
  → TRAILING_RUNNER（保本激活）
  → CLOSED_TIME（超时）

TRAILING_RUNNER
  → CLOSED_WIN（跟踪止损触发）
  → CLOSED_TIME（超时）
```

---

## 7. 五类常量

### 7.1 A 股指数标识

```python
PRIMARY_INDEX_CODE = "000001.SH"       # 上证综指（主基准）
VALIDATION_INDEX_CODES = (
    "000300.SH",   # 沪深300
    "399001.SZ",   # 深证成指
    "399006.SZ",   # 创业板指
    "000688.SH",   # 科创50
)
MARKET_CONTEXT_ENTITY_CODE = "CN_WIDE_INDEX_POOL"
```

### 7.2 A 股交易费率（冻结）

```python
COMMISSION_RATE    = 0.0003   # 佣金 万3（双边）
STAMP_DUTY_RATE    = 0.0005   # 印花税 0.05%（当前为单边卖出，注意：trade 模块用 0.001）
TRANSFER_FEE_RATE  = 0.00002  # 过户费 0.002%
```

**注意**：`core.contracts` 中印花税率 `0.0005` 是历史旧版本，`trade` 模块成本模型中使用 `0.001`（当前正确税率）。下一版本需对齐。

### 7.3 默认资金合同

```python
DEFAULT_CAPITAL_BASE   = 1_000_000.0   # 默认初始资金（百万）
DEFAULT_FIXED_NOTIONAL = 100_000.0     # 默认单笔固定名义金额
DEFAULT_LOT_SIZE       = 100           # A 股最小交易单位（手 = 100 股）
```

### 7.4 PAS 信号方向

```python
PAS_SIGNAL_SIDE   = "LONG"   # 当前主线只做多
PAS_SIGNAL_ACTION = "BUY"
```

### 7.5 市场背景实体标识

```python
MARKET_CONTEXT_ENTITY_CODE = "CN_WIDE_INDEX_POOL"
```

---

## 8. 已知问题

### 8.1 待修复

| 问题 | 描述 | 优先级 |
|---|---|---|
| 印花税率不一致 | `core.contracts.STAMP_DUTY_RATE=0.0005` vs `trade` 成本模型 `0.001` | 中（下版本对齐） |
| 缺少 ID 构造函数 | EQ-gamma 有 `build_signal_id()` 等，本系统 ID 构造散落在各模块 | 低（当前可接受） |

### 8.2 已解决

| 问题 | 解决方案 | 解决日期 |
|---|---|---|
| 无 checkpoint store | 新增 `checkpoint.py`（JsonCheckpointStore）+ `resumable.py`（6 个续跑工具） | 2026-04-02 |

---

## 9. 禁止操作

1. 在业务模块内自定义重复的枚举（如自己写 `class MyState(str, Enum): BULL = "BULL"`）
2. 在业务代码中硬编码魔法字符串（如 `if pattern == "BPB":`，必须用枚举）
3. 在 `core.contracts` 中加入任何 import 第三方库（pandas、duckdb、numpy 等）
4. 修改已发布枚举值的字符串（格式冻结，破坏历史数据）
5. 把任何模块专有逻辑（如 BOF 探测条件）提升进 `core`
