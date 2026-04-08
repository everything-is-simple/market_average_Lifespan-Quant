# structure 快照合同与 pipeline 规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/structure/00-structure-charter-20260401.md`。

## 1. 范围

本规格冻结：

1. `StructureLevel / BreakoutEvent / StructureSnapshot` 合同字段约束
2. `structure.duckdb` 中 `structure_snapshot / structure_build_manifest` 的主字段与写权边界
3. `build_structure_snapshot()`、`run_structure_build()` 与脚本入口的最小执行合同

本规格不覆盖：

1. pivot high / low 算法细节
2. 水平位聚合参数调优
3. 突破分类阈值的进一步研究优化

## 2. 合同字段约束

### 2.1 `StructureLevel`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `level_type` | str | `StructureLevelType` 枚举值 |
| `price` | float | 结构位价格 |
| `formed_date` | date | 结构位形成日期 |
| `strength` | float | 必须在 `[0.0, 1.0]` |
| `touch_count` | int | 默认 `1`，表示被触达次数 |
| `is_tested` | bool | 是否已回测/测试 |
| `notes` | str | 人读说明 |

派生属性：

1. `is_support`
2. `is_resistance`

### 2.2 `BreakoutEvent`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `event_date` | date | 事件日期 |
| `level` | `StructureLevel` | 被穿越的结构位 |
| `breakout_type` | str | `BreakoutType` 枚举值 |
| `penetration_pct` | float | 穿越幅度；正值一般表示向上穿越 |
| `recovered` | bool | 是否已经收回 |
| `confirmed` | bool | 是否已确认 |
| `notes` | str | 人读说明 |

### 2.3 `StructureSnapshot`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `support_levels` | `tuple[StructureLevel, ...]` | 当前有效支撑位列表 |
| `resistance_levels` | `tuple[StructureLevel, ...]` | 当前有效阻力位列表 |
| `recent_breakout` | `BreakoutEvent | None` | 最近突破事件，可为空 |
| `nearest_support` | `StructureLevel | None` | 最近支撑位，可为空 |
| `nearest_resistance` | `StructureLevel | None` | 最近阻力位，可为空 |

派生读数：

1. `has_clear_structure`
2. `available_space_pct`

说明：

1. `structure` 只描述结构事实，不输出“可交易/不可交易”结论。
2. `StructureSnapshot` 是 `filter` 与 `alpha/pas` 的统一结构语言入口。

## 3. `structure.duckdb` 主表与写权边界

### 3.1 主表

由 `src/lq/structure/pipeline.py` 中 `STRUCTURE_SCHEMA_SQL` 建立：

| 表名 | 说明 |
| --- | --- |
| `structure_snapshot` | 每只股票每日的结构位快照主表 |
| `structure_build_manifest` | 每次构建的 manifest |

### 3.2 `structure_snapshot` 最小列要求

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `code` | VARCHAR | 股票代码 |
| `signal_date` | DATE | 信号日期 |
| `has_clear_structure` | BOOLEAN | 是否至少同时有支撑与阻力 |
| `nearest_support_price` | DOUBLE | 最近支撑位价格 |
| `nearest_resistance_price` | DOUBLE | 最近阻力位价格 |
| `available_space_pct` | DOUBLE | 最近支撑阻力空间百分比 |
| `support_count` | INTEGER | 支撑位数量 |
| `resistance_count` | INTEGER | 阻力位数量 |
| `recent_breakout_type` | VARCHAR | 最近突破事件类型 |
| `recent_breakout_date` | DATE | 最近突破日期 |
| `recent_breakout_confirmed` | BOOLEAN | 最近突破是否确认 |
| `detail_json` | VARCHAR | 完整 `StructureSnapshot` JSON |
| `run_id` | VARCHAR | 构建 run 标识 |
| `created_at` | TIMESTAMP | 写入时间 |

主键：`(code, signal_date)`

### 3.3 写权边界

允许：

1. `structure` 写 `structure.duckdb`
2. `structure` 读 `market_base.stock_daily_adjusted`
3. `filter` / `alpha` / `system` 读取 `structure_snapshot`

禁止：

1. `structure` 写 `market_base.duckdb`
2. `structure` 写 `malf.duckdb`
3. `structure` 写 `filter.duckdb`
4. `structure` 越权给出入场结论

## 4. 执行合同

### 4.1 单股单日结构快照

```python
snapshot = build_structure_snapshot(code, signal_date, daily_df)
```

输入最小列要求：

1. `date`
2. `adj_high`
3. `adj_low`
4. `adj_close`

允许附带：

1. `adj_open`
2. `adj_volume`

### 4.2 多日期批量构建

```python
result = run_structure_build(
    market_base_path=Path(...),
    structure_db_path=Path(...),
    signal_dates=[...],
    codes=None,
    batch_size=200,
    resume=False,
    reset_checkpoint=False,
    settings=None,
    verbose=True,
)
```

语义：

1. 按日期逐日处理
2. 每日内按 `batch_size` 分批处理股票
3. 每批完成立即写入 `structure_snapshot`
4. 每个日期完成后保存 checkpoint

### 4.3 脚本入口

```text
python scripts/structure/build_structure_snapshot.py --start 2015-01-01 --end 2026-04-07
python scripts/structure/build_structure_snapshot.py --date 2026-04-07
python scripts/structure/build_structure_snapshot.py --start 2015-01-01 --end 2026-04-07 --resume
```

## 5. 幂等与恢复约束

1. `structure_snapshot` 以 `(code, signal_date)` 为主键。
2. 当前 pipeline 采用“先删后插”策略实现同日同股幂等重写。
3. 支持 checkpoint 断点续传。
4. 根层设计纪律中的 `config_hash` 仍是全局方向，但本规格不假定当前 `structure_snapshot` 已完整落地该字段。

## 6. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/structure/contracts.py` | ✅ 已有 | `StructureLevel / BreakoutEvent / StructureSnapshot` |
| `src/lq/structure/detector.py` | ✅ 已有 | pivot、聚合、突破分类、快照生成 |
| `src/lq/structure/pipeline.py` | ✅ 已有 | schema、批量构建、checkpoint、落表 |
| `scripts/structure/build_structure_snapshot.py` | ✅ 已有 | CLI 入口 |

## 7. 当前确认的正式消费方式

1. `filter` 读取 `structure_snapshot` 中的 `nearest_support_price / nearest_resistance_price`
2. `alpha/pas` 使用 `StructureSnapshot` 合同或等价结构事实进行 trigger 判断
3. `system` 只能通过主线依赖读取 `structure` 输出，不得越权重写
