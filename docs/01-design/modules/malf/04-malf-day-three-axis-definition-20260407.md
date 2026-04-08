# MALF 生命周期三轴度量定义 / 2026-04-07（重构版）

> 本文定义章程 §3 第二步——生命周期排位所使用的三把尺子的计算规格。
> 新价结构轴思想来源：立花义正《你也能成为股票操作高手》（あなたも株のプロになれる），扩展为同时覆盖新高与新低。

## 1. 定位

三轴度量是章程 §3 的**第二步（生命周期排位）**，在月线 + 周线完成四格上下文分类之后进行。

三把尺子回答同一个问题：**当前中级波段的生命走到哪里了？**

| 轴 | 度量对象 | 回答 |
|----|----------|------|
| 波动幅度（`amplitude`） | 当前中级波段已走出的价格振幅 | 走了多远 |
| 时间跨度（`duration`） | 当前中级波段已持续的交易时间 | 走了多久 |
| 新价结构（`new_price`） | 创新高/新低的次数与间隔 | 推进节奏如何 |

每轴产出原始历史排位区间 → 三轴相加得到总生命区间 → 四分位压缩辅助执行（详见 `05`）。

## 2. 波动幅度轴（amplitude）

### 2.1 定义

当前中级波段从起点到当前日的**价格振幅**。

```text
amplitude = abs(当前收盘价 - 波段起点价) / 波段起点价
```

### 2.2 字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `amplitude_value` | `float` | 当前波段振幅（百分比） |

### 2.3 排位输出

| 字段 | 含义 |
|------|------|
| `amplitude_rank_low` / `amplitude_rank_high` | 在历史同类波段中的排位区间 |
| `amplitude_rank_total` | 该四格下可比历史样本总数 |

## 3. 时间跨度轴（duration）

### 3.1 定义

当前中级波段从起点到当前日已持续的**交易日数量**。

```text
duration = 当前日期 - 波段起点日期（交易日计）
```

### 3.2 字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `duration_value` | `int` | 当前波段已持续交易日数 |

### 3.3 排位输出

| 字段 | 含义 |
|------|------|
| `duration_rank_low` / `duration_rank_high` | 在历史同类波段中的排位区间 |
| `duration_rank_total` | 该四格下可比历史样本总数 |

## 4. 新价结构轴（new_price）

### 4.1 定义

当前中级波段推进过程中，创新价事件的节奏。包含两个维度（章程 §5）：

- **次数**：当前波段第几次创新价（牛市计新高，熊市计新低）
- **间隔**：相邻两次创新价之间的交易日数；间隔放大 = 趋势活力衰竭的早期信号

> **一段行情最值钱的部分，集中在创新价的日子。**

方向由四格上下文决定：

| 四格 | 计新价方向 |
|------|-----------|
| `BULL_MAINSTREAM` | 新高 |
| `BULL_COUNTERTREND` | 新低 |
| `BEAR_MAINSTREAM` | 新低 |
| `BEAR_COUNTERTREND` | 新高 |

### 4.2 字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `is_new_price_today` | `bool` | 当日是否为新价日 |
| `new_price_seq` | `int` | 当前波段内第几个新价日；0 = 非新价日 |
| `days_since_last_new_price` | `int \| None` | 距上一个新价日的交易日间距；`None` = 无前序新价日 |
| `new_price_count` | `int` | 当前波段内新价日总数量 |

### 4.3 新价日判定

**牛市顺势 / 熊市逆势（计新高）**：

```text
当日收盘价 > max(过去 lookback_days 个交易日的收盘价)
```

**熊市顺势 / 牛市逆势（计新低）**：

```text
当日收盘价 < min(过去 lookback_days 个交易日的收盘价)
```

- 默认 `lookback_days = 20`（约一个交易月）
- 只看收盘价，不看当日最高/最低价
- 第一根 K 线永远不是新价日

### 4.4 新价间距参考

| 阶段 | 典型间距 | 解读 |
|------|----------|------|
| 趋势健康期 | 1~5 交易日 | 新价频繁，趋势活力强 |
| 趋势减速期 | 6~15 交易日 | 新价变难，开始消耗 |
| 趋势衰竭期 | >20 交易日 | 新价极难，趋势末端 |

### 4.5 排位输出

| 字段 | 含义 |
|------|------|
| `new_price_rank_low` / `new_price_rank_high` | 在历史同类波段中的排位区间 |
| `new_price_rank_total` | 该四格下可比历史样本总数 |

## 5. 总生命区间

三轴排位简单相加（详见 `05` §8）：

| 字段 | 公式 |
|------|------|
| `lifecycle_rank_low` | `amplitude_rank_low + duration_rank_low + new_price_rank_low` |
| `lifecycle_rank_high` | `amplitude_rank_high + duration_rank_high + new_price_rank_high` |
| `lifecycle_rank_total` | `amplitude_rank_total + duration_rank_total + new_price_rank_total` |

## 6. 实现入口

- `src/lq/malf/daily.py` → `compute_new_price_structure()` — 新价结构轴计算
- `src/lq/malf/pipeline.py` → 波动幅度与时间跨度在 pipeline 中根据波段起止计算
- 排位逻辑见 `05` 章程与后续 runner 实现

## 7. 历史化说明

- 旧的 `daily rhythm` / `new high counting` 命名可以继续保留为来源追溯，但不再代表本文正式边界。
- 当前正式边界是“生命周期三轴度量”，其中日线只承担 `new_price` 这一轴，不再被解释为独立第三层。
- 当前代码若仍出现 `is_new_high_today` / `new_high_seq` / `days_since_last_new_high` 等命名，视为兼容残留；正式合同应收敛到 `new_price_*`。
- `amplitude` / `duration` / `new_price` 的正式主读数必须保留原始历史排位区间，不得先归一化再冒充主字段。
