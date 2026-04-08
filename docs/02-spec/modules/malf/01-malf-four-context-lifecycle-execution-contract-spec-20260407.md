# MALF 四格上下文与生命周期执行合同规格 / 2026-04-07（重构版）

> 父系统对应文档：`G:\MarketLifespan-Quant\docs\02-spec\modules\malf\28-malf-four-context-lifecycle-execution-contract-spec-20260407.md`

## 1. 目标

本规格把 `MALF` 正式执行合同固定为：

`四格上下文 + 生命周期三轴原始排位 + 四分位辅助表达`

## 2. 正式主字段

### 2.1 背景与角色

| 字段 | 取值 | 映射 |
|------|------|------|
| `long_background_2` | `BULL / BEAR` | 月线价格结构 |
| `intermediate_role_2` | `MAINSTREAM / COUNTERTREND` | 周线相对月线 |
| `malf_context_4` | 四格 | `long_background_2 + "_" + intermediate_role_2` |

### 2.2 生命周期三轴原始排位

| 轴 | 字段 |
|----|------|
| 波动幅度 | `amplitude_rank_low` / `amplitude_rank_high` / `amplitude_rank_total` |
| 时间跨度 | `duration_rank_low` / `duration_rank_high` / `duration_rank_total` |
| 新价结构 | `new_price_rank_low` / `new_price_rank_high` / `new_price_rank_total` |

字段类型与边界：

1. 类型固定为 `INTEGER`
2. `low / high` 取值必须满足 `1 <= low <= high <= total`
3. `total` 必须大于等于 `1`
4. 空值只允许出现在历史样本不足或当前波段无法评分的显式边界场景

字段含义：

1. `low / high` 表示当前活跃波段夹在历史样本的哪两个相邻名次之间
2. `total` 表示该标的、该四格上下文下的历史样本总数
3. 系统必须优先保留 `28/281 -- 29/281` 这种原始表达，不先归一化

### 2.3 生命周期四分位

| 字段 | 取值 |
|------|------|
| `amplitude_quartile` | `Q1 / Q2 / Q3 / Q4` |
| `duration_quartile` | `Q1 / Q2 / Q3 / Q4` |
| `new_price_quartile` | `Q1 / Q2 / Q3 / Q4` |
| `lifecycle_quartile` | `Q1 / Q2 / Q3 / Q4` |

### 2.4 生命周期总区间

| 字段 | 公式 |
|------|------|
| `lifecycle_rank_low` | `amplitude_rank_low + duration_rank_low + new_price_rank_low` |
| `lifecycle_rank_high` | `amplitude_rank_high + duration_rank_high + new_price_rank_high` |
| `lifecycle_rank_total` | `amplitude_rank_total + duration_rank_total + new_price_rank_total` |

类型 `INTEGER`，必须满足 `1 <= lifecycle_rank_low <= lifecycle_rank_high <= lifecycle_rank_total`。

### 2.5 当前 active wave 身份

| 字段 | 含义 |
|------|------|
| `active_wave_id` | 正在被评分的当前中级波段 |
| `historical_sample_count` | 同标的同格历史已完成波段数量 |
| `ranking_asof_date` | 本次生命周期读数的观察日期 |

按 `020` bootstrap 结论，当前第一版 `execution_context_snapshot` 允许：

1. `active_wave_id` 暂时为空
2. `historical_sample_count` 暂时为空
3. `ranking_asof_date` 先等于本次 `calc_date`

### 2.6 兼容残留字段（非正式）

下列字段或命名允许因历史 run、旧报表、旧接口而继续存在，但**不属于**当前正式执行合同最小集：

| 残留字段 / 命名 | 当前地位 | 说明 |
|-----------------|----------|------|
| `monthly_state` / `monthly_state_8` | 诊断 / 兼容 | 月线八态可保留，但执行层正式主字段是 `long_background_2` |
| `weekly_flow` / `weekly_flow_relation_to_monthly` | 诊断 / 兼容 | 正式主字段是 `intermediate_role_2` |
| `is_new_high_today` / `new_high_seq` / `days_since_last_new_high` / `new_high_count_in_window` | 历史命名 / 待迁移 | 若继续存在，只能视为 `new_price_*` 的旧命名，不得替代正式字段 |
| `scene_quartile` / 裸 `quartile` / `16-cell` | 历史报表 / 兼容观察字段 | 不代表生命周期三轴原始排位或总生命区间 |

