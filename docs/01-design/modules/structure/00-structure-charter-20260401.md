# structure 模块章程 / 2026-04-01

## 1. 来源与血统

`structure` 是 Lifespan-Quant **原创新增模块**，父系统（MarketLifespan-Quant）和爷爷系统（EmotionQuant-gamma）均无此模块。

### 1.1 理论来源

**主要来源：YTC（Your Trading Coach）— Lance Beggs**
- 《Your Trading Edge》中的"结构位语言"（Structure Level Language）
- 核心概念：支撑/阻力位不是一条线而是一个区域；突破事件必须分类（有效突破 / 假突破 / 测试 / 回踩确认）
- 波段高低点（Swing High / Swing Low）识别是所有结构分析的起点
- 假突破（False Breakout / BOF - Bar Of Failure）：日内穿越但收盘收回，是高概率反转信号

**辅助参考：**
- 经典技术分析：支撑阻力区域、价格记忆
- 量化实现：pivot high/low 算法（左右各 N 根 K 线比较法）

### 1.2 在系统架构中的位置

```
data → malf → [ structure ] → filter → alpha/pas → position → trade → system
                    ↑
              本系统新增核心层
              优先级 A1（最高优先级）
```

`structure` 是主线链路的**第三层**（在 malf 之后、filter 之前）：
- 给 `filter` 提供：`nearest_support_price / nearest_resistance_price`（用于空间检查）
- 给 `alpha/pas` 提供：`StructureSnapshot`（突破事件分类、结构清晰度判断）
- `system` 层通过 `build_structure_snapshot()` 在每日扫描中调用

### 1.3 为何父系统没有此模块

父系统（MarketLifespan-Quant）主线为 `data → malf → PAS → position → trade`，**没有显式的结构位语言层**。PAS trigger 的判断直接在 `alpha` 模块内部内化了结构位判断逻辑，没有独立抽象。

本系统认为：**统一结构位语言后才能规范扩充 trigger 语义**。BOF/TST/BPB/CPB 等所有 PAS 触发形态本质上都是对结构位的不同反应方式，应先有公共结构位语言，再在上面定义触发形态。这是相对父系统最重要的架构升级。

---

## 2. 模块定位

`structure` 负责**从日线 K 线序列中识别关键价格位和突破事件**，输出统一的结构位快照合同（`StructureSnapshot`），供 `filter` 和 `alpha/pas` 消费。

**核心职责**：
1. 波段高低点（Pivot High / Pivot Low）识别
2. 水平支撑/阻力位聚合（附强度计算）
3. 突破事件分类（FALSE_BREAKOUT / TEST / PULLBACK_CONFIRMATION / VALID_BREAKOUT）
4. 生成 `StructureSnapshot`（统一的结构位快照合同）

**`structure` 不做**：
- 不判断是否入场（属于 `filter` 和 `alpha/pas`）
- 输出落入 `structure.duckdb`（L3，按日按股增量追加）
- 不依赖 MALF 上下文（结构位识别是价格行为本身，不需要背景层）

---

## 3. 模块边界

### 3.1 负责

1. 波段高低点识别（`find_pivot_highs / find_pivot_lows`）
2. 水平价格位聚合（2% 以内视为同一区域，合并计算强度）
3. 突破事件分类（`classify_breakout_event`）
4. 结构快照生成（`build_structure_snapshot`）
5. 结构合同定义（`StructureLevel / BreakoutEvent / StructureSnapshot`）

### 3.2 不负责

1. 判断可否入场（属于 filter）
2. PAS 触发器判断（属于 alpha）
3. 多股聚合分析

---

## 4. 数据流

```
输入：
  code         — 股票代码
  signal_date  — 信号日期
  daily_bars   — DataFrame（含 adj_high / adj_low / adj_close / date）

输出：
  StructureSnapshot (frozen dataclass)
    ├── support_levels    — 有效支撑位列表（由近到远，最多5个）
    ├── resistance_levels — 有效阻力位列表（由近到远，最多5个）
    ├── recent_breakout   — 最近的突破事件（针对最近支撑位，可为 None）
    ├── nearest_support   — 最近支撑位（可为 None）
    └── nearest_resistance — 最近阻力位（可为 None）
```

---

## 5. 模块依赖

```python
from lq.core.contracts import StructureLevelType, BreakoutType  # 只依赖 core
```

`structure` 依赖链：仅依赖 `core`，不依赖 `data / malf / alpha / position / trade`。

---

## 6. 持久化 pipeline（2026-04-07 实现）

### 6.1 数据库

`structure.duckdb`（L3 层），由 `structure` 模块独占写入。

| 表 | 职责 |
|---|---|
| `structure_snapshot` | 主输出：每只股票每日的结构位快照（支撑/阻力位、突破事件、结构清晰度） |
| `structure_build_manifest` | 构建元数据（run_id / status / asof_date） |

### 6.2 构建模式

| 模式 | 入口 | 说明 |
|---|---|---|
| 全量构建 | `python scripts/structure/build_structure_snapshot.py --start 2015-01-01 --end 2026-04-07` | 首次历史回填 |
| 日增量 | `python scripts/structure/build_structure_snapshot.py --date 2026-04-07` | 每日收盘后追加 |
| 断点续传 | `python scripts/structure/build_structure_snapshot.py --start ... --end ... --resume` | 中断后从上次日期继续 |

### 6.3 pipeline 实现

- `structure/pipeline.py` — `run_structure_build()` 按日期逐日处理，每日内按 `batch_size` 分批处理股票
- 每批完成立即写入 `structure.duckdb`（先删后插，幂等）
- 每个日期完成后保存 JSON checkpoint（`core.resumable`）
- `bootstrap_structure_storage()` 初始化 schema（幂等）
- 嵌套对象（`StructureLevel` / `BreakoutEvent`）以 JSON 序列化存储，关键标量字段（`nearest_support_price` 等）同时存为独立列

---

## 7. 铁律

1. **structure 拥有 `structure.duckdb`**：结构位快照按日按股增量追加，历史一旦计算绝不重算
2. **增量更新**：只处理新日期，每行带 `config_hash`，参数冻结则跳过已有数据
3. **无 MALF 依赖**：结构位识别只看价格行为，不依赖月线/周线背景（背景判断属于 filter）
3. **结构位合同格式冻结**：`StructureSnapshot` 的字段结构一旦发布不允许缩减（只允许向后兼容添加）
4. **强度公式固定**：`strength = 0.5 * age_decay + touch_bonus`，不允许在不同调用路径中使用不同公式
5. **禁止入场判断**：`structure` 模块禁止返回任何"可以入场"或"不可以入场"的结论，只描述结构事实

---

## 7. 成功标准

1. `build_structure_snapshot()` 对任意股票日线数据（≥11 根）不报错，返回有效 `StructureSnapshot`
2. 在 BULL_FORMING 背景下的主力股，能正确识别至少 1 个支撑位和 1 个阻力位
3. 假突破（BOF）场景：穿越结构位但收回时，`recent_breakout.breakout_type == "FALSE_BREAKOUT"`
4. 有效突破场景：收盘超越结构位 1% 以上时，`breakout_type == "VALID_BREAKOUT"`
5. 数据不足（< 11 根）时，`StructureSnapshot` 中 `support_levels` 和 `resistance_levels` 均为空元组，不报错

---

## 8. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-structure-charter-20260401.md`（本文） | 模块章程、YTC 来源、定位、边界、铁律 |
| `01-structure-level-detector-design-20260401.md` | 波段高低点算法、聚合逻辑、突破分类规则、强度公式、参数设计 |
