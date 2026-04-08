# filter 模块 — 不利条件检测设计 / 2026-04-01

## 1. 设计目标

本文定义 `filter/adverse.py` 的完整算法设计，包括：

1. 5 类不利条件的算法逻辑与参数
2. 每个条件的判断依据与调优边界
3. 主函数执行序列与合并逻辑
4. A4-4（信号冲突）的待实现说明
5. 与 `structure` 模块的协作接口

---

## 2. 参数总览（冻结基线）

| 参数名 | 值 | 所属条件 | 含义 |
|---|---|---|---|
| `COMPRESSION_WINDOW` | 10 | A4-1 | 检测振幅压缩的近期窗口（日） |
| `COMPRESSION_FLAT_THRESHOLD` | 0.005 | A4-1 | 均线斜率归一化绝对值 < 0.5% 视为走平 |
| `COMPRESSION_RANGE_RATIO` | 0.5 | A4-1 | 近期振幅 < 长期振幅 50% 视为压缩 |
| `CHAOS_WINDOW` | 15 | A4-2 | 检测方向混乱的窗口（日） |
| `CHAOS_REVERSAL_COUNT` | 4 | A4-2 | 超过 N 次方向切换视为混乱 |
| `MIN_SPACE_PCT` | 0.05 | A4-3 | 支撑到阻力最小空间 5% |
| `BEAR_PERSISTING_BLOCK` | True | A4-5 | 熊市持续期屏蔽做多（开关） |
| `BEAR_FORMING_BLOCK` | False | A4-5 | 熊市形成期屏蔽做多（关闭 = 允许逆势 BOF） |

---

## 3. A4-1：压缩且无方向

### 3.1 触发条件（AND 关系，两者同时满足）

**条件一：振幅压缩**
```
近 10 日平均日内振幅（adj_high - adj_low 均值）
  < 过去 10~20 日平均日内振幅 × 50%
```

**条件二：均线走平**
```
近 10 日收盘价线性回归斜率（绝对值，归一化）< 0.5%
归一化 = abs(slope) / mean(closes)
```

### 3.2 算法实现

```python
recent = df.tail(10)           # 近期窗口
long_window = df.tail(20).head(10)  # 参照窗口（第11~20日）

compression = recent_range < long_range * 0.5

x = np.arange(10)
slope = np.polyfit(x, closes, 1)[0]
normalized_slope = abs(slope) / mean(closes)
flat = normalized_slope < 0.005

trigger = compression AND flat
```

### 3.3 设计依据

"振幅压缩 + 无方向"是价格进入横盘整理、方向不明的典型状态。在这种状态下：
- trigger 的突破/假突破判断缺乏有效参考（没有明确的上行/下行背景）
- 仓位的止损线设置依据不充分（支撑/阻力位也可能不清晰）

只有振幅压缩同时均线走平时才触发，**单独压缩但有方向（如三角形收敛中）不触发**。

### 3.4 调优边界

| 参数 | 放松（降低过滤） | 收紧（加强过滤） |
|---|---|---|
| `COMPRESSION_RANGE_RATIO` | 降至 0.3（只过滤极度压缩） | 升至 0.7（过滤大部分收窄） |
| `COMPRESSION_FLAT_THRESHOLD` | 升至 0.01（允许更多斜率） | 降至 0.002（只过滤绝对走平） |
| `COMPRESSION_WINDOW` | 缩小到 5（更短期判断） | 扩大到 20（更长期判断） |

---

## 4. A4-2：结构混乱

### 4.1 触发条件

```
近 15 日收盘价序列中，方向切换次数 ≥ 4 次
方向切换定义：close[i] - close[i-1] 的符号与 close[i-1] - close[i-2] 的符号相反
```

### 4.2 算法实现

```python
closes = df.tail(15)["adj_close"].values
changes = 0
for i in range(2, 15):
    prev_dir = closes[i-1] - closes[i-2]
    curr_dir = closes[i]   - closes[i-1]
    if prev_dir * curr_dir < 0:   # 符号相反 = 方向切换
        changes += 1

trigger = changes >= 4
```

