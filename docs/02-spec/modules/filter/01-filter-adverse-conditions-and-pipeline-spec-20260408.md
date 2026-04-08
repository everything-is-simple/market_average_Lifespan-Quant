# filter 不利条件合同与 pipeline 规格 / 2026-04-08

> 对应设计文档 `docs/01-design/modules/filter/00-filter-charter-20260401.md`。

## 1. 范围

本规格冻结：

1. `AdverseConditionResult` 合同字段约束
2. `filter.duckdb` 中 `filter_snapshot / filter_build_manifest` 的主字段与写权边界
3. `check_adverse_conditions()`、`run_filter_build()` 与脚本入口的最小执行合同

本规格不覆盖：

1. 每个 adverse condition 的参数调优细节
2. A4-4 多重信号冲突的未来实现方案
3. trigger 层的最终信号判断

## 2. 合同字段约束

### 2.1 `AdverseConditionResult`

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `code` | str | 股票代码 |
| `signal_date` | date | 信号日期 |
| `active_conditions` | `tuple[str, ...]` | 触发的不利条件枚举值 |
| `tradeable` | bool | `True` 表示允许进入 trigger 探测 |
| `notes` | str | 人读说明 |

说明：

1. `tradeable=True` 只表示“未发现不利条件”，不等于已经产生信号。
2. `tradeable=False` 表示任一不利条件触发。
3. `active_conditions` 当前由 `AdverseConditionType` 枚举值组成。

### 2.2 当前条件清单

| 编号 | 条件 | 代码状态 |
| --- | --- | --- |
| `A4-1` | 压缩且无方向 | 已实现 |
| `A4-2` | 结构混乱 | 已实现 |
| `A4-3` | 空间不足 | 已实现 |
| `A4-4` | 多重信号冲突 | 待实现 |
| `A4-5` | 背景不支持 | 已实现 |

## 3. `filter.duckdb` 主表与写权边界

### 3.1 主表

由 `src/lq/filter/pipeline.py` 中 `FILTER_SCHEMA_SQL` 建立：

| 表名 | 说明 |
| --- | --- |
| `filter_snapshot` | 每只股票每日的不利条件检查主表 |
| `filter_build_manifest` | 每次构建的 manifest |

### 3.2 `filter_snapshot` 最小列要求

| 列名 | 类型 | 说明 |
| --- | --- | --- |
| `code` | VARCHAR | 股票代码 |
| `signal_date` | DATE | 信号日期 |
| `tradeable` | BOOLEAN | 是否允许进入 trigger 探测 |
| `condition_count` | INTEGER | 触发条件数量 |
| `active_conditions` | VARCHAR | 触发条件列表，当前以分号拼接 |
| `notes` | VARCHAR | 人读说明 |
| `run_id` | VARCHAR | 构建 run 标识 |
| `created_at` | TIMESTAMP | 写入时间 |

主键：`(code, signal_date)`

### 3.3 写权边界

允许：

1. `filter` 写 `filter.duckdb`
2. `filter` 读 `market_base.stock_daily_adjusted`
3. `filter` 读 `malf` 提供的背景字段
4. `filter` 读 `structure_snapshot` 的最近支撑/阻力价格

禁止：

1. `filter` 写 `market_base.duckdb`
2. `filter` 写 `malf.duckdb`
3. `filter` 写 `structure.duckdb`
4. `filter` 直接写 `research_lab.duckdb`
5. `filter` 代替 `alpha/pas` 生成信号

## 4. 执行合同

### 4.1 单股单日检查

```python
result = check_adverse_conditions(
    code=code,
    signal_date=signal_date,
    daily_bars=daily_df,
    malf_ctx=malf_ctx,
    nearest_support_price=sup_price,
    nearest_resistance_price=res_price,
)
```

输入最小要求：

1. `daily_bars` 至少提供 `date / adj_high / adj_low / adj_close`
2. `malf_ctx` 可为空；为空时背景检查应自动跳过或降级
3. `nearest_support_price / nearest_resistance_price` 可为空；为空时空间检查应自动跳过或降级

### 4.2 多日期批量构建

```python
result = run_filter_build(
    market_base_path=Path(...),
    malf_db_path=Path(...),
    structure_db_path=Path(...),
    filter_db_path=Path(...),
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

1. 依赖 `malf` 与 `structure` 对应日期数据已完成构建
2. 按日期逐日处理
3. 每日内批量预加载当日 `malf` 与 `structure` 数据
4. 每批完成立即写入 `filter_snapshot`
5. 每个日期完成后保存 checkpoint

### 4.3 脚本入口

```text
python scripts/filter/build_filter_snapshot.py --start 2015-01-01 --end 2026-04-07
python scripts/filter/build_filter_snapshot.py --date 2026-04-07
python scripts/filter/build_filter_snapshot.py --start 2015-01-01 --end 2026-04-07 --resume
```

## 5. MALF 与 structure 依赖口径

当前代码实现中：

1. `filter` 批量构建从 `malf_context_snapshot` 读取：
   - `monthly_state`
   - `weekly_flow`
   - `malf_context_4`
   - `long_background_2`
   - `intermediate_role_2`
2. `filter` 从 `structure_snapshot` 读取：
   - `nearest_support_price`
   - `nearest_resistance_price`

说明：

1. 当前背景主字段应优先理解为 `long_background_2 / intermediate_role_2 / malf_context_4`。
2. `monthly_state / weekly_flow` 仍保留为兼容细粒度背景。
3. `filter` 不要求 import `StructureSnapshot` 对象本身，只消费所需价格字段。

## 6. 幂等与恢复约束

1. `filter_snapshot` 以 `(code, signal_date)` 为主键。
2. 当前 pipeline 采用“先删后插”策略实现同日同股幂等重写。
3. 支持 checkpoint 断点续传。
4. 根层设计纪律中的 `config_hash` 仍是全局方向，但本规格不假定当前 `filter_snapshot` 已完整落地该字段。

## 7. 代码落点

| 文件 | 状态 | 说明 |
| --- | --- | --- |
| `src/lq/filter/adverse.py` | ✅ 已有 | 条件检测函数与 `AdverseConditionResult` |
| `src/lq/filter/pipeline.py` | ✅ 已有 | schema、批量构建、checkpoint、落表 |
| `scripts/filter/build_filter_snapshot.py` | ✅ 已有 | CLI 入口 |

## 8. 当前确认的正式消费方式

1. `alpha/pas` 依据 `tradeable` 决定是否继续进入 trigger 探测
2. `system` 可读取 `filter_snapshot` 作为准入证据，但不得绕开 `filter` 直接伪造结果
3. `filter` 输出是准入门槛，不是交易信号本身
