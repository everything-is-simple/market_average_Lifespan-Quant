# MALF 四格上下文与生命周期三轴排位详细规格 / 2026-04-07（重构版）

> 父系统对应文档：`G:\MarketLifespan-Quant\docs\01-design\modules\malf\28-malf-four-context-and-lifecycle-ranking-charter-20260407.md`

## 1. 目标

本文是 `00-malf-charter` 的详细展开。章程定义了"回答什么"和"怎么回答"，本文定义具体规则。

MALF 对每个股票、每个指数，持续完成同一套经验统计：

1. 把当前中级波段放进可比的四格上下文。
2. 把它与该标的历史上同类已完成中级波段逐一比较。
3. 输出"当前趋势生命走到哪里了"的原始排位读数与四分位辅助标签。

## 2. 权威来源

书义锚点固定为两张图：

1. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_160_img-54.jpeg.png`
2. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_345_img-57.jpeg.png`

系统吸收口径：

1. 用历史已发生的中级趋势事实，估计当前趋势位于其生命周期分布的什么位置。
2. 主读数必须保留"原味历史排位"，不先归一化。
3. 四分位只是压缩表达，不是主读数。
4. 先尊重每个标的自己的历史，再谈 pooled 背景。

## 3. 什么是趋势的生命

当前这段中级波段，相对于该标的历史上同类中级波段，已经走到了多远、多久、多密。

三把尺子：

1. **波动幅度**：这段中级波段已走出的价格振幅。
2. **时间跨度**：这段中级波段已持续的交易时间。
3. **新价结构**：这段中级波段推进过程中，创新价事件的节奏。

新价结构包含两个维度：

- **次数**：当前波段第几次创新高/新低（牛市计新高，熊市计新低）。
- **间隔**：相邻两次创新价之间的交易日数。间隔放大 = 趋势活力衰竭的早期信号。

这是立花义正「新高日」思想的计算层实现，扩展为同时覆盖新高与新低。

## 4. 波段层级与四格前置

寿命统计的对象是中级波段（`INTERMEDIATE` wave）。

1. `LONG` 只负责给 `INTERMEDIATE` 提供牛熊背景。
2. `SHORT` 只服务转折确认与预警，不承担寿命统计主读数。
3. 每条中级波段必须先进入四格之一，再允许进入生命周期排位。

先分类再排位，不是为了把市场说复杂，而是为了避免把本质不同的中级波段混排。

## 5. 四格上下文

| 格 | 含义 |
|----|------|
| `BULL_MAINSTREAM` | 长期牛市，中级波段顺势 |
| `BULL_COUNTERTREND` | 长期牛市，中级波段逆势 |
| `BEAR_MAINSTREAM` | 长期熊市，中级波段顺势 |
| `BEAR_COUNTERTREND` | 长期熊市，中级波段逆势 |

规则：

1. `BULL / BEAR` 回答长期背景是谁。
2. `MAINSTREAM / COUNTERTREND` 回答当前中级波段相对长期背景是顺势还是逆势。
3. 只有进入同一格的历史中级波段，才允许拿来比较生命周期。

## 6. 历史样本池

对每个 `entity_code`、每个 `malf_context_4`，维护一组历史已完成中级波段样本池。

规则：

1. 只收录该标的自身历史上已完成的 `INTERMEDIATE` wave。
2. 只与同一 `malf_context_4` 的历史波段比较。
3. 当前活跃波段可被排位，但不得反向进入自己的历史样本池。

## 7. 三轴原始排位

正式三轴主读数固定为原始排位区间：

| 轴 | 字段 |
|----|------|
| 波动幅度 | `amplitude_rank_low / amplitude_rank_high / amplitude_rank_total` |
| 时间跨度 | `duration_rank_low / duration_rank_high / duration_rank_total` |
| 新价结构 | `new_price_rank_low / new_price_rank_high / new_price_rank_total` |

经验含义：

1. 若当前波段幅度落在 `28/281 -- 29/281`，按原始历史排位原样保存，不先压成 `0.10` 或 `10%`。
2. 若当前波段时间落在 `30/281 -- 31/281`，同样按原始历史排位保存。
3. 若当前波段新价结构落在 `40/281 -- 41/281`，同样按原始历史排位保存。

补充规则：

1. `low / high` 表示当前活跃波段夹在历史样本的哪两个相邻名次之间。
2. `total` 表示该标的、该四格上下文下可比较历史样本总数。
3. 若当前值正好与某一历史名次重合，允许 `low = high`。

## 8. 总生命区间与四分位

### 8.1 总生命区间

三轴小值/大值简单相加：

| 字段 | 公式 |
|------|------|
| `lifecycle_rank_low` | `amplitude_rank_low + duration_rank_low + new_price_rank_low` |
| `lifecycle_rank_high` | `amplitude_rank_high + duration_rank_high + new_price_rank_high` |
| `lifecycle_rank_total` | `amplitude_rank_total + duration_rank_total + new_price_rank_total` |

### 8.2 四分位压缩

先后顺序不可逆：原始排位 → 总生命区间 → 四分位。

| 层级 | 字段 |
|------|------|
| 轴级 | `amplitude_quartile` / `duration_quartile` / `new_price_quartile` |
| 执行级 | `lifecycle_quartile` |

`lifecycle_quartile` 是辅助字段，不得覆盖三轴原始排位读数，也不得覆盖 `lifecycle_rank_low / high`。

推导规则：

1. `lifecycle_quartile` 必须晚于 `lifecycle_rank_low / high` 产生。
2. 第一版允许仅根据 `lifecycle_rank_low / high` 所落的大致区间，给出辅助四分位。
3. 若后续需要更复杂的联合规则，必须另开卡。

## 9. execution_context_snapshot 桥表

`malf.execution_context_snapshot` 把执行需要的上下文与寿命读数物化为一张表。

字段清单：

| 类别 | 字段 |
|------|------|
| 定位 | `entity_scope` / `entity_code` / `calc_date` / `active_wave_id` |
| 上下文 | `long_background_2` / `intermediate_role_2` / `malf_context_4` |
| 波幅排位 | `amplitude_rank_low` / `amplitude_rank_high` / `amplitude_rank_total` |
| 时间排位 | `duration_rank_low` / `duration_rank_high` / `duration_rank_total` |
| 新价排位 | `new_price_rank_low` / `new_price_rank_high` / `new_price_rank_total` |
| 总生命 | `lifecycle_rank_low` / `lifecycle_rank_high` / `lifecycle_rank_total` |
| 四分位 | `amplitude_quartile` / `duration_quartile` / `new_price_quartile` / `lifecycle_quartile` |

## 10. 与 PAS / position 的接口

`PAS` 正式消费：`malf_context_4` + 三轴 `_rank_*` + `lifecycle_rank_*` + 四分位。

`position` 正式消费同一组字段，用于统计准入与资金使用。

接口方向：

1. 先让 MALF 给出正确的生命周期读数。
2. 再让 PAS / position 基于这些读数做决策。
3. 禁止反过来为了迁就固定仓位而篡改 MALF 生命周期定义。

## 11. 成功标准

1. 四格上下文与生命周期三轴原始排位已写入正式设计/规格。
2. `execution_context_snapshot` 桥表已定义并可落盘。
3. 后续 runner / PAS / position 都以 `execution_context_snapshot` 为消费入口。
4. 任何人问"MALF 的生命体现在哪里"，答案首先回到历史中级波段三轴原始排位。
