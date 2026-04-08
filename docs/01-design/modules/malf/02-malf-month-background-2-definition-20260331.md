# MALF 月线牛熊判定 / 2026-04-07（重构版）

> 继承来源：父系统 `04-malf-long-trend-definition-and-validation-20260324.md`

## 1. 定位

月线直接输出 `long_background_2`（`BULL / BEAR`），参与四格上下文分类。

## 2. 定义

| 值 | 含义 |
|----|------|
| `BULL` | 当前处于长期牛市背景 |
| `BEAR` | 当前处于长期熊市背景 |

## 3. 判定阈值

阈值定义在 `src/lq/malf/contracts.py`：

| 常量 | 值 | 说明 |
|------|-----|------|
| `MONTHLY_LONG_BULL_REVERSAL_PCT` | 0.20 | 牛市确认：从低点反弹 ≥ 20% |
| `MONTHLY_LONG_BEAR_REVERSAL_PCT` | 0.18 | 熊市确认：从高点下跌 ≥ 18% |
| `MONTHLY_LONG_MIN_BAR_COUNT` | 2 | 最小月线 K 线数量 |
| `MONTHLY_LONG_BULL_MIN_DURATION_MONTHS` | 6 | 牛市最小持续月数 |
| `MONTHLY_LONG_BEAR_MIN_DURATION_MONTHS` | 4 | 熊市最小持续月数 |
| `MONTHLY_LONG_BULL_MIN_AMPLITUDE_PCT` | 25.0 | 牛市最小涨幅 (%) |
| `MONTHLY_LONG_BEAR_MIN_AMPLITUDE_PCT` | 18.0 | 熊市最小跌幅 (%) |
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
- `src/lq/malf/contracts.py` → 常量定义

## 6. 历史化说明

- `monthly_state_8` 可以保留为研究、诊断与兼容字段。
- 但本系统当前正式执行口径中，月线只对外输出 `long_background_2`（`BULL / BEAR`）。
- 放弃“月线八态作为执行主轴”的原因是：样本切分过细，会先切碎中级波段的历史样本池，不利于寿命统计保留原味历史排位。
