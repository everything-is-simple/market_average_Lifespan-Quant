# PAS 五 Trigger 冻结层级与地位汇总 / 2026-04-01

> 本文汇总父系统所有已关闭 PAS 结论卡的最终口径，作为本系统的唯一权威参考。
> 不再以父系统原始卡号为行动入口，只以本文结论为准。

## 1. 五 Trigger 冻结地位表

| Trigger | 地位（冻结） | 父系统结论卡 |
|---|---|---|
| `BOF` | `core / primary_trend_driver` | 93 |
| `PB` | `conditional / conditional_assist_driver` | 110, 121 |
| `TST` | `conditional / conditional_assist_driver` | 126 |
| `CPB` | `excluded / rejected`（保留段负收益） | 129, 258 |
| `BPB` | `excluded / not_for_long_alpha` | 93, 131 |

## 2. BOF — core / primary_trend_driver

**父系统卡 93：BOF-only 三年正式回测结论**

- 验证窗口：`2023-01-01 → 2026-03-20`，全市场 A 股
- non-sparse 结果集中在 `BEAR_PERSISTING / BULL_PERSISTING` 两大月线主状态
- persisting 四格（BULL_PERSISTING × MAINSTREAM/COUNTERTREND，BEAR_PERSISTING × MAINSTREAM/COUNTERTREND）均为主力格
- 执行语义：`T+1 open <= T+0 low` 的样本记为 `SKIPPED_INVALID_1R`

**正式口径：**

- BOF 是趋势持续态下的顺势主力 trigger，尤其在牛市持续顺势时更强。
- persisting 四格都允许主线，但 BULL_PERSISTING__MAINSTREAM 是最核心格。
- 其他月线状态（FORMING/EXHAUSTING/REVERSING）也可能触发，但样本稀疏，不作为主力格。

## 3. PB — conditional / conditional_assist_driver

**父系统卡 110, 121：PB 16 格三年正式验证结论**

- 验证窗口：同 BOF，三年全窗口
- 正式准入格：`BULL_PERSISTING__MAINSTREAM`，`BEAR_PERSISTING__COUNTERTREND`
- 其余格或为弱区，或为稀疏格，不准入

**正式口径：**

- PB 只适合少数条件格，更像补充工具，不是通用主力 trigger。
- 区别于 BOF：BOF 在全 persisting 四格，PB 只在两个对角格。
- 第一 PB（`pb_sequence_number == 1`）信号强度高于后续 PB，评分应给额外权重。

## 4. TST — conditional / conditional_assist_driver

**父系统卡 126：TST 独立 16 格正式验证结论**

- 验证窗口：短窗口 + 三年全窗口双重验证
- 正式准入格：`BULL_PERSISTING__MAINSTREAM`，`BEAR_PERSISTING__COUNTERTREND`
- `BEAR_PERSISTING__MAINSTREAM` 和 `BULL_PERSISTING__COUNTERTREND` 为弱区

**正式口径：**

- TST 被验证为"持续态中的条件格 trigger"，不是区间市场通用 trigger。
- 不支持"TST 本身反脆弱"的系统结论（父系统明确不采用）。
- "TST 在区间表现不错"的假说当前无正式证据，禁止作为系统口径。

## 5. CPB — excluded / rejected

**父系统卡 129 + 258：CPB 独立验证 + 三段回测裁决**

- 父系统卡 129：16 格短窗口/全窗口双重验证，条件格有效但不强
- 父系统卡 258：877 只股票三段回测（基准线/校验线/保留段）
  - 基准线 2010-2019：2432 笔，胜率 43.3%，净收益 +3.3万（微正）
  - 校验线 2020-2022：1056 笔，胜率 43.0%，净收益 +11.7万
  - 保留段 2023-2026：1565 笔，胜率 42.2%，净收益 **-33.1万**

**正式口径：**

- CPB 三段回测保留段负收益，未证明正期望，降为 REJECTED。
- `system` 层禁止调用 CPB，与 BPB 同等对待。
- 代码存留但不参与任何主线 runner。

## 6. BPB — excluded / not_for_long_alpha

**父系统卡 93, 131：BPB 全面拒绝结论**

- 三年验证全面未通过
- 代码可以保留（用于历史追溯或研究），但 `system` 层不启用

**正式口径：**

- BPB 永久禁止进入主线，无论未来测试结果如何。
- 下游 alpha 合同只允许消费 `trigger_tier + expected_role + cell_gate + contract_scope`，不允许因"BPB 某日触发"就直接进入交易。

## 7. 价格口径边界说明

**父系统卡 130：五触发器价格口径审计结论**

- 信号层（`PasSignal`）读取 `stock_daily_adjusted`（后复权）
- `position sizing` 层用后复权 `reference_price` 计算 `target_shares`
- 当前长跑验证更接近"研究识别 + 经济收益"口径，不是 raw-execution 口径

**本系统继承：**

- `PasSignal` 是研究层合同，不是执行层合同
- 如需对接 raw-execution（普通散户按真实价格操作），须另开执行层对齐卡

## 8. 铁律

1. 五兄弟地位一经冻结，不得在 `alpha` 模块内擅自调整准入格范围。
2. 条件格判断必须同时验证 `monthly_state` 和 `weekly_flow`，不能只看 `surface_label`。
3. BPB 禁止主线，无例外。
4. TST/CPB 的准入格与 PB 完全相同（均为两格），不得混淆。
5. 本文结论不覆盖退出策略、仓位规划和执行价格，这些属于 `position / trade` 模块。
