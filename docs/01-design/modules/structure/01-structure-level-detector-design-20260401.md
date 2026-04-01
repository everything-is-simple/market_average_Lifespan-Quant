# structure 模块 — 结构位检测器设计 / 2026-04-01

## 1. 设计目标

本文定义 `structure/detector.py` 的完整算法设计，包括：

1. 波段高低点识别算法（Pivot High / Pivot Low）
2. 水平价格位聚合算法（clustering）
3. 结构位强度公式
4. 突破事件分类规则（四类）
5. 参数选择依据与调优边界
6. 主入口 `build_structure_snapshot()` 的完整流程

---

## 2. 算法参数（冻结基线）

| 参数名 | 值 | 含义 | 来源依据 |
|---|---|---|---|
| `PIVOT_LOOKBACK` | 5 | 波段高低点识别左右各看 N 根 K 线 | 日线级别结构位经验值，<5 噪音多，>10 响应太慢 |
| `LEVEL_CLUSTER_PCT` | 0.02 | 两价格位在 2% 以内视为同一区域 | A 股日线精度，过小会碎片化，过大会丢失精度 |
| `BREAKOUT_CONFIRM_PCT` | 0.01 | 有效突破需收盘超越结构位 ≥ 1% | 防止收盘仅刚过一分钱算"有效突破" |
| `FALSE_BREAKOUT_RECOVER_PCT` | 0.005 | 假突破收回门槛（0.5% 以内算收回） | 允许小量"尾巴"噪音 |
| `MIN_SPACE_PCT` | 0.05 | 最小交易空间 5%（供 filter 消费） | 1R止损+第一目标至少需要 5% 运动空间 |
| `LEVEL_MAX_AGE_DAYS` | 120 | 结构位有效期（超过后强度大幅衰减） | 约半年；A 股机构持仓换手节奏 |

---

## 3. Step 1：波段高低点识别

### 3.1 算法：左右比较法

```python
# Pivot High：i 点的最高价 ≥ 左侧所有 lookback 根，且 > 右侧所有 lookback 根
for i in range(lookback, len(highs) - lookback):
    left = highs[i - lookback : i]
    right = highs[i + 1 : i + lookback + 1]
    if highs[i] >= max(left) and highs[i] > max(right):
        pivots.append((i, highs[i], dates[i]))

# Pivot Low：对称规则（用 adj_low，min 比较）
```

**关键细节**：
- 左侧用 `>=`，右侧用 `>`：允许左侧有同高价（平台顶），但右侧必须严格低于当前点
- 使用 `adj_high / adj_low`（后复权价格），不用 `close`
- 结果按时间顺序返回，不含索引边界（前 lookback 和后 lookback 根 K 线不参与计算）

### 3.2 识别输入要求

- DataFrame 必须含列：`adj_high`、`adj_low`、`adj_close`、`date`
- 最少需要 `PIVOT_LOOKBACK * 2 + 1 = 11` 根 K 线，否则返回空列表
- `date` 列应为可转为 `pd.Timestamp` 的类型

---

## 4. Step 2：水平价格位聚合

### 4.1 算法：相邻聚类（贪心合并）

```python
# 输入：raw_prices = [(price, formed_date, level_type), ...]
# 按价格升序排列，相邻价格位在 2% 以内则合并为一组
# 合并输出：(avg_price, earliest_date, level_type, touch_count)
```

**聚合逻辑**：
1. 按价格升序排列所有原始波段点
2. 维护当前 cluster，判断新点与 cluster 基准价格的距离
3. 距离 ≤ `LEVEL_CLUSTER_PCT`（2%）：加入当前 cluster
4. 距离 > `LEVEL_CLUSTER_PCT`：输出当前 cluster（取均价 + 最早日期），开启新 cluster

**合并后属性**：
- `price` = cluster 内所有价格的均值（代表该价格区域的中轴）
- `formed_date` = cluster 内最早的形成日期
- `touch_count` = cluster 内原始点的数量（触及次数越多越强）

### 4.2 支撑 vs 阻力筛选

聚合完成后，以当日收盘价为基准线：
- **支撑位**：合并后价格 < 当日收盘价 → 在价格下方
- **阻力位**：合并后价格 > 当日收盘价 → 在价格上方

各取最近的最多 5 个（`max_levels=5`），按价格由近到远排序。

---

## 5. Step 3：结构位强度公式

```python
age_decay  = max(0.1, 1.0 - age_days / LEVEL_MAX_AGE_DAYS)
touch_bonus = min(0.3, (touch_count - 1) * 0.1)
strength   = clip(0.5 * age_decay + touch_bonus, 0.0, 1.0)
```

### 5.1 强度分量说明

| 分量 | 权重 | 含义 | 边界 |
|---|---|---|---|
| `age_decay` 分量 | ×0.5 | 结构位年龄越大强度越低 | 最新（0日）= 0.5；120日后≈0.05；最低保底 0.05 |
| `touch_bonus` 分量 | +n×0.1 | 触及次数越多强度越高 | 每多触及1次加0.1，最高+0.3 |
| 合计 | — | 综合强度 [0, 1] | 新鲜单触结构位≈0.5；老旧多触≈0.8 |

