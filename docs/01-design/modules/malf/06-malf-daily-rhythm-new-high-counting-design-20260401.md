# MALF 日线节奏设计：新高日计数 / 2026-04-01

> 本系统新增，父系统无对应文档。
> 思想来源：立花义正《你也能成为股票操作高手》（あなたも株のプロになれる）——新高日序列观察法。

## 1. 核心思想

立花义正的核心观察：

> **一段行情最值钱的部分，集中在新高日。**
> 行情初期，新高日密集出现，说明趋势活力充沛。
> 行情末端，新高越来越难出现，新高日间距持续放大，是趋势衰竭的早期视觉信号。

这提供了一种和 MALF 月线/周线完全不同的视线：
- 月线看背景状态（牛/熊哪个阶段）
- 周线看顺逆关系（当前这段是主流还是逆流）
- 日线看节奏活力（新高日还在出现吗？间距有没有在放大？）

**这与 PAS 触发器是两件事，不能混淆。**
触发器回答"什么形态触发"，日线节奏回答"趋势活力怎样"。

## 2. 字段定义（冻结）

| 字段 | 类型 | 含义 |
|---|---|---|
| `is_new_high_today` | `bool` | 当日是否为新高日（`close > max(past N days close)`） |
| `new_high_seq` | `int` | 当日是 `window_days` 内第几个新高日；0 表示今日非新高日 |
| `days_since_last_new_high` | `int \| None` | 距上一个新高日的交易日间距；`None` 表示历史内无前序新高日 |
| `new_high_count_in_window` | `int` | `window_days` 内新高日总数量 |

## 3. 判定规则

### 3.1 新高日定义

```
当日收盘价 > max(过去 lookback_days 个交易日的收盘价)
```

- 默认 `lookback_days = 20`（约一个交易月）
- 只看收盘价，不看当日最高价（口径更稳定）
- 第一根 K 线永远不是新高日（没有过去可比较）

### 3.2 新高序列号（new_high_seq）

在 `window_days`（默认 60 交易日）滑动窗口内，从最早到最新顺序编号：
- 若当日为新高日，`new_high_seq` = 该窗口内迄今第几个新高日
- 若当日非新高日，`new_high_seq = 0`

### 3.3 新高间距（days_since_last_new_high）

- 若当日是新高日：间距 = 距**前一个**新高日的交易日数
- 若当日非新高日：间距 = 距最近一次新高日的交易日数
- 若历史内无前序新高日：返回 `None`

间距放大是衰竭信号，例如：

| 阶段 | 典型间距 | 解读 |
|---|---|---|
| 趋势健康期 | 1~5 交易日 | 新高频繁出现，趋势活力强 |
| 趋势减速期 | 6~15 交易日 | 新高出现变难，开始消耗 |
| 趋势衰竭期 | >20 交易日 | 新高极难出现，趋势末端警示 |

## 4. 参数

| 参数 | 默认值 | 含义 |
|---|---|---|
| `lookback_days` | `20` | 新高判定的回看窗口（交易日） |
| `window_days` | `60` | 新高序列统计的滑动窗口（交易日） |

参数可在调用 `compute_daily_rhythm()` 时覆盖，不硬编码到 `MalfContext`。

## 5. 代码实现

入口函数：`src/lq/malf/daily.py` → `compute_daily_rhythm()`

函数签名：

```python
def compute_daily_rhythm(
    daily_bars: pd.DataFrame,   # 含 ['trade_date', 'close'] 列
    asof_date: date,
    lookback_days: int = 20,
    window_days: int = 60,
) -> dict:
    ...
```

返回的 `dict` 键名与 `MalfContext` 字段名一一对应。

## 6. MalfContext 集成

`MalfContext` 中四个日线节奏字段默认值均为零/False/None，
**向后兼容**：现有不传日线数据的调用不会报错。

当 pipeline 读入 L2 日线数据（`stock_daily_adjusted`）后，
由 pipeline.py 调用 `compute_daily_rhythm()` 并将结果注入 `MalfContext`。

**当前状态**：日线节奏字段已进入合同，算法已实现，pipeline 集成待 L2 日线数据就绪后另开执行卡。

## 7. 与父系统的关系

父系统未专门实现此功能（实验过多，不再扩展）。本系统是首次正式实现。
触发器（PAS 五形态）研究在父系统已完成验证；本日线节奏是独立的第三层视线，
两者通过 `MalfContext` 合同解耦：
- 日线节奏字段由 `malf.daily` 计算，进入 `MalfContext`
- PAS 触发器由 `alpha/pas` 模块消费 `MalfContext` 后独立检测

## 8. 铁律

1. `is_new_high_today / new_high_seq / days_since_last_new_high / new_high_count_in_window` 字段名冻结，不允许改名。
2. 日线节奏不替代月线背景和周线顺逆，只是第三层补充视线。
3. 日线节奏与 PAS 触发器是两件事，不能在同一层讨论或混淆。
4. `_empty_rhythm()` 永远返回合规结构，调用方无需做空值检查。
