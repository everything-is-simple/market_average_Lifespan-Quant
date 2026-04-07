# filter 模块章程 / 2026-04-01

## 1. 来源与血统

`filter` 是 Lifespan-Quant **原创新增模块**，父系统（MarketLifespan-Quant）和爷爷系统（EmotionQuant-gamma）均无独立 filter 模块。

### 1.1 理论来源

**主要来源：YTC（Your Trading Coach）— Lance Beggs**
- "Adverse Conditions"（不利条件）概念：在进入 trigger 检测之前，先排除市场处于不利状态的情况
- 核心思想：不是找信号，而是先找"好的市场状态"；只有市场状态合适，PAS trigger 才有意义
- 五类不利条件：压缩无方向、结构混乱、空间不足、信号冲突、背景不支持

**辅助参考：**
- EQ-gamma `broker/risk.py`：`BrokerRiskState` 中的 `bear_threshold / max_positions` 有风险门槛思想，但那是仓位层面控制，不是信号层面的前置过滤
- MarketLifespan `alpha/pas` 内部：filter 逻辑分散内嵌在各 detector 中（无独立层），本系统将其提取为独立模块

### 1.2 在系统架构中的位置

```
data → malf → structure → [ filter ] → alpha/pas → position → trade → system
                                ↑
                         本系统新增核心层
                         优先级 A4（第四优先级）
                         准入门槛：先过 filter 才进 trigger
```

`filter` 是主线链路的**第四层**（在 structure 之后、alpha/pas 之前）：

- 消费 `structure` 的输出：`nearest_support_price / nearest_resistance_price`（空间检查）
- 消费 `malf` 的输出：`MalfContext`（背景检查）
- 消费日线数据：直接接收 DataFrame（振幅检查、方向检查）
- 输出 `AdverseConditionResult` → `system` 层判断 `tradeable` 决定是否进入 trigger 探测

### 1.3 设计理念：过滤器不是信号生成器

`filter` 的职责是**排除**，而不是"选择"。它回答的是：
> "当前市场状态是否有明显的不利条件？"

- `tradeable=True`：无不利条件，可以进入 trigger 探测（**不等于有信号**）
- `tradeable=False`：发现不利条件，直接跳过本股当日（**不等于一定没机会**）

这个二元输出是**保守过滤**：宁可漏掉一些机会，也不在不利条件下强行入场。

### 1.4 为何父系统没有此模块

父系统（MarketLifespan-Quant）将 adverse conditions 逻辑内嵌在 PAS detector 内部——每个 detector 自己判断"背景是否支持"。这导致：
1. 相同的过滤逻辑在 BOF、PB、TST 等多个 detector 中重复
2. 修改过滤参数时需要同步改多处
3. 无法独立测试过滤层的效果

本系统将其**提取为独立模块**，单一职责，统一维护。

---

## 2. 模块定位

`filter` 负责在进入 PAS trigger 探测前，**统一执行所有不利市场条件检查**，输出单只股票当日的准入结论（`AdverseConditionResult`）。

核心职责：5 类不利条件的独立检测（当前实现 4 类，A4-4 待补）：

| 编号 | 条件 | 检测函数 |
|---|---|---|
| A4-1 | 压缩且无方向 | `_check_compression_no_direction()` |
| A4-2 | 结构混乱 | `_check_structural_chaos()` |
| A4-3 | 空间不足 | `_check_insufficient_space()` |
| A4-4 | 多重信号冲突 | **待实现**（暂缺） |
| A4-5 | 背景不支持 | `_check_background_not_supporting()` |

**任意一个条件触发 = `tradeable=False`**（AND 逻辑：必须全部通过才算可交易）

---

## 3. 模块边界

### 3.1 负责

1. 5 类不利条件的独立检测函数
2. 主函数 `check_adverse_conditions()` 统一执行所有检查
3. 快捷函数 `is_tradeable()` 提供布尔接口
4. 结果合同 `AdverseConditionResult` 定义（active_conditions + tradeable + notes）
5. 所有过滤参数常量（统一在本模块管理，不散落到业务模块）

### 3.2 不负责

1. 信号生成（属于 alpha/pas）
2. 结构位识别（属于 structure）
3. MALF 计算（属于 malf）
4. 读写上游数据库（filter 只写自己的 `filter.duckdb`）
5. 仓位或资金管理层面的风险控制（属于 position/trade）

---

## 4. 数据流