## 3. execution_context_snapshot 桥表

`malf.execution_context_snapshot` 最小列要求：

1. `run_id`
2. `entity_scope`
3. `entity_code`
4. `calc_date`
5. `long_background_2`
6. `intermediate_role_2`
7. `malf_context_4`
8. `active_wave_id`
9. `historical_sample_count`
10. `amplitude_rank_low` / `amplitude_rank_high` / `amplitude_rank_total`
11. `duration_rank_low` / `duration_rank_high` / `duration_rank_total`
12. `new_price_rank_low` / `new_price_rank_high` / `new_price_rank_total`
13. `lifecycle_rank_low` / `lifecycle_rank_high` / `lifecycle_rank_total`
14. `amplitude_quartile` / `duration_quartile` / `new_price_quartile` / `lifecycle_quartile`
15. `ranking_asof_date`
16. `contract_version`

上述列是正式最小列。兼容残留列若暂时保留，必须显式标注其非正式身份，且不得替代任一正式列。

当前 bootstrap 边界：

1. 第一版 bridge table 允许 `active_wave_id`、`historical_sample_count` 为 `NULL`
2. 当前最小落表合同**不包含** `ranking_status` / `ranking_status_reason`
3. 若后续需要把 ranking 状态正式落表，必须另开卡并同步升级 design / spec / schema

## 4. 历史样本池合同

样本池规则：

1. 按 `entity_code + malf_context_4` 切分
2. 只收录历史已完成 `INTERMEDIATE` wave
3. 当前 active wave 不得进入自己的基准样本池
4. 历史样本不足时，必须显式落边界状态，不允许静默伪造四分位

目标态扩展状态（当前 bootstrap 未落表）：

| 字段 | 含义 |
|------|------|
| `ranking_status` | `READY / INSUFFICIENT_HISTORY / ACTIVE_WAVE_NOT_SCORABLE` |
| `ranking_status_reason` | 可复述原因 |

上述状态字段当前只作为后续 ranking 算法落地后的扩展方向说明，不属于 `020` 第一版 bridge table 的正式最小列。

## 5. 计算合同

### 5.1 三轴原始排位

三轴主读数必须来自该标的、该四格上下文历史样本的经验排序，原样保留为名次区间。

禁止：

1. 用全市场 pooled 排名替代个体历史排名
2. 先归一化再当主存储字段
3. 用硬编码阈值直接生成四分位而不保留原始名次区间

### 5.2 生命周期总区间

三轴小值相加、大值相加。

禁止：

1. 用加权平均替代简单相加
2. 在没有三轴原始排位的情况下直接伪造 `lifecycle_rank_low / high`
3. 用归一化值替代原始值作为主存储字段

### 5.3 四分位压缩

轴级四分位：

1. `Q1 = [0%, 25%)`
2. `Q2 = [25%, 50%)`
3. `Q3 = [50%, 75%)`
4. `Q4 = [75%, 100%]`

`lifecycle_quartile` 必须晚于 `lifecycle_rank_low / high / total` 产生。第一版允许直接根据 `lifecycle_rank_*` 所处区段给出辅助四分位。

## 6. Runner 合同

`execution_context_snapshot build` 阶段：

输入：月线背景 + 周线中级角色 + 当前 active wave 边界（起点价 / 起点日期） + 日线新价结构输入 + 历史波段样本池。

输出：`execution_context_snapshot` 桥表。

## 7. PAS 接口合同

`PAS` 正式最小输入：

1. `malf_context_4`
2. `amplitude_rank_*` / `duration_rank_*` / `new_price_rank_*`（各 `low / high / total`）
3. `lifecycle_rank_low` / `lifecycle_rank_high` / `lifecycle_rank_total`
4. `amplitude_quartile` / `duration_quartile` / `new_price_quartile` / `lifecycle_quartile`

`PAS` 不得把 `monthly_state_8`、`weekly_flow_relation_to_monthly`、`scene_quartile` 等兼容字段重新抬升为正式准入主轴。

## 8. Position 接口合同

`position` 正式最小输入：

1. `malf_context_4`
2. 三轴原始排位区间 + `lifecycle_rank_*`
3. 三轴四分位 + `lifecycle_quartile`

`position` 若暂时继续透传旧字段，只能作为兼容观察信息，不得覆盖生命周期正式读数。

本规格不冻结具体仓位公式，只冻结输入合同。先把生命周期读数做对，下游 sizing 可以变，上游定义不能漂。
