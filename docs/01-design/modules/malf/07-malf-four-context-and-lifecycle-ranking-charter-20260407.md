# MALF 四格上下文与生命周期三轴排名章程 / 2026-04-07

## 0. 历史重定向说明

自 `016-malf-four-context-lifecycle-contract-reset-conclusion-20260407.md` 起，`MALF` 的对外正式执行主轴不再是：

`monthly_state_8 x weekly_flow_relation_to_monthly x pas_trigger`

也不再允许把 `scene quartile / scene_id / 16-cell` 误表述为"趋势生命周期主读数"。

本章程重新冻结的正确方向是：

`四格上下文分类 + 同标的历史中级波段三轴原始排位 + 四分位辅助表达`

保留旧文档与旧实现的原因只有两个：

1. 兼容既有正式 run、报表与审计链。
2. 保留主线曾经跑偏到哪里的追溯证据。

放弃旧主轴的原因也必须写明：

1. 它把 `MALF` 从"平均寿命经验统计系统"跑偏成了"月线八态上下文系统"。
2. 它没有直接复刻书图所表达的"当前趋势在历史分布中的位置"。
3. 它把 `scene quartile` 与 `lifecycle quartile` 混在一起，导致下游误把场景分位当成寿命分位。

> 父系统对应文档：`G:\MarketLifespan-Quant\docs\01-design\modules\malf\28-malf-four-context-and-lifecycle-ranking-charter-20260407.md`

## 1. 目标

本章程只冻结一件事：

把 `MALF` 重新收口为"复刻书中两张生命周期分布图"的正式系统设计。

这里说的"复刻"不是手工画图，而是让计算机对每个股票、每个指数，持续完成同一套经验统计工作：

1. 先把当前中级波段放进可比的四格上下文。
2. 再把它与该标的历史上同类已完成中级波段逐一比较。
3. 最后输出"当前趋势生命走到哪里了"的原始排位读数与四分位辅助标签。

## 2. 权威来源

本轮书义锚点固定为两张图：

1. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_160_img-54.jpeg.png`
2. `F:\《股市浮沉二十载》\2011.专业投机原理\专业投机原理_ocr_results\page_345_img-57.jpeg.png`

系统吸收口径固定为：

1. 用历史已经发生过的中级趋势事实，去估计当前趋势位于其生命周期分布的什么位置。
2. 四分位只是压缩表达，不是主读数。
3. 主读数必须尽量保留"原味历史排位"，不先做归一化。
4. 先尊重每个标的自己的历史，再谈 pooled 背景。

## 3. 什么是趋势的生命

`趋势的生命` 指的不是一句抽象比喻，而是：

当前这段中级波段，相对于该标的历史上同类中级波段，已经走到了多深、多久、多密。

这里的"三个多"在本轮固定为：

1. `波动幅度`：这段中级波段已经走出的价格振幅。
2. `时间跨度`：这段中级波段已经持续的交易时间。
3. `新高频率`：这段中级波段推进过程中，创新高事件出现得多不多。

补充边界：

1. 本轮沿书图固定使用 `新高频率` 这个名称，不在本章擅自扩展成别的术语。
2. 若后续在熊市主跌段需要把"创新低频率"显式收成对称字段，必须另开卡，不在本章偷改语义。

## 4. 为什么先定义趋势、再定义顺逆

先定义趋势，不是为了装饰性标签，而是为了得到可重复、可审计、可比较的中级波段对象。

先定义顺逆，也不是为了把市场说复杂，而是为了避免把本质不同的中级波段拿来混排。

因此本轮固定：

1. `INTERMEDIATE` wave 仍是正式寿命统计对象。
2. `LONG` 只负责给 `INTERMEDIATE` 提供背景。
3. `SHORT` 只继续服务转折确认与预警，不承担寿命统计主读数。
4. 每条中级波段都必须先进入四格之一，再允许进入生命周期排名。

## 5. 四格上下文

`MALF` 的正式可比上下文固定为四格：

1. `BULL_MAINSTREAM`
2. `BULL_COUNTERTREND`
3. `BEAR_MAINSTREAM`
4. `BEAR_COUNTERTREND`

解释规则固定为：

1. `BULL / BEAR` 回答长期背景是谁。
2. `MAINSTREAM / COUNTERTREND` 回答当前中级波段相对长期背景是顺势还是逆势。
3. 只有进入同一格的历史中级波段，才允许拿来比较生命周期。

本轮正式放弃把 `monthly_state_8` 当成 `MALF` 生命周期主轴，原因是：

1. 八态会先把样本切碎。
2. 八态回答的是背景细分，不是生命位置。
3. 当前中线寿命统计的核心，不需要先把月线切成八类才成立。

## 6. 生命周期三轴排名

对每个 `entity_code`、每个 `malf_context_4`，都必须维护一组历史已完成中级波段样本池。

正式样本池规则固定为：

1. 只收录该标的自身历史上已完成的 `INTERMEDIATE` wave。
2. 只与同一 `malf_context_4` 的历史波段比较。
3. 当前活跃波段可以被评分，但不得反向进入自己的历史样本池。

正式三轴主读数固定为原始排位区间：

1. `amplitude_rank_low / amplitude_rank_high / amplitude_rank_total`
2. `duration_rank_low / duration_rank_high / duration_rank_total`
3. `new_high_frequency_rank_low / new_high_frequency_rank_high / new_high_frequency_rank_total`

各轴经验含义固定为：

1. 若当前波段幅度落在 `28/281 -- 29/281`，就按这个原始历史排位原样保存，不先压成 `0.10` 或 `10%`。
2. 若当前波段时间落在 `30/281 -- 31/281`，也按这个原始历史排位保存。
3. 若当前波段新高频率落在 `40/281 -- 41/281`，同样按这个原始历史排位保存。

补充规则固定为：

1. 这里的 `low / high` 表示当前活跃波段夹在历史样本的哪两个相邻名次之间。
2. `total` 表示该标的、该四格上下文下可比较历史样本总数。
3. 若当前值正好与某一历史名次重合，允许 `low = high`。

## 7. 四分位压缩表达

本轮允许四分位存在，但必须服从下面的先后顺序：

1. 先有原始历史排位区间。
2. 再把三轴的小值、大值分别简单相加，得到总生命区间。
3. 最后才允许出现 `Q1 / Q2 / Q3 / Q4` 的压缩表达。

总生命区间固定为：

1. `lifecycle_rank_low = amplitude_rank_low + duration_rank_low + new_high_frequency_rank_low`
2. `lifecycle_rank_high = amplitude_rank_high + duration_rank_high + new_high_frequency_rank_high`
3. `lifecycle_rank_total = amplitude_rank_total + duration_rank_total + new_high_frequency_rank_total`

正式解释固定为：

1. 三条轴各自先保留"原味历史排位"。
2. 再把三条轴的小值相加，得到当前中级生命区间的下界。
3. 再把三条轴的大值相加，得到当前中级生命区间的上界。
4. 当前波段就落在这个月周背景下的中级生命框架里。

本轮正式保留两层四分位：

1. 轴级四分位：
   - `amplitude_quartile`
   - `duration_quartile`
   - `new_high_frequency_quartile`
2. 执行级总四分位：
   - `lifecycle_quartile`

这里的 `lifecycle_quartile` 是辅助字段，不得覆盖三轴原始排位读数，也不得覆盖 `lifecycle_rank_low / high`。

推导规则冻结为：

1. `lifecycle_quartile` 必须晚于 `lifecycle_rank_low / high` 产生。
2. 第一版允许仅根据 `lifecycle_rank_low / high` 所落的大致区间，给出辅助四分位。
3. 若后续需要更复杂的联合规则，必须另开卡并保留前后对照证据。

## 8. 正式表与桥接层

本章要求后续实现至少形成一张新的执行桥表：

1. `malf.execution_context_snapshot`

它的职责不是替代底层 `lifespan_* / scene_*`，而是把"执行真正需要的上下文与寿命读数"明确物化出来。

字段分层固定为：

1. 主字段：
   - `entity_scope`
   - `entity_code`
   - `calc_date`
   - `long_background_2`
   - `intermediate_role_2`
   - `malf_context_4`
   - `active_wave_id`
   - `amplitude_rank_low`
   - `amplitude_rank_high`
   - `amplitude_rank_total`
   - `duration_rank_low`
   - `duration_rank_high`
   - `duration_rank_total`
   - `new_high_frequency_rank_low`
   - `new_high_frequency_rank_high`
   - `new_high_frequency_rank_total`
   - `lifecycle_rank_low`
   - `lifecycle_rank_high`
   - `lifecycle_rank_total`
   - `amplitude_quartile`
   - `duration_quartile`
   - `new_high_frequency_quartile`
   - `lifecycle_quartile`
2. 观察字段：
   - `monthly_state_8`
   - `weekly_flow_relation_to_monthly`
   - `surface_label`
   - `scene_id`
   - `scene_quartile`

正式约束固定为：

1. 观察字段必须保留，但不得再冒充生命周期主轴。
2. `scene_quartile` 必须与 `lifecycle_quartile` 拆名，禁止再次共用裸字段名 `quartile`。

## 9. 与 PAS / position 的接口边界

`PAS` 后续正式消费的，不应再是"某个 scene 的 quartile"，而应是：

1. `malf_context_4`
2. `amplitude_rank_low / amplitude_rank_high / amplitude_rank_total`
3. `duration_rank_low / duration_rank_high / duration_rank_total`
4. `new_high_frequency_rank_low / new_high_frequency_rank_high / new_high_frequency_rank_total`
5. `lifecycle_rank_low / lifecycle_rank_high / lifecycle_rank_total`
6. `amplitude_quartile / duration_quartile / new_high_frequency_quartile`
7. `lifecycle_quartile`

`position` 后续正式消费的，也不应再只是固定基线仓位，而应至少能读到同一组生命周期字段。

本章明确不在这里冻结具体仓位公式，只冻结接口方向：

1. 先让 `MALF` 给出正确的生命周期读数。
2. 再让 `PAS / position` 基于这些读数做统计准入与资金使用。
3. 禁止反过来为了迁就当前固定仓位，而篡改 `MALF` 生命周期定义。

## 10. 显式放弃的跑偏口径

从本章起，下面这些口径不再代表 `MALF` 的正确设计：

1. 把 `monthly_state_8 x weekly_flow_relation_to_monthly` 当作 `MALF` 执行主轴。
2. 把 `scene_id = surface_label + quartile` 当作"趋势生命位置"的正式表达。
3. 把 `scene quartile` 混同为 `lifecycle quartile`。
4. 把 `16-cell` 验证结论当作 `MALF` 生命周期主线本体。

它们可以保留，但必须只以三种身份继续存在：

1. 历史 run 兼容
2. 研究附录
3. 审计追溯

## 11. 与父系统的对应关系

| 本系统 | 父系统 |
|---|---|
| `07-malf-four-context-and-lifecycle-ranking-charter-20260407.md` | `28-malf-four-context-and-lifecycle-ranking-charter-20260407.md` |
| `02-malf-four-context-lifecycle-execution-contract-spec-20260407.md` | `28-malf-four-context-lifecycle-execution-contract-spec-20260407.md` |
| 被覆盖的旧 design `02/03/05` | 被覆盖的旧 design `13/14/15/16` |
| 被覆盖的旧 spec `01` | 被覆盖的旧 spec `14/15/16/17` |
| 包名 `lq.malf` | 包名 `mlq.malf` |

## 12. 成功标准

当下面几件事同时成立时，视为本章完成：

1. 仓库内正式设计/规格已经把四格上下文与生命周期三轴原始排位写死。
2. 跑偏的设计文档与实现代码已被显式标记为历史兼容，并写明放弃原因。
3. 后续 runner、PAS 接口、position 接口都以 `execution_context_snapshot` 为新方向。
4. 任何人再问"`MALF` 的生命体现在哪里"，答案都首先回到历史中级波段三轴原始排位，而不是月线八态。