```
输入：
  code                     — 股票代码
  signal_date              — 信号日期
  daily_bars               — DataFrame（adj_high / adj_low / adj_close / date）
  malf_ctx                 — MalfContext（可选，来自 malf 模块）
  nearest_support_price    — float | None（来自 structure 模块）
  nearest_resistance_price — float | None（来自 structure 模块）

输出：
  AdverseConditionResult (frozen dataclass)
    ├── code                 — 股票代码
    ├── signal_date          — 信号日期
    ├── active_conditions    — tuple[str]（触发的 AdverseConditionType 值列表）
    ├── tradeable            — bool（True = 全部通过，可进入 trigger）
    └── notes                — str（人读说明，分号分隔每个触发条件原因）
```

---

## 5. 模块依赖

```python
from lq.core.contracts import AdverseConditionType
from lq.malf.contracts import MalfContext
```

`filter` 的依赖链：`core` + `malf`（接收 MalfContext），不依赖 `structure`（只接收 price float，不依赖 StructureSnapshot 对象）。

**设计取舍**：filter 接收 `nearest_support_price: float | None` 而非整个 `StructureSnapshot`，理由是：
- 避免循环依赖风险（filter 不应 import structure）
- 保持接口最小化（filter 只需要价格数值）
- 允许在没有 structure 输出时仍然运行 A4-1/A4-2/A4-5 三项检查

---

## 6. 持久化 pipeline（2026-04-07 实现）

### 6.1 数据库

`filter.duckdb`（L3 层），由 `filter` 模块独占写入。

| 表 | 职责 |
|---|---|
| `filter_snapshot` | 主输出：每只股票每日的不利条件检查结果（tradeable / active_conditions / notes） |
| `filter_build_manifest` | 构建元数据（run_id / status / asof_date） |

### 6.2 构建模式

| 模式 | 入口 | 说明 |
|---|---|---|
| 全量构建 | `python scripts/filter/build_filter_snapshot.py --start 2015-01-01 --end 2026-04-07` | 首次历史回填 |
| 日增量 | `python scripts/filter/build_filter_snapshot.py --date 2026-04-07` | 每日收盘后追加 |
| 断点续传 | `python scripts/filter/build_filter_snapshot.py --start ... --end ... --resume` | 中断后从上次日期继续 |

### 6.3 pipeline 实现

- `filter/pipeline.py` — `run_filter_build()` 按日期逐日处理，每日内按 `batch_size` 分批处理股票
- 依赖 `malf.duckdb`（读 surface_label）和 `structure.duckdb`（读最近支撑/阻力价）
- 每批完成立即写入 `filter.duckdb`（先删后插，幂等）
- 每个日期完成后保存 JSON checkpoint（`core.resumable`）
- `bootstrap_filter_storage()` 初始化 schema（幂等）

---

## 7. 铁律

1. **filter 拥有 `filter.duckdb`**：不利条件结果按日按股增量追加，历史一旦计算绝不重算
2. **增量更新**：只处理新日期，每行带 `config_hash`，参数冻结则跳过已有数据
3. **每条件独立**：每个 `_check_xxx()` 函数必须独立返回 bool，不允许相互依赖
3. **任一触发即 False**：`tradeable = (active_conditions == [])` ——OR 关系触发，AND 关系通过
4. **不判断信号有效性**：filter 只说"状态不对"，不说"没有信号"；`tradeable=False` 不等于市场无机会
5. **参数常量统一管理**：所有阈值（COMPRESSION_WINDOW、MIN_SPACE_PCT 等）必须在本模块顶部声明，禁止在调用处写死数值
6. **A4-4 占位保留**：代码注释中保留 A4-4 信号冲突的位置，明确标注"待实现"

---

## 7. 成功标准

1. `check_adverse_conditions()` 对任意股票日线数据不报错，返回有效 `AdverseConditionResult`
2. `malf_ctx=None` 时，A4-5 背景检查自动跳过（不报错）
3. `nearest_support_price=None` 时，A4-3 空间检查自动跳过（不报错）
4. `daily_bars` 为空 DataFrame 时，A4-1/A4-2 自动跳过（不报错）
5. BEAR_PERSISTING 月线背景下，`tradeable=False`，`active_conditions` 包含 `BACKGROUND_NOT_SUPPORTING`
6. 振幅压缩且均线走平时，`active_conditions` 包含 `COMPRESSION_NO_DIRECTION`

---

## 8. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-filter-charter-20260401.md`（本文） | 模块章程、YTC 来源、定位、边界、铁律 |
| `01-filter-adverse-conditions-design-20260401.md` | 5类不利条件算法详解、参数选择、调优边界、A4-4 待实现说明 |