### 5.2 典型强度值

| 场景 | strength 参考 |
|---|---|
| 刚形成（0天）单触 | 0.50 |
| 30天前形成，触及2次 | 0.50×(1-30/120) + 0.1 ≈ 0.475 |
| 60天前形成，触及3次 | 0.50×0.5 + 0.2 = 0.45 |
| 120天前形成，触及4次 | 0.50×0.1 + 0.3 = 0.35 |
| 已超120天，任意触及次数 | ≤ 0.05+0.3 = 0.35（衰减主导） |

---

## 6. Step 4：突破事件分类

### 6.1 分类判断树

```
输入：最近 lookback_days（默认5日）的 K 线 + 目标结构位

penetration = 穿越幅度（支撑 → 下穿深度；阻力 → 上穿高度）/ 结构位价格

if penetration <= 0:
    → None（未触及，无事件）

elif recovered AND penetration > 0.5%:
    → FALSE_BREAKOUT（日内穿越但收回，BOF 候选）

elif penetration <= 1%:
    → TEST（轻触，TST 候选）

else:
    if 前N日已有有效突破：
        → PULLBACK_CONFIRMATION（BPB/CPB 候选）
    else：
        → VALID_BREAKOUT（有效突破）
```

### 6.2 "收回"的判断

| 结构位类型 | "收回"定义 |
|---|---|
| 支撑位 | 收盘 > 结构位价格 × (1 - 0.5%)，即收盘守住支撑（收回到支撑之上） |
| 阻力位 | 收盘 < 结构位价格 × (1 + 0.5%)，即收盘未能站上阻力（收回到阻力之下） |

### 6.3 四类突破事件与 PAS 关联

| breakout_type | 含义 | PAS 关联 | 关键判断条件 |
|---|---|---|---|
| `FALSE_BREAKOUT` | 假突破：穿越后收回 | BOF 候选 | recovered=True，穿越>0.5% |
| `TEST` | 测试：轻触未穿越 | TST 候选 | penetration ≤ 1% |
| `PULLBACK_CONFIRMATION` | 突破后回踩 | BPB/CPB 候选 | 前N日已有效突破，当日回踩 |
| `VALID_BREAKOUT` | 有效突破 | 后续 BPB/CPB 前提 | 首次穿越>1%且未收回 |

**重要**：这里只描述事件类型，**不判断是否构成交易信号**（那是 alpha/pas 的职责）。

### 6.4 当前限制

突破检测只针对**最近支撑位**（`nearest_support`），不对所有结构位逐一检测。原因：
- 计算效率（全量检测 ×10 个结构位成本翻倍）
- 最近结构位通常是当前最关键的价格博弈点

**已知缺陷**：如果最近突破事件发生在阻力位，当前版本不会捕获。未来可扩展为双侧检测。

---

## 7. 主入口：build_structure_snapshot()

### 7.1 完整流程

```
输入：code, signal_date, daily_bars

Step 1: find_horizontal_levels(daily_bars, signal_date)
    ├── find_pivot_highs(df)   → highs pivot 列表
    ├── find_pivot_lows(df)    → lows pivot 列表
    ├── _merge_nearby_levels() → 合并聚类
    └── 筛选 + 强度计算        → (supports, resistances)

Step 2: classify_breakout_event(daily_bars, supports[0], signal_date)
    → recent_breakout（仅对最近支撑位）

Step 3: 构建 StructureSnapshot(
    support_levels=tuple(supports),
    resistance_levels=tuple(resistances),
    recent_breakout=recent_breakout,
    nearest_support=supports[0] if supports else None,
    nearest_resistance=resistances[0] if resistances else None,
)
```

### 7.2 输出合同的辅助属性

`StructureSnapshot` 上有两个 system/filter 常用的辅助属性：

```python
@property
def has_clear_structure(self) -> bool:
    """有清晰结构 = 至少有一个支撑位 AND 一个阻力位。"""
    return len(self.support_levels) > 0 and len(self.resistance_levels) > 0

@property
def available_space_pct(self) -> float | None:
    """支撑到阻力的相对空间（用于 filter 的空间检查）。"""
    if nearest_support is None or nearest_resistance is None: return None
    mid = (nearest_support.price + nearest_resistance.price) / 2
    space = nearest_resistance.price - nearest_support.price
    return space / mid
```

---

## 8. 已知限制与未来方向

| 限制 | 描述 | 优先级 |
|---|---|---|
| L1 仅检测最近支撑位的突破 | 阻力位突破未检测 | 中 |
| L2 Pivot 算法对震荡市容易误识别 | 没有量能过滤，低量假波段高低点会混入 | 低 |
| L3 结构位不落库 | 每次重新计算，无历史回溯 | 低 |
| L4 `touch_count` 计数不精确 | 仅依赖 cluster 内的 pivot 数量，不是真实回踩次数 | 低 |

### 8.1 量能过滤（未来方向）

加入量能过滤的思路：
```python
# 未来增补：volume_ratio > 1.5 的 pivot 才作为强结构位
# strength += min(0.2, (volume_ratio - 1.0) * 0.1)
```

这是 T2 信任档能力，当前不引入。
