# position 模块 — Sizing 家族设计 / 2026-04-01

## 1. 设计目标

本文定义 `position` 模块支持的 9 种 sizing 策略的：

1. 公式与 A 股适配规则
2. 控制基线对（operating + floor sanity）
3. 研究评价框架（评价指标与证据口径）
4. 当前主线选用理由

本文不回答：
- 哪种策略未来升级为主线默认
- 是否引入 MSS / IRS 参与 sizing 决策

---

## 2. 全局 A 股适配规则

所有 sizing 策略共享以下 A 股约束，优先于任何策略公式：

```
lot_size = 100                      # 最小交易单位（A 股标准一手）
target_shares = floor(raw / 100) * 100
if target_shares == 0:
    target_shares = 100             # 不满一手时向上取整到最小一手
target_notional = target_shares * entry_price
```

此外，所有策略均遵守：
- **执行语义**：`signal_date = T`，`entry_date = T+1`，`entry_price = T+1 开盘价`
- **1R 基准**：`risk_unit = entry_price - initial_stop`；若 `risk_unit ≤ 0` 则退化为 `entry_price × 0.005`
- **initial_stop**：`signal_low × (1 - stop_buffer_pct)`，默认 `stop_buffer_pct = 0.005`

---

## 3. 策略详细设计

### 3.1 SINGLE_LOT_CONTROL — 单手对照（地板验证）

**定位**：最朴素的 floor sanity 对照组，用于验证其他策略是否优于最小投入。

**公式**：
```
target_shares = lot_size          # 固定一手（100股）
target_notional = 100 * entry_price
```

**评价意义**：  
如果某 sizing 策略在同一 entry baseline 下无法显著胜出单手对照组，则该策略不具备升级价值。  
（爷爷系统历史结论：当前 BOF baseline 下 `no_candidate_survives_single_lot_sanity`）

---

### 3.2 FIXED_NOTIONAL_CONTROL — 固定名义金额（当前 operating 控制基线）

**定位**：当前主线 operating 控制基线。每笔交易分配固定名义金额，与账户余额解耦。

**公式**：
```
raw_shares = fixed_notional / entry_price
target_shares = floor(raw_shares / lot_size) * lot_size  # A股整手
target_notional = target_shares * entry_price
```

**默认参数**：`fixed_notional = 100_000`（10 万元）

**选用理由**：  
- 结果直观可比，适合研究阶段的 cross-signal 对照
- 不依赖账户余额历史序列，避免路径依赖
- 与 `SINGLE_LOT_CONTROL` 配对构成稳健的 baseline pair

---

### 3.3 FIXED_RISK — 固定风险

**理论来源**：《交易圣经》第8章，最保守的反马丁格尔策略。

**公式**：
```
risk_budget = capital_base × risk_pct          # 例：100万 × 0.5% = 5000元
risk_per_share = entry_price - initial_stop    # = risk_unit
raw_shares = risk_budget / risk_per_share
target_shares = floor(raw_shares / lot_size) * lot_size
```

**默认参数**：`risk_pct = 0.005`（0.5%），`capital_base = 1_000_000`

**特性**：
- 利润最低，回撤最小（最大回撤约 5%）
- 净利润/跌幅比（价值回报）最高（约 32）
- 不允许小账户（fixed_notional 不足 1 手时跳过信号）

---

### 3.4 FIXED_CAPITAL — 固定资本单位

**理论来源**：《交易圣经》第8章，最激进的加仓策略（积累合同最快）。

**公式**：
```
capital_unit = capital_step                    # 例：每 2.5 万元增加 1 手
contracts = floor(account_equity / capital_unit)
target_shares = min(contracts, max_contracts) * lot_size
```

**默认参数**：`capital_step = 25_000`，`max_contracts = 100`

**风险提示**：  
灾难性损失下跌可达 58%（《交易圣经》数据），需要 140% 收益才能恢复。**当前不作为候选，只作对比保留。**

