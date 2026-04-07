# MALF 四格上下文与生命周期执行合同规格 / 2026-04-07

## 0. 历史重定向说明

自 `016-malf-four-context-lifecycle-contract-reset-conclusion-20260407.md` 起，本规格成为 `MALF` 对外执行合同的新基线。

被替代的旧主轴包括：

1. `monthly_state_8`
2. `weekly_flow_relation_to_monthly`
3. `scene_id`
4. `scene quartile`
5. `16-cell`

它们继续存在，但只允许作为兼容/观察字段存在。

> 父系统对应文档：`G:\MarketLifespan-Quant\docs\02-spec\modules\malf\28-malf-four-context-lifecycle-execution-contract-spec-20260407.md`

## 1. 目标

本规格把 `MALF` 正式执行合同固定为：

`四格上下文 + 生命周期三轴原始排位 + 四分位辅助表达`

## 2. 正式主字段

### 2.1 背景与角色

正式字段：

1. `long_background_2`
2. `intermediate_role_2`
3. `malf_context_4`

正式取值：

1. `long_background_2 = BULL / BEAR`
2. `intermediate_role_2 = MAINSTREAM / COUNTERTREND`
3. `malf_context_4 = BULL_MAINSTREAM / BULL_COUNTERTREND / BEAR_MAINSTREAM / BEAR_COUNTERTREND`

固定映射：

1. `malf_context_4 = long_background_2 + "_" + intermediate_role_2`

### 2.2 生命周期三轴原始排位

正式字段：

1. `amplitude_rank_low`
2. `amplitude_rank_high`
3. `amplitude_rank_total`
4. `duration_rank_low`
5. `duration_rank_high`
6. `duration_rank_total`
7. `new_high_frequency_rank_low`
8. `new_high_frequency_rank_high`
9. `new_high_frequency_rank_total`

字段类型与边界：

1. 类型固定为 `INTEGER`
2. `low / high` 取值必须满足 `1 <= low <= high <= total`
3. `total` 必须大于等于 `1`
4. 空值只允许出现在历史样本不足或当前波段无法评分的显式边界场景

字段含义固定为：

1. `low / high` 表示当前活跃波段夹在历史样本的哪两个相邻名次之间
2. `total` 表示该标的、该四格上下文下的历史样本总数
3. 系统必须优先保留 `28/281 -- 29/281` 这种原始表达，不先归一化成百分比或小数

### 2.3 生命周期四分位

正式字段：

1. `amplitude_quartile`
2. `duration_quartile`
3. `new_high_frequency_quartile`
4. `lifecycle_quartile`

正式取值：

1. 轴级四分位固定为 `Q1 / Q2 / Q3 / Q4`
2. `lifecycle_quartile` 固定为 `Q1 / Q2 / Q3 / Q4`

### 2.4 生命周期总区间

正式字段：

1. `lifecycle_rank_low`
2. `lifecycle_rank_high`
3. `lifecycle_rank_total`

推导合同固定为：

1. `lifecycle_rank_low = amplitude_rank_low + duration_rank_low + new_high_frequency_rank_low`
2. `lifecycle_rank_high = amplitude_rank_high + duration_rank_high + new_high_frequency_rank_high`
3. `lifecycle_rank_total = amplitude_rank_total + duration_rank_total + new_high_frequency_rank_total`

字段类型与边界：

1. 类型固定为 `INTEGER`
2. 必须满足 `1 <= lifecycle_rank_low <= lifecycle_rank_high <= lifecycle_rank_total`
3. 系统必须优先保留这个总区间原始值，不先压成归一化分数

### 2.5 当前 active wave 身份

正式字段：

1. `active_wave_id`
2. `historical_sample_count`
3. `ranking_asof_date`

正式含义：

1. `active_wave_id` 标识正在被评分的当前中级波段
2. `historical_sample_count` 表示该评分所用的同标的同格历史已完成波段数量
3. `ranking_asof_date` 表示这次生命周期读数的观察日期

## 3. 正式桥表合同

正式桥表固定新增为：

1. `malf.execution_context_snapshot`

最小列要求固定为：

1. `run_id`
2. `entity_scope`
3. `entity_code`
4. `calc_date`
5. `long_background_2`
6. `intermediate_role_2`
7. `malf_context_4`
8. `active_wave_id`
9. `historical_sample_count`
10. `amplitude_rank_low`
11. `amplitude_rank_high`
12. `amplitude_rank_total`
13. `duration_rank_low`
14. `duration_rank_high`
15. `duration_rank_total`
16. `new_high_frequency_rank_low`
17. `new_high_frequency_rank_high`
18. `new_high_frequency_rank_total`
19. `lifecycle_rank_low`
20. `lifecycle_rank_high`
21. `lifecycle_rank_total`
22. `amplitude_quartile`
23. `duration_quartile`
24. `new_high_frequency_quartile`
25. `lifecycle_quartile`
26. `ranking_asof_date`
27. `contract_version`

## 4. 观察字段合同

桥表允许保留下列观察字段：

1. `monthly_state_8`
2. `weekly_flow_relation_to_monthly`
3. `surface_label`
4. `scene_id`
5. `scene_quartile`

使用限制固定为：