### 4.3 设计依据

"频繁方向切换"是锯齿形震荡的量化特征。在结构混乱的市场中：
- 日内高低点没有规律，无法形成可靠的支撑/阻力结构
- PAS 触发器的信号可靠性大幅下降（假信号密集）
- 止损设置容易被噪音触发

### 4.4 限制说明

当前算法对**收盘价**做方向切换计数，可能把正常的"两步上行中的小回调"也计入切换。更精确的方式是对 swing high/low 序列做方向判断（参考 structure 模块的 pivot 逻辑），但当前版本用简单版保持计算效率。

### 4.5 调优边界

| 参数 | 放松 | 收紧 |
|---|---|---|
| `CHAOS_REVERSAL_COUNT` | 升至 6（只过滤极度混乱） | 降至 3（过滤更多震荡） |
| `CHAOS_WINDOW` | 缩小到 10 | 扩大到 20 |

---

## 5. A4-3：空间不足

### 5.1 触发条件

```
(nearest_resistance_price - nearest_support_price) / current_price < 5%
```

### 5.2 算法实现

```python
space_pct = (nearest_resistance - nearest_support) / current_price
trigger = space_pct < 0.05
```

### 5.3 依赖关系

A4-3 依赖 `structure` 模块的输出：
- `nearest_support_price`（最近支撑位价格）
- `nearest_resistance_price`（最近阻力位价格）

**若两者任一为 None，A4-3 自动跳过**（不视为触发）。这个设计是保守的：当结构不明时，宁可放行到 trigger 检测阶段，而不是因为"没有结构信息"就直接过滤掉。

### 5.4 设计依据

5% 的最小空间对应：
- 1R 止损（约 2~3%）+ 第一目标（约 4~5%）的最小运动需求
- 低于 5% 时，即使信号正确也难以获得足够的盈亏比

### 5.5 调优边界

| `MIN_SPACE_PCT` | 效果 |
|---|---|
| 0.03（3%） | 放松：更多股票通过，允许窄幅信号 |
| 0.05（5%） | 当前基线 |
| 0.08（8%） | 收紧：只选高弹性空间 |

---

## 6. A4-4：多重信号冲突（待实现）

### 6.1 当前状态

**A4-4 未实现**，代码中保留了占位注释：
```python
# A4-4: 多重信号冲突 — 同一个股同日不同触发逻辑给出矛盾信号（暂用跨周期背离代替）
```

### 6.2 设计意图

多重信号冲突的原始含义（YTC）：同一个价格行为，从不同 PAS 触发形态的角度看，给出了矛盾的结论。例如：
- 日内看像 BOF（假突破），但更大级别看像 BPB（突破后回踩）
- 这种"形态冲突"说明结构定义本身有歧义，不应入场

### 6.3 实现计划（非当前阻塞项）

当多个 PAS detector 都认为当日有信号，但 `breakout_type` 互相冲突时触发：

```python
# 未来版本：
from lq.alpha.pas.detectors import run_all_detectors
traces = run_all_detectors(code, signal_date, daily_bars, ...)
triggered_patterns = [t.pattern for t in traces if t.triggered]
if len(triggered_patterns) >= 2:
    active.append(AdverseConditionType.SIGNAL_CONFLICT.value)
```

**当前不实现**：需要 filter 反向依赖 alpha 模块，违反当前依赖矩阵（filter → core + malf，不依赖 alpha）。需要设计合适的接口后才能引入。

---

## 7. A4-5：背景不支持

### 7.1 触发条件（OR 关系，任一满足）

```python
# 正式摘要：长期背景为 BEAR，说明主环境不支持做多
long_background_2 == "BEAR"

# 兼容细粒度：若处于 BEAR_PERSISTING，则按最危险背景处理
monthly == "BEAR_PERSISTING"

# 兼容细粒度：BEAR_FORMING 是否屏蔽由开关控制
monthly == "BEAR_FORMING" AND BEAR_FORMING_BLOCK is True

# 正式中期角色：熊市持续 + COUNTERTREND（逆势反弹）视为双重不利
monthly == "BEAR_PERSISTING" AND intermediate_role_2 == "COUNTERTREND"
```

