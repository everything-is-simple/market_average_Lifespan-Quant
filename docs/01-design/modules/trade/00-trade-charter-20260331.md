# trade 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\` (system/trade 合并) | 有基础合同，无生命周期管理器 |
| 本系统 | `G:\Lifespan-Quant\src\lq\trade\` | **新增** `TradeManager` 状态机，完整交易管理模板 |

本模块是本系统相对父系统**增强最显著**的模块。父系统有基础合同但没有完整的交易生命周期管理，本系统补全了这一缺口。

## 2. 模块定位

`trade` 是交易管理模板层。

它负责消费 `PositionPlan` 和每日 K 线，执行完整的交易生命周期管理：

```
入场 → 初始止损 → 保护性提损 → 半仓止盈 → 跟踪 runner → 时间止损 → 平仓
```

`TradeManager` 是一个有状态的状态机，驱动单笔交易从信号到平仓的全过程。

## 3. 正式输入

1. `PositionPlan`（来自 `position` 模块，仓位规划合同）
2. `PositionExitPlan`（来自 `position` 模块，退出合同）
3. 每日 K 线 `DataFrame`（来自 `market_base.duckdb`）

## 4. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `TradeRecord` | `dataclass`（冻结合同） | 落入 `trade_runtime.duckdb`（L4） |

`TradeRecord` 包含：完整交易历史、每笔 K 线的状态机状态、最终平仓原因、盈亏统计。

## 5. 交易管理模板（五阶段，冻结）

| 阶段 | 触发条件 | 动作 |
|---|---|---|
| 初始止损 | 价格触及 `stop_loss_price` | 全仓平仓 |
| 保护性提损 | 价格上涨超过 1R | 止损移至成本价（保本止损） |
| 半仓止盈 | 价格达到 `first_target` | 减仓 50%，剩余跟踪 |
| 跟踪 runner | 半仓止盈后继续运行 | 以最高价回撤 X% 为跟踪止损 |
| 时间止损 | 持仓超过 `time_stop_bars` K 线 | 强制平仓（信号无效假设） |

## 6. 模块边界

### 6.1 负责

1. `TradeManager` 状态机实现
2. 每日状态更新（`update(bar)` 接口）
3. `TradeRecord` 生成与落库
4. 五阶段管理模板（初始止损 / 保护性提损 / 半仓止盈 / 跟踪 / 时间止损）
5. 回测中的交易历史记录

### 6.2 不负责

1. 信号生成（属于 `alpha/pas`）
2. 仓位规划（属于 `position`）
3. 市场数据基础库（属于 `data`）
4. 全局系统编排（属于 `system`）
5. 实盘下单（当前版本不涉及）

## 7. 铁律

1. `TradeManager` 只消费 `PositionPlan` + `PositionExitPlan`，禁止直接读 `PasSignal` 内部字段。
2. 执行语义固定：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价。
3. 止损移位只能向对持仓有利方向移动（止损只能移高，不能回退）。
4. `TradeRecord` 落入 `trade_runtime.duckdb`（L4），不写 `research_lab`。
5. 五阶段管理模板的阶段顺序不允许跳过。

## 8. 成功标准

1. `TradeManager` 状态机实现，五阶段能正确顺序触发
2. `TradeRecord` 合同冻结，含完整交易历史字段
3. 执行语义（T+1 开盘价）在所有测试场景中正确
4. 三年历史窗口回测中，TradeManager 能正确处理每日 bar 更新
5. 有单元测试覆盖五类触发条件和边界场景
