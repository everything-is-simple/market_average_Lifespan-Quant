# MALF 月线八态计算规格 / 2026-03-31（重构版）

> 继承来源：父系统 `04-malf-long-trend-definition-and-validation-20260324.md` +
> `09-malf-monthly-close-long-experiment-20260324.md` +
> `11-malf-monthly-long-full-cycle-refinement-20260324.md`

## 1. 定位

月线八态（`monthly_state_8`）是 MALF 计算层的第一层输出。

- 计算层：八态区分月线所处阶段（形成/持续/衰竭/反转 × 牛/熊）
- 执行层：八态收敛为 `long_background_2`（`BULL / BEAR`），参与四格上下文分类

## 2. 八态定义

| 状态 | 含义 | 信号特征 |
|------|------|----------|
| `BULL_FORMING` | 牛市形成中 | 从低点反弹 ≥ 20%，趋势向上但尚未充分展开 |
| `BULL_PERSISTING` | 牛市持续中 | 主升浪，价格持续创新高 |
| `BULL_EXHAUSTING` | 牛市衰竭中 | 高位涨速放缓，顶部信号累积 |
| `BULL_REVERSING` | 牛市反转中 | 牛市明确转折，从高点开始向下 |
| `BEAR_FORMING` | 熊市形成中 | 趋势向下确认，尚未充分展开 |
| `BEAR_PERSISTING` | 熊市持续中 | 主跌浪，价格持续创新低 |
| `BEAR_EXHAUSTING` | 熊市衰竭中 | 低位跌速放缓，底部信号累积 |
| `BEAR_REVERSING` | 熊市反转中 | 从低点开始向上，进入下一轮 BULL_FORMING |

循环顺序：

```text
BULL_FORMING → BULL_PERSISTING → BULL_EXHAUSTING → BULL_REVERSING
     ↓                                                    ↓
BEAR_REVERSING ← BEAR_EXHAUSTING ← BEAR_PERSISTING ← BEAR_FORMING
```

收敛映射：`BULL_*` → `long_background_2 = BULL`，`BEAR_*` → `long_background_2 = BEAR`。

## 3. 判定阈值

阈值定义在 `src/lq/malf/contracts.py`：

| 常量 | 值 | 说明 |
|------|-----|------|
| `MONTHLY_LONG_BULL_REVERSAL_PCT` | 0.20 | 牛市反转确认：从低点反弹 ≥ 20% |
| `MONTHLY_LONG_BEAR_REVERSAL_PCT` | 0.18 | 熊市反转确认：从高点下跌 ≥ 18% |
| `MONTHLY_LONG_MIN_BAR_COUNT` | 2 | 最小月线 K 线数量 |
| `MONTHLY_LONG_BULL_MIN_DURATION_MONTHS` | 6 | 牛市最小持续月数 |
| `MONTHLY_LONG_BEAR_MIN_DURATION_MONTHS` | 4 | 熊市最小持续月数 |
| `MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT` | 25.0 | 牛市最小涨幅 (%) |
| `MONTHLY_LONG_BEAR_MIN_AMPLITUDE_PCT` | 18.0 | 熊市最小跌幅 (%) |
| `MONTHLY_LONG_EXHAUSTION_RATIO` | 0.6 | 衰竭判定：涨/跌速 < 前期 60% |
| `MONTHLY_VALIDATION_LOOKBACK_MONTHS` | 12 | 验证回看月数 |

修改阈值须另开执行卡 + 提供样本验证证据 + 更新 `contracts.py` 常量。

## 4. 五指数体系

| 角色 | 代码 | 说明 |
|------|------|------|
| 主锚 | `000001.SH` | 上证综指 |
| 验证 | `000300.SH` | 沪深 300 |
| 验证 | `399001.SZ` | 深证成指 |
| 验证 | `399006.SZ` | 创业板指 |
| 验证 | `000688.SH` | 科创 50 |

验证规则：至少 2 个验证指数与主锚同向 → 主趋势获得验证。

## 5. 实现入口

- `src/lq/malf/monthly.py` → `classify_monthly_state()`
- `src/lq/malf/monthly.py` → `compute_monthly_strength()`
- `src/lq/malf/contracts.py` → 常量定义
