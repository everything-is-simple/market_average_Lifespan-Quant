# position 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma` 的 `positioning` 模块 | 思想原型，仅参考 |
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\position\` | 正式定型，完整设计 |
| 本系统 | `G:\Lifespan-Quant\src\lq\position\` | 继承父系统 sizing / exit 合同，无结构性变化 |

## 2. 模块定位

`position` 是仓位与退出研究模块。
它负责把 `PasSignal` 转化为可验证的仓位规划与退出合同，为交易主线提供可冻结迁移的持仓治理结果。

本模块**不是交易账户**，输出的是研究层合同对象，经桥接后才进入正式交易运行态。

## 3. 正式输入

1. `PasSignal`（来自 `alpha/pas` 模块）
2. `MalfContext`（可选，用于背景感知 sizing）
3. 当日日线价格（入场价格参考，用于计算 1R）

## 4. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `PositionPlan` | `dataclass`（冻结合同） | 传给 `trade` 模块 |
| `PositionExitPlan` | `dataclass`（冻结合同） | 传给 `trade` 模块 |

两个合同是本模块对外的唯一正式输出。

### PositionPlan 核心字段

- `code`：股票代码
- `signal_date`：信号日（T 日）
- `entry_date`：执行日（T+1 日）
- `entry_price`：计划入场价（T+1 开盘价）
- `stop_loss_price`：初始止损价（1R 基准）
- `risk_per_share`：每股风险（1R）
- `position_size`：计划股数
- `risk_amount`：总风险额（= `risk_per_share × position_size`）

### PositionExitPlan 核心字段

- `first_target`：第一目标价（半仓止盈）
- `trail_stop_trigger`：跟踪止损触发条件
- `time_stop_bars`：时间止损 K 线数

## 5. 模块边界

### 5.1 负责

1. `PositionPlan` bootstrap（1R 仓位计算）
2. `PositionExitPlan` 构建（半仓止盈 + 跟踪止损 + 时间止损）
3. position 研究样本与 run 元数据
4. sizing baseline 规则

### 5.2 不负责

1. 市场基础库拥有权（属于 `data`）
2. MALF 计算（属于 `malf`）
3. broker / 订单 / 成交 / 权益曲线（属于 `trade`）
4. 系统总控编排（属于 `system`）
5. 直接接管 `trade_runtime` 写入

## 6. 铁律

1. 仓位以 1R 为基准单位，`risk_per_share × position_size = risk_amount` 必须在 `__post_init__` 校验。
2. `entry_date = signal_date + 1 个交易日`，禁止 T 日成交。
3. `entry_price` 使用 T+1 开盘价，禁止用 T 日收盘价。
4. `PositionPlan` 不直接写 `trade_runtime`；必须经过 `trade` 模块桥接。
5. 研究样本的正式落点进入 `research_lab.duckdb`（L3），不进入 `trade_runtime`。

## 7. 成功标准

1. `PositionPlan` 合同冻结，1R 计算逻辑有测试覆盖
2. `PositionExitPlan` 合同冻结，三类退出条件（半仓止盈 / 跟踪止损 / 时间止损）有明确字段
3. 研究结果可追溯到来源 `PasSignal` run 与策略口径
4. 只有经过桥接迁移，`position` 结果才进入 `trade_runtime`