---

### 3.5 FIXED_RATIO — 固定比例（小账户推荐）

**理论来源**：《交易圣经》第8章，每合同要求相同利润贡献，灾难性损失恢复最稳健。

**公式**：
```
# 合同数 n 从 1 开始，每增加 1 手需要固定利润增量 delta
delta_amount = n * (n - 1) / 2 * delta_ratio * profit_per_contract
next_level = account_equity - delta_amount
n = floor(sqrt(2 * account_equity / delta_ratio / profit_per_contract + 0.25) - 0.5)
target_shares = min(n, max_contracts) * lot_size
```

**默认参数**：`delta_ratio = 0.5`（每新增 1 合同需 50% 的合同利润贡献），`max_contracts = 20`

**特性**：
- 灾难性损失最大下跌约 13%，恢复只需 15%（不对称杠杆最小）
- 加仓速度比 `FIXED_UNIT` 慢，比 `FIXED_PERCENTAGE` 快
- 适合小账户（< 50 万）

---

### 3.6 FIXED_UNIT — 固定单位数量

**理论来源**：《交易圣经》第8章，每固定资产增量增加 1 手。

**公式**：
```
unit_increment = account_equity / unit_size    # 每 unit_size 增加 1 手
contracts = floor(account_equity / unit_size)
target_shares = min(contracts, max_contracts) * lot_size
```

**默认参数**：`unit_size = 50_000`，`max_contracts = 20`

**特性**：
- 加仓最快（在 10 万目标内第一个达到），利润最高
- 标准差最大（22.8%），灾难性下跌约 44%
- 适合早期账户激进模式，不作为长期默认

---

### 3.7 WILLIAMS_FIXED_RISK — 威廉斯固定风险

**理论来源**：《交易圣经》第8章，以最大允许损失为锚确定仓位。

**公式**：
```
max_loss_cap = capital_base × max_loss_pct     # 例：100万 × 1.5% = 15000元
raw_shares = max_loss_cap / risk_unit          # risk_unit = entry - stop
target_shares = floor(raw_shares / lot_size) * lot_size
```

**默认参数**：`max_loss_pct = 0.015`（1.5%），`capital_base = 1_000_000`

**特性**：
- 大账户候选（需要 30 万以上起步）
- 在 100 万目标时表现均衡（下跌约 14%，价值回报约 12）
- 不允许小账户入场

---

### 3.8 FIXED_PERCENTAGE — 固定百分比（专业首选）

**理论来源**：《交易圣经》第8章，专业交易者首选，破产风险最低。

**公式**：
```
risk_budget = account_equity × risk_pct        # 账户余额的固定百分比
risk_per_share = risk_unit                     # entry - stop
raw_shares = risk_budget / risk_per_share
target_shares = floor(raw_shares / lot_size) * lot_size
```

**默认参数**：`risk_pct = 0.01`（1%，按账户余额动态），`capital_base = 1_000_000`（初始账户基准）

**特性**：
- 连续亏损时自动减仓，保护账户不被侵蚀
- 在长跑模式（100万利润目标）下表现最好（速度 34% 样本集达标）
- 与 `FIXED_VOLATILITY` 共同被书中推荐为长跑首选
- **未来主线升级候选**：当有足够历史证据后可替换 `FIXED_NOTIONAL_CONTROL`

---

### 3.9 FIXED_VOLATILITY — 固定波幅（ATR 自适应，海龟法）

**理论来源**：《交易圣经》第8章，理查德·丹尼斯（海龟）交易法。

**公式**：
```
atr_n = ATR(10)                                # 10 日均幅（日线 True Range 均值）
volatility_amount = atr_n * entry_price / close  # 换算成每股金额
vol_budget = capital_base × vol_pct            # 例：100万 × 2% = 20000元
raw_shares = vol_budget / volatility_amount
target_shares = floor(raw_shares / lot_size) * lot_size
```

