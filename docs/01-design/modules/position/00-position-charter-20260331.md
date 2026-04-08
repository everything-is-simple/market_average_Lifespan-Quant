# position 模块章程 / 2026-03-31（2026-04-01 增补）

## 1. 血统与来源

| 层代 | 系统 | 状态 | 主要吸收点 |
|---|---|---|---|
| 理论源头 | 《交易圣经》第8章 — 布伦特·奔富 | 冻结吸收 | 9种反马丁格尔 sizing 策略、风险优先原则、评价框架 |
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma\positioning\` | 思想原型已收口 | sizing/partial-exit 双赛道分离、研究卡序列结构、no MSS/IRS 铁律 |
| 父系统 | `G:\MarketLifespan-Quant\src\mlq\position\` | 正式定型，完整实现 | 5表 schema、控制基线对、position 状态机、v1 partial-exit 契约 |
| 本系统 | `H:\Lifespan-Quant\src\lq\position\` | 继承演进 | 继承父系统全部合同，本地化 A 股整手约束与 1R 计算 |

### 1.1 从书中冻结吸收的核心原则

1. **生存优先**：交易目标首先是生存，其次才是利润；资金管理不能把消极期望变成积极期望
2. **反马丁格尔铁律**：亏时缩仓、盈时加仓；马丁格尔策略（亏时补仓）仅作反例保留，不进入任何正式候选
3. **9 种策略家族**（详见设计文档01）：`single_lot / fixed_risk / fixed_capital / fixed_ratio / fixed_unit / williams_fixed_risk / fixed_percentage / fixed_volatility / fixed_notional`
4. **固定比例（fixed_percentage）= 专业首选**：在连续亏损时自动缩减风险，长跑表现最佳；本系统的 operating 控制基线选用 `fixed_notional`（简化版）而非 `fixed_percentage`，因为当前尚无足够历史证据
5. **固定比例（fixed_ratio）= 小账户最佳**：每合同要求相同利润贡献，灾难性损失恢复最稳健

### 1.2 从爷爷系统（EmotionQuant-gamma）吸收的结论

1. **sizing 和 partial-exit 必须分两赛道独立验证**，混跑无法得到干净证据
2. **no MSS / no IRS 铁律**：sizing 决策不引入市场情绪层和行业层，只用 entry baseline
3. **sizing 家族全部回放结果**：在爷爷系统的正式实验中，`no_candidate_survives_single_lot_sanity`；即没有任何 sizing 策略在单手对照组下显著胜出，这是重要历史证据
4. **partial-exit 研究结论**：`TRAIL_SCALE_OUT_25_75`（25% 第一腿止盈 + 75% 跟踪止损）在爷爷系统中为 provisional leader
5. **控制基线对**：`FIXED_NOTIONAL_CONTROL`（operating）+ `SINGLE_LOT_CONTROL`（floor sanity）为冻结基线

### 1.3 从父系统（MarketLifespan-Quant）继承的合同

1. **5 张研究表口径**：`position_run / position_policy_registry / position_sizing_snapshot / position_exit_plan / position_exit_leg` 仍是从父系统继承的目标态 research schema，但当前仓库尚未独立实现 position 的 bootstrap / pipeline / 落库写入
2. **Position 状态机**：`OPEN → PARTIAL_EXIT_PENDING → OPEN_REDUCED → FULL_EXIT_PENDING → CLOSED`
3. **v1 partial-exit 契约**：多腿 SELL 订单，stop-loss / force-close 永远是硬全平，不进 partial-exit 路径
4. **入场执行语义**：`signal_date = T`，`execute_date = T+1`，成交价 = T+1 开盘价
5. **A 股整手约束**：`target_shares = floor(raw / lot_size) * lot_size`，最小 100 股，结果不满一手则向上取整到 `lot_size`

---

## 2. 模块定位

`position` 是仓位与退出研究模块。

**一句话定位**：  
`把冻结后的 PasSignal 转化为可验证的仓位规划与退出合同；当前已实现合同层与 sizing/exit 计算，独立 research_lab 落库仍待后续 pipeline/bootstrap 补齐。`

本模块**不是交易账户**，输出的是研究层合同对象，经桥接后才进入正式交易运行态。

---

## 3. 正式输入

1. `PasSignal`（来自 `alpha/pas` 模块，已冻结后的正式 run；可携带 `execution_context_snapshot` 的正式生命周期字段）
2. 交易日历辅助（用于 `next_trading_day(signal_date)` 计算 `entry_date`）
3. 调用方传入的 `entry_price`（通常按 `T+1` 开盘价语义提供；当前 `market_base` 查询发生在调用方如 `trade`，不是 `position` 自身）
4. `MalfContext`（可选，兼容追溯；当前不参与 sizing 决策）

当前约束：

1. `position` 可以接收 `PasSignal` 中的正式生命周期字段，但当前 sizing 公式不得因这些字段而改变。
2. 正式生命周期字段在本阶段的作用是为后续 sizing 升级预留合同，而不是立即引入权重调节。

---

## 4. 正式输出

### 4.1 目标态落盘输出（research_lab.duckdb，当前尚未独立实现）

| 表名 | 内容 |
|---|---|
| `position_run` | 每次 pipeline 运行元数据 |
| `position_policy_registry` | 本次 run 使用的 sizing / exit policy 元数据 |
| `position_sizing_snapshot` | 每笔信号的仓位快照（target_shares, target_notional, sizing_payload_json） |
| `position_exit_plan` | 每笔信号的完整退出计划合同 |
| `position_exit_leg` | 每个退出计划的各腿明细 |

当前代码中已实现的是 `PositionPlan / PositionExitPlan` 合同与对应计算函数；上表所述独立 research schema 仍属于待补齐目标态，不得在其他正式文档中表述为“已经落地现状”。

### 4.2 当前已实现的对外合同（传递给 trade 模块）

| 合同 | 类型 | 传递时机 |
|---|---|---|
| `PositionPlan` | `dataclass`（冻结） | 经桥接进入 trade |
| `PositionExitPlan` | `dataclass`（冻结） | 当前已实现合同与生成函数，但尚未核实为 trade 主线直接消费入口 |

---

## 5. Sizing 家族注册表（摘要）

详见 `01-position-sizing-family-design-20260401.md`。

| 策略名 | 英文标识 | 角色 |
|---|---|---|
| 单手对照 | `SINGLE_LOT_CONTROL` | floor sanity（地板验证） |
| 固定名义金额 | `FIXED_NOTIONAL_CONTROL` | **operating 控制基线**（当前主线默认）|
| 固定风险 | `FIXED_RISK` | 最保守，回撤最小但利润低 |
| 固定资本 | `FIXED_CAPITAL` | 加仓最激进，灾难性下跌风险高 |
| 固定比例 | `FIXED_RATIO` | 小账户首选，每合同等额利润贡献 |
| 固定单位 | `FIXED_UNIT` | 加仓较快，适合早期账户 |
| 威廉斯固定风险 | `WILLIAMS_FIXED_RISK` | 以最大损失为锚，大账户候选 |
| 固定百分比 | `FIXED_PERCENTAGE` | 专业首选，长跑表现最佳 |
| 固定波幅 | `FIXED_VOLATILITY` | ATR 自适应（海龟法），最市场敏感 |

当前研究线冻结结论（继承爷爷系统）：  
**`no_candidate_survives_single_lot_sanity`**，即没有任何策略在当前 BOF baseline 下显著胜出单手对照组。在正式研究卡完成前，主线继续使用 `FIXED_NOTIONAL_CONTROL`。

---

## 6. 退出合同铁律

详见 `02-position-partial-exit-design-20260401.md`。

1. **止损（STOP_LOSS）= 硬全平**，不进 partial-exit 路径
2. **强制平仓（FORCE_CLOSE）= 硬全平**，立即清空 remaining_quantity
3. **v1 partial-exit = 多腿 SELL 订单**（每腿一张 SELL，单腿单次撮合）
4. **第一腿止盈**：入场 + 1R，卖出 half_lot（A 股整手约束向下取整）
5. **runner 腿**：`position` 当前只产出 runner 腿合同与初始 `trailing_stop_trigger` 占位值；真正基于持仓最高价动态上移的跟踪止损由 `trade.management` 在运行期管理

---

## 7. 模块边界

### 7.1 负责

1. `PositionPlan` bootstrap（1R 仓位计算 + A 股整手约束）
2. `PositionExitPlan` 构建（第一腿止盈 + runner 跟踪止损 + 时间止损）
3. 冻结 position research schema 与写权边界，但当前不把“已独立写入 `research_lab`”冒充为完成事实
4. sizing 家族注册与 baseline 管理
5. partial-exit 合同冻结（`position_exit_plan / position_exit_leg`）

### 7.2 不负责

1. 市场基础库拥有权（属于 `data`）
2. MALF 计算（属于 `malf`）
3. broker / 订单 / 成交 / 权益曲线（属于 `trade`）
4. 系统总控编排（属于 `system`）
5. 直接写 `trade_runtime`

---

## 8. 铁律

1. **1R 基准**：`risk_unit = entry_price − initial_stop`；`risk_unit > 0` 必须满足；若 `≤ 0` 则退化为 `entry_price × 0.005`
2. **T+1 开盘执行**：`entry_date = next_trading_day(signal_date)`，成交价 = T+1 开盘价
3. **A 股整手**：`target_shares = floor(raw / lot_size) * lot_size`，最小结果不满一手则取 `lot_size`
4. **研究层写权边界**：若后续补 position 独立落库，其写权只能落在 `research_lab` 中属于 position 的 5 张表；在当前未实现独立 pipeline 之前，禁止把目标态写权表述成“已落地现状”
5. **no MSS / no IRS 铁律**：sizing 决策不引入 MALF surface label、MSS 市场情绪层、IRS 行业层作为权重调节
6. **桥接才进 trade**：`PositionPlan / PositionExitPlan` 必须经过 `trade` 模块桥接，不能直接接管交易执行

---

## 9. 成功标准

1. `PositionPlan` 合同冻结，1R 计算逻辑有测试覆盖（含负 risk_unit 退化情形）
2. `PositionExitPlan` 合同冻结，两腿结构（first_target + runner）有明确字段
3. 当前最小完成标准不要求 position 独立 research schema 已落库；若后续补齐 bootstrap / pipeline，必须另开卡并同步升级本文档
4. sizing 家族注册表已定义，`FIXED_NOTIONAL_CONTROL + SINGLE_LOT_CONTROL` 基线对可运行
5. partial-exit 退出计划当前至少可生成 `PositionExitPlan` 合同对象；独立 `position_exit_plan + position_exit_leg` 落库仍属待补目标态
6. 只有经过桥接迁移，`position` 结果才进入 `trade_runtime`

---

## 10. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-position-charter-20260331.md`（本文） | 模块章程、血统、边界、铁律 |
| `01-position-sizing-family-design-20260401.md` | 9 种 sizing 策略、公式、A 股适配、评价框架 |
| `02-position-partial-exit-design-20260401.md` | Position 状态机、ID 规则、v1 多腿合同、研究表 schema |
