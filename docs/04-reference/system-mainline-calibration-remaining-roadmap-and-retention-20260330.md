# 系统主线校对剩余路线图与留存边界 / 2026-03-30

## 1. 当前阶段判断

当前系统已经不是“主线是否存在”的问题，而是：

`主线已成，正在继续扩样、扩时间、扩范围，并逐步把 system-level 校对打到边界。`

当前最诚实的判断是：

- 已完成：最小闭环、四触发补齐、四层及更高层多轮扩围
- 未完成：继续扩围到边界、候选池耗尽/补入、最终主线冻结

## 2. 还剩几类卡

按当前节奏，主线校对剩余大约 `6-10` 张卡。

大类如下：

1. 更高层样本集继续扩围准入评审
2. 新一层候选历史补齐与 readiness 复核
3. 对应扩样重新准入重评
4. 重准入后的更高层时间窗扩围评审
5. 候选池耗尽或新候选补入评审
6. system mainline calibration closeout / boundary freeze

## 3. 每类卡的目的

### 3.1 样本集继续扩围评审

回答：
`在当前已准入样本集之上，下一层扩样当前是否还准入。`

### 3.2 history backfill + readiness

回答：
`若新候选被 data 历史覆盖拦下，补齐之后是否跨过 system runner 的最低门槛。`

### 3.3 扩样重新准入重评

回答：
`通过 readiness 的新候选加入之后，四触发 system-level 正式执行是否继续稳定。`

### 3.4 重准入后的时间窗扩围评审

回答：
`样本集放大后，时间窗还能否继续往前扩。`

### 3.5 候选池耗尽或新候选补入评审

回答：
`当前已校对候选池是否已经打到边界；若未耗尽，下一批可控候选在哪里。`

### 3.6 mainline closeout / boundary freeze

回答：
`系统主线校对到此完成到什么程度、哪些东西属于当前边界外。`

## 4. 什么条件下算主线校对完成

至少满足以下条件：

1. `BOF / PB / TST / CPB` 四触发的 system-level admission 已全部补齐
2. 当前候选池已推进到明确边界，边界原因已被正式写清
3. 所有 data 侧关键阻塞都已转化为正式 backfill / revalidation 结论，而不是悬空问题
4. 已形成最终的 closeout / boundary freeze 卡

## 5. temp / report 留存边界

### 5.1 `G:\MarketLifespan-temp`

只保留：

1. 当前仍消费的 `audit`
2. 当前仍消费的 `summary`
3. 当前仍消费的 `checkpoints`
4. probe / calibration 相关最小临时库

不长期保留：

1. pytest 临时产物
2. smoke 中间目录
3. 旧 backup
4. 一次性 repair 临时库

### 5.2 `G:\MarketLifespan-report`

只保留：

1. 当前版本正式输出
2. 当前波段仍需复看的正式 run 导出

不长期保留：

1. 被新一轮同类正式输出覆盖的旧重复导出
2. 仅为中间排错服务的非结论性 report 目录

### 5.3 `G:\MarketLifespan-Validated`

长期珍贵资产统一归这里，不再堆在 `temp/report`。
