# MALF 月线八态冻结定义 / 2026-03-31

> 继承来源：父系统 `04-malf-long-trend-definition-and-validation-20260324.md` +
> `09-malf-monthly-close-long-experiment-20260324.md` +
> `11-malf-monthly-long-full-cycle-refinement-20260324.md`
> 阈值来自 `src/lq/malf/contracts.py`（父系统 MarketLifespan-Quant 验证数据）。

## 1. 月线八态定义（冻结）

| 状态 | 含义 | 信号特征 |
|---|---|---|
| `BULL_FORMING` | 牛市形成中 | 从历史/近期低点反弹 ≥ 20%，趋势向上但尚未充分展开 |
| `BULL_PERSISTING` | 牛市持续中 | 主升浪，价格持续创新高，趋势明确向上 |
| `BULL_EXHAUSTING` | 牛市衰竭中 | 高位涨速放缓，顶部信号累积，仍处于高位 |
| `BULL_REVERSING` | 牛市反转中 | 牛市明确转折，从高点开始向下 |
| `BEAR_FORMING` | 熊市形成中 | 趋势向下确认，但熊市尚未充分展开 |
| `BEAR_PERSISTING` | 熊市持续中 | 主跌浪，价格持续创新低，趋势明确向下 |
| `BEAR_EXHAUSTING` | 熊市衰竭中 | 低位跌速放缓，底部信号累积，仍处于低位 |
| `BEAR_REVERSING` | 熊市反转中 | 熊市明确转折，从低点开始向上，进入下一轮 BULL_FORMING |

循环顺序（正常周期）：
```
BULL_FORMING → BULL_PERSISTING → BULL_EXHAUSTING → BULL_REVERSING
     ↓                                                    ↓
BEAR_REVERSING ← BEAR_EXHAUSTING ← BEAR_PERSISTING ← BEAR_FORMING
```

## 2. 判定阈值（冻结，来自父系统验证）

阈值定义在 `src/lq/malf/contracts.py`，不允许随意修改：

| 常量名 | 值 | 说明 |
|---|---|---|
| `MONTHLY_LONG_BULL_REVERSAL_PCT` | 0.20 | 牛市反转确认：从低点反弹 ≥ 20% |
| `MONTHLY_LONG_BEAR_REVERSAL_PCT` | 0.18 | 熊市反转确认：从高点下跌 ≥ 18% |
| `MONTHLY_LONG_MIN_BAR_COUNT` | 2 | 最小月线 K 线数量 |
| `MONTHLY_LONG_BULL_MIN_DURATION_MONTHS` | 6 | 牛市最小持续月数 |
| `MONTHLY_LONG_BEAR_MIN_DURATION_MONTHS` | 4 | 熊市最小持续月数 |
| `MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT` | 25.0 | 牛市最小涨幅 (%) |
| `MONTHLY_LONG_BEAR_MIN_AMPLITUDE_PCT` | 18.0 | 熊市最小跌幅 (%) |
| `MONTHLY_LONG_EXHAUSTION_RATIO` | 0.6 | 衰竭判定：近期涨/跌速 < 前期的 60% |
| `MONTHLY_VALIDATION_LOOKBACK_MONTHS` | 12 | 验证回看月数 |

若要修改阈值，必须：
1. 另开独立执行卡
2. 提供样本验证证据
3. 更新 `contracts.py` 中的常量（不允许直接硬编码在函数体内）

## 3. 五指数体系（冻结）

月线背景分析的正式指数锚：

| 角色 | 代码 | 说明 |
|---|---|---|
| 主锚 | `000001.SH` | 上证综指，唯一主锚，由此给出第一读数 |
| 验证指数 | `000300.SH` | 沪深 300 |
| 验证指数 | `399001.SZ` | 深证成指 |
| 验证指数 | `399006.SZ` | 创业板指 |
| 验证指数 | `000688.SH` | 科创 50 |

验证规则：
- 至少 **2 个**验证指数与主锚同向 → 主趋势已获得验证
- 至少 **2 个**验证指数与主锚反向 → 主趋势受到挑战

代码常量：`PRIMARY_LONG_TREND_INDEX_CODE`、`LONG_TREND_VALIDATION_INDEX_CODES`、`MIN_LONG_TREND_VALIDATION_PASS_COUNT = 2`

## 4. 与旧口径的差异（继承父系统纠偏）

| 旧口径 | 当前正式口径 |
|---|---|
| 长期趋势看周线 | 长期趋势只看月线收盘线 |
| 用 1-2-3 慢确认链 | 用保护位破坏 + 反弹/回撤幅度判定 |
| 衰竭靠定性描述 | 衰竭靠量化速度比较（`EXHAUSTION_RATIO`） |

## 5. 实现入口

- 月线状态判定：`src/lq/malf/monthly.py` → `classify_monthly_state()`
- 月线强度计算：`src/lq/malf/monthly.py` → `compute_monthly_strength()`
- 常量定义：`src/lq/malf/contracts.py`

## 6. 已知实现 Gap（待后续执行卡处理）

当前 `monthly.py` 的 `classify_monthly_state()` 函数存在以下不完整之处：

1. `BEAR_REVERSING` 状态**未被显式返回**——当熊市反转时，代码目前走到 `BULL_REVERSING`
   分支，语义上存在混淆，需要在后续专门的月线状态机执行卡中修正。
2. `BULL_REVERSING` 的触发逻辑当前依赖 `rebound_from_low ≥ 20%` 且 `ma6_direction = False`，
   这与"牛市明确转折"的语义有偏差（应更接近"从高点显著下跌"而非"从低点反弹"）。

上述 gap 不影响 `BOF / PB` 当前主线验证结果，但在正式月线状态机校验卡前，
`BULL_REVERSING / BEAR_REVERSING` 的读数需谨慎使用。
