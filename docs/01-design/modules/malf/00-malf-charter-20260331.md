# MALF 模块章程 / 2026-04-07（重构版）

## 1. 模块定位

`malf`（Market Average Lifespan Framework）是**趋势生命周期经验统计系统**。

它回答一个问题：**当前趋势的生命走到哪里了？**

## 2. 血统

父系统 `G:\MarketLifespan-Quant\docs\01-design\modules\malf\` 是本模块设计的权威参考。
当前权威设计文档：父系统 `28` 号（四格上下文与生命周期排名章程）。

## 3. 回答方法

回答分两步，二者不可分割——上下文分类让排位有意义，排位是系统的核心输出：

**第一步：上下文分类** — 把当前中级波段归入四格之一，使历史样本可比。

| 计算 | 产出 | 取值 |
|------|------|------|
| 月线价格结构判断长期牛熊 | `long_background_2` | `BULL / BEAR` |
| 周线相对月线判断顺势逆势 | `intermediate_role_2` | `MAINSTREAM / COUNTERTREND` |
| 组合 | `malf_context_4` | 四格（见 §4） |

**第二步：生命周期排位** — 在同一四格内，用三把尺子度量当前波段在历史同类中的位置。

| 尺子 | 度量 | 回答 |
|------|------|------|
| 波动幅度 | 当前波段已走出的价格振幅 | 走了多远 |
| 时间跨度 | 当前波段已持续的交易时间 | 走了多久 |
| 新价结构 | 创新高/新低的次数与间隔 | 推进节奏如何 |

每把尺子产出原始历史排位区间 → 三轴相加得到总生命区间 → 四分位压缩辅助执行。

## 4. 四格上下文

| 格 | 含义 |
|----|------|
| `BULL_MAINSTREAM` | 长期牛市，中级波段顺势 |
| `BULL_COUNTERTREND` | 长期牛市，中级波段逆势 |
| `BEAR_MAINSTREAM` | 长期熊市，中级波段顺势 |
| `BEAR_COUNTERTREND` | 长期熊市，中级波段逆势 |

规则：

1. 只有同一标的、同一格内的历史已完成中级波段，才是可比样本。
2. 当前活跃波段可被排位，但不得反向进入自己的历史样本池。

## 5. 生命周期三轴

### 5.1 三轴定义

| 轴 | 度量对象 | 含义 |
|----|----------|------|
| 波动幅度 | 当前中级波段已走出的价格振幅 | 走了多远 |
| 时间跨度 | 当前中级波段已持续的交易时间 | 走了多久 |
| 新价结构 | 创新高/新低的次数与间隔 | 推进节奏如何 |

**新价结构**包含两个维度：

- **次数**：当前波段第几次创新高/新低（牛市计新高，熊市计新低）。
- **间隔**：相邻两次创新价之间的交易日数。间隔放大 = 趋势活力衰竭的早期信号。

这是立花义正「新高日」思想的计算层实现，扩展为同时覆盖新高与新低。

### 5.2 原始排位

每轴输出原始历史排位区间：

| 字段 | 含义 |
|------|------|
| `amplitude_rank_low / high / total` | 波幅在历史同类中的排位区间 |
| `duration_rank_low / high / total` | 时间在历史同类中的排位区间 |
| `new_price_rank_low / high / total` | 新价结构在历史同类中的排位区间 |

- `low / high`：当前波段夹在历史样本的哪两个相邻名次之间。
- `total`：该标的、该四格下可比历史样本总数。
- 若当前值恰好与某历史名次重合，允许 `low = high`。
- 保留原味排位（如 `28/281 -- 29/281`），不先归一化。

### 5.3 总生命区间

三轴小值/大值简单相加：

| 字段 | 公式 |
|------|------|
| `lifecycle_rank_low` | `amplitude_rank_low + duration_rank_low + new_price_rank_low` |
| `lifecycle_rank_high` | `amplitude_rank_high + duration_rank_high + new_price_rank_high` |
| `lifecycle_rank_total` | `amplitude_rank_total + duration_rank_total + new_price_rank_total` |

### 5.4 四分位压缩

| 字段 | 含义 |
|------|------|
| `amplitude_quartile` | 波幅轴四分位（Q1 / Q2 / Q3 / Q4） |
| `duration_quartile` | 时间轴四分位 |
| `new_price_quartile` | 新价结构轴四分位 |
| `lifecycle_quartile` | 总生命四分位（辅助） |

四分位必须晚于原始排位产生，不得覆盖原始排位读数。

## 6. 正式输入

所有输入均来自 `market_base.duckdb`，取后复权价（`adjust_method='backward'`）：

| 表 | 用途 |
|----|------|
| `stock_monthly_adjusted` | 月线 → 长期牛熊判断 |
| `stock_weekly_adjusted` | 周线 → 顺势逆势判断 |
| `stock_daily_adjusted` | 日线 → 新价结构度量 |
| `index_monthly` / `index_weekly` | 宽基指数市场背景 |
| `trade_calendar` | 交易日历 |

## 7. 正式输出

`execution_context_snapshot`（DuckDB 桥表）：承载四格上下文 + 生命周期三轴排位，供下游消费。

| 字段类 | 字段 |
|--------|------|
| 定位 | `entity_scope` / `entity_code` / `calc_date` / `active_wave_id` |
| 上下文 | `long_background_2` / `intermediate_role_2` / `malf_context_4` |
| 排位 | `amplitude_rank_*` / `duration_rank_*` / `new_price_rank_*` / `lifecycle_rank_*`（各 `low / high / total`） |
| 四分位 | `amplitude_quartile` / `duration_quartile` / `new_price_quartile` / `lifecycle_quartile` |

## 8. 模块边界

MALF 的全部职责是一条流水线：

1. 月线价格结构 → `long_background_2`（BULL / BEAR）
2. 周线相对月线 → `intermediate_role_2`（MAINSTREAM / COUNTERTREND）
3. 组合 → `malf_context_4`
4. 日线新价结构度量（新高/新低次数、间隔）
5. 在同一四格内对历史已完成中级波段排位
6. 输出 `execution_context_snapshot`
7. 宽基指数市场背景池计算

**不负责**：数据采集与复权（`data`）、结构位识别（`structure`）、不利条件过滤（`filter`）、PAS 触发器探测（`alpha/pas`）、仓位管理与交易执行（`position / trade`）。

## 9. 铁律

1. 执行层主读数是 `malf_context_4` + 三轴原始排位 + 四分位。
2. 三轴排位必须保留原始历史名次区间，不先归一化。
3. 四分位只是压缩辅助，不得覆盖三轴原始排位读数。
4. 只有同一标的、同一四格的历史已完成中级波段才是可比样本。
5. MALF 以 `market_base` 为唯一数据来源。

## 10. 成功标准

1. 四格上下文能正确分类每个标的的当前中级波段。
2. 三轴原始排位能输出正确的历史名次区间。
3. 新价结构度量能正确识别新高/新低次数与间隔。
4. `lifecycle_rank_*` 由三轴正确相加。
5. 批量构建能覆盖全市场。
6. 下游 `filter` / `alpha/pas` / `position` 能消费 `execution_context_snapshot`。

## 11. 设计文档索引

| 文档 | 内容 |
|------|------|
| `00-malf-charter` | 模块章程（本文） |
| `01-malf-full-cycle-layering` | 月线 / 周线 / 日线三层职责边界 |
| `04-malf-weekly-flow-relation` | 周线顺逆判定规则 |
| `06-malf-daily-rhythm-new-high-counting` | 日线新价结构度量设计 |
| `07-malf-four-context-and-lifecycle-ranking-charter` | 四格上下文 + 生命周期排位详细规格 |