**默认参数**：`vol_pct = 0.02`（2%），`atr_period = 10`，`capital_base = 1_000_000`

**特性**：
- 市场波动大时自动减仓，波动小时自动加仓（最市场自适应）
- 加仓速度最慢（需要 76% 样本集才达 100 合同上限）
- 灾难性损失下跌约 23%，标准差最小（4.8%）
- 需要 `market_base` 中的 ATR 数据支撑

---

## 4. 控制基线对

```
Operating Control:  FIXED_NOTIONAL_CONTROL    (100,000 固定名义金额)
Floor Sanity:       SINGLE_LOT_CONTROL        (100股 最小一手)
```

两者构成当前研究层的稳定对照基准。所有其他策略必须同时与这两个基线对比，才算完整的研究证据。

---

## 5. 研究评价框架

### 5.1 必选评价指标

| 指标 | 说明 |
|---|---|
| `net_pnl` | 净利润（含手续费） |
| `ev_per_trade` | 每笔期望值 |
| `profit_factor` | 盈利总额 / 亏损总额 |
| `max_drawdown_pct` | 最大回撤百分比 |
| `max_drawdown_usd` | 最大回撤金额 |
| `value_return_ratio` | `net_pnl / max_drawdown_usd`（价值回报比） |
| `trade_count` | 总交易笔数 |
| `avg_position_size` | 平均持仓股数 |
| `avg_notional` | 平均名义金额 |
| `exposure_utilization` | 资金使用率（已用 / 总可用） |
| `pnl_std_pct` | 利润标准差（波动性） |

### 5.2 风险路径指标（ruin-sensitive）

| 指标 | 说明 |
|---|---|
| `consecutive_loss_max` | 最大连续亏损笔数 |
| `recovery_pct_required` | 从最大回撤恢复所需上涨百分比（不对称杠杆） |
| `ruin_path_count` | 账户跌至初始余额 50% 以下的路径数 |
| `contracts_at_max_dd` | 最大回撤时的合同数 |

### 5.3 证据类型

| 类型 | 内容 | 格式 |
|---|---|---|
| `matrix` | 各 sizing family 的对照矩阵（同一 entry baseline 下） | 宽表 CSV / DuckDB 查询 |
| `digest` | retained / no-go 裁决摘要 | markdown |
| `record` | 每张研究卡的正式结论 | `docs/03-execution/` 下的 conclusion 文件 |

---

## 6. 研究赛道分离原则（继承爷爷系统）

```
S1 / sizing lane:
    - 固定 entry baseline（当前：BOF PAS 信号）
    - 固定 exit 语义（全平，STOP_LOSS + TRAILING_STOP）
    - 只比较不同 sizing family
    - S1 未完成前不允许混入 partial-exit

S2 / partial-exit lane:
    - 固定 entry baseline
    - 固定 sizing baseline（FIXED_NOTIONAL_CONTROL operating）
    - 只比较不同 exit family
    - 不改 entry / sizing
```

---

## 7. 当前状态与未来演进路径

| 阶段 | 条件 | 行动 |
|---|---|---|
| 当前 | 无历史回测证据 | 使用 `FIXED_NOTIONAL_CONTROL` 作为主线 operating baseline |
| 阶段 A | S1 sizing 回放完成 | 若有候选通过 single_lot sanity，升级为 retained candidate |
| 阶段 B | retained candidate 稳健性验证 | 替换 `FIXED_NOTIONAL_CONTROL` 为正式候选 |
| 阶段 C | 大账户（>100万） | 考虑 `FIXED_PERCENTAGE` 或 `FIXED_VOLATILITY` |

禁止操作：
1. 在 S1 未完成前把 sizing 和 partial-exit 混跑
2. 把书中公式直接当真，不做 formal replay
3. 借 MSS / IRS 给 sizing 加解释性特例
4. 直接把研究结果宣布为主线默认参数