1. 不得替代 `malf_context_4`
2. 不得替代任何 lifecycle 原始排位字段
3. 不得替代 `lifecycle_rank_low / high / total`
4. 不得替代 `lifecycle_quartile`
5. 不得在新代码中继续使用裸字段名 `quartile` 指代生命周期读数

## 5. 历史样本池合同

生命周期评分的正式样本池规则固定为：

1. 样本池按 `entity_code + malf_context_4` 切分
2. 只收录历史已完成 `INTERMEDIATE` wave
3. 当前 active wave 不得进入自己的基准样本池
4. 历史样本不足时，必须显式落边界状态，不允许静默伪造四分位

本轮最小统计输出固定为：

1. `historical_sample_count`
2. `ranking_status`
3. `ranking_status_reason`

其中：

1. `ranking_status` 可取 `READY / INSUFFICIENT_HISTORY / ACTIVE_WAVE_NOT_SCORABLE`
2. `ranking_status_reason` 必须给出可复述原因

## 6. 原始排位与四分位计算合同

### 6.1 三轴原始排位

三轴主读数必须来自该标的、该四格上下文历史样本的经验排序，并原样保留为名次区间。

正式禁止：

1. 用全市场 pooled 排名替代个体历史排名
2. 用 `scene quartile` 反代三轴原始排位
3. 先把原始名次区间归一化，再把归一化值当主存储字段
4. 用硬编码阈值直接生成四分位而不保留原始名次区间

### 6.2 生命周期总区间

生命周期总区间必须来自三轴原始排位的小值相加、大值相加。

正式禁止：

1. 用加权平均替代简单相加
2. 在没有三轴原始排位的情况下直接伪造 `lifecycle_rank_low / high`
3. 用归一化值替代 `lifecycle_rank_low / high / total` 作为主存储字段

### 6.3 四分位压缩

轴级四分位压缩规则固定为：

1. `Q1 = [0%, 25%)`
2. `Q2 = [25%, 50%)`
3. `Q3 = [50%, 75%)`
4. `Q4 = [75%, 100%]`

执行级 `lifecycle_quartile` 合同固定为：

1. 必须晚于 `lifecycle_rank_low / high / total` 产生
2. 第一版允许直接根据 `lifecycle_rank_low / high / total` 所处区段给出辅助四分位
3. 若后续引入更复杂联合规则，必须同步更新 contract version 与 evidence

## 7. Runner 合同

`MALF` 官方链路后续最小新增阶段固定为：

1. `execution_context_snapshot build`

输入来源固定为现有正式 MALF 表族：

1. `monthly background`
2. `weekly intermediate`
3. `malf_context_snapshot`（现有三层主轴输出）

输出要求固定为：

1. 先保留现有 `malf_context_snapshot` 链路
2. 再并行落出新的 `execution_context_snapshot`
3. 后续 `PAS` 迁移时优先消费 `execution_context_snapshot`

## 8. PAS 接口合同

`PAS` 后续正式最小输入字段固定为：

1. `malf_context_4`
2. `amplitude_rank_low / amplitude_rank_high / amplitude_rank_total`
3. `duration_rank_low / duration_rank_high / duration_rank_total`
4. `new_high_frequency_rank_low / new_high_frequency_rank_high / new_high_frequency_rank_total`
5. `lifecycle_rank_low / lifecycle_rank_high / lifecycle_rank_total`
6. `amplitude_quartile`
7. `duration_quartile`
8. `new_high_frequency_quartile`
9. `lifecycle_quartile`

兼容字段允许保留：

1. `monthly_state_8`
2. `weekly_flow_relation_to_monthly`
3. `scene_id`
4. `scene_quartile`

但兼容字段只允许用于：

1. 历史报表回放
2. 兼容旧 run
3. 诊断与附录

## 9. Position 接口合同

`position` 后续正式最小输入固定为：

1. `malf_context_4`
2. `lifecycle_quartile`
3. 三轴原始排位区间
4. `lifecycle_rank_low / lifecycle_rank_high / lifecycle_rank_total`
5. 三轴 quartile

本规格当前不冻结具体仓位公式，只冻结输入合同，原因是：

1. 先把生命周期读数做对，比先拍仓位曲线更重要。
2. 下游 sizing 可以变，但上游生命周期定义不能再漂。

## 10. 显式放弃的旧合同

下列合同自本规格起不再代表正确执行口径：

1. `monthly_state_8 x weekly_flow_relation_to_monthly x pas_trigger` 是 `MALF` 的正式执行主轴
2. `scene_id = surface_label + quartile` 可以代表生命周期位置
3. `quartile` 不拆名即可同时表达 `scene` 与 `lifecycle`
4. `16-cell` readout 可以代表 `MALF` 生命周期主线

放弃原因固定写法为：

1. 旧合同强调的是背景细分与场景切片，不是历史波段生命排名
2. 旧合同不能直接复刻书图那种"`28/281 -- 29/281`"式原始经验分布读数
3. 旧合同会误导 `PAS / position` 把场景分位当成寿命分位

## 11. 非目标

本规格当前明确不做：

1. 立即删除旧表、旧报表、旧 runner
2. 立即重跑所有历史 `16-cell` 结论
3. 在没有新卡与新证据的情况下，直接改写 `PAS / position` 的实际交易行为

本轮只先把合同重定向写死。