### 7.2 算法实现

```python
def _check_background_not_supporting(malf_ctx: MalfContext | None) -> bool:
    if malf_ctx is None:
        return False          # 无背景信息，保守不过滤

    long_bg = malf_ctx.long_background_2
    inter_role = malf_ctx.intermediate_role_2
    monthly = malf_ctx.monthly_state

    if long_bg != "BEAR":
        return False

    if BEAR_PERSISTING_BLOCK and monthly == "BEAR_PERSISTING":
        return True
    if BEAR_FORMING_BLOCK and monthly == "BEAR_FORMING":
        return True
    if monthly == "BEAR_PERSISTING" and inter_role == "COUNTERTREND":
        return True
    return False
```

### 7.3 开关设计说明

**`BEAR_PERSISTING_BLOCK = True`**（默认开启）：
- 熊市持续期间，系统默认屏蔽所有做多信号
- 理由：主趋势明确向下时，逆势做多的赔率显著偏低

**`BEAR_FORMING_BLOCK = False`**（默认关闭 = 默认放行）：
- `False` 意味着熊市形成期暂不单独屏蔽，由后续 trigger 与其他 adverse 条件继续判断
- 如果改为 `True`，则熊市形成期也会被 A4-5 直接屏蔽
- 当前策略是：保留 `BEAR_FORMING` 作为可配置边界，不默认一刀切屏蔽

### 7.4 正式主轴说明

- `long_background_2` / `intermediate_role_2` / `malf_context_4` 是 A4-5 的正式背景摘要来源
- `monthly_state` / `weekly_flow` 仍可读取，但只用于兼容保留的细粒度阶段差异（如 `BEAR_FORMING` 与 `BEAR_PERSISTING`）

### 7.5 与旧 16 格验证框架的历史关联

A4-5 可以与旧验证资料中的“背景格”做历史映射对照，但这种对照只用于追溯理解，不代表当前正式执行主轴回退到旧 `16-cell`：

| 月线状态 | 当前处理 | 16 格对应 |
|---|---|---|
| BULL_FORMING / BULL_PERSISTING | 不过滤（最佳背景） | 主流牛市格 |
| BULL_EXHAUSTING / BULL_REVERSING | 不过滤（谨慎） | 可用，边界格 |
| BEAR_EXHAUSTING / BEAR_REVERSING | 不过滤（允许逆势反弹） | 反转候选格 |
| BEAR_FORMING | 默认不屏蔽，可配置屏蔽 | 危险格 |
| BEAR_PERSISTING | 屏蔽（当前策略） | 最危险格 |

正式口径保持为：A4-5 的背景合同收敛到 `long_background_2 / intermediate_role_2 / malf_context_4` 这一组 MALF 正式摘要；`monthly_state / weekly_flow` 仅保留兼容细粒度差异，不再把旧 `16-cell` 写成 filter 的未来正式目标态。

---

## 10. 已知限制与未来方向

| 编号 | 限制 | 说明 | 计划 |
|---|---|---|---|
| F1 | A4-4 信号冲突未实现 | 需要 alpha 模块反向接口 | 等待依赖矩阵设计后引入 |
| F2 | A4-2 基于收盘价计数 | 可能把正常回调计为混乱 | 未来改用 swing 序列方向分析 |
| F3 | A4-5 当前只做保守背景屏蔽 | 目前尚未引入按 trigger 分层的更细背景准入，但这不意味着回到旧 `16-cell` 主轴 | 如需增强，只能基于当前正式背景摘要另开卡扩展 |
| F4 | 参数未经回测优化 | 当前参数为经验值 | R3 研究储备：参数回测调优 |
| F5 | 无按触发器区分的过滤规则 | 所有触发器用同一套过滤 | 未来允许 BOF 在熊市形成期通过（单独配置） |
