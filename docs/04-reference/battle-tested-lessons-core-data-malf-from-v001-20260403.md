# 实战经验总结：core → data → malf 三模块（继承自 v0.01）/ 2026-04-03

> **来源**：本文继承自父系统 MarketLifespan-Quant v0.01（从立项到第 244 张卡的实战萃取）。
> v0.1（Lifespan-Quant）在实现 `lq.core` / `lq.data` / `lq.malf` 时，必须逐条对照本文。
> 每一条都来自真实踩过的坑、花过的时间、或差点翻车的教训。
> 第五章"传承清单"是 v0.1 实现时的强制检查表。

---

## 一、core 模块：不只是路径，而是系统骨骼

### 1.1 五库路径合同是铁律

- `paths.py` 的 `WorkspaceRoots` + `DatabasePaths` 是冻结 dataclass
- 五个正式数据库路径在此一锤定音，所有模块必须经 `default_settings()` 解析
- 环境变量覆盖（`MLQ_REPO_ROOT` 等）让 pytest 和 CI 能重定向到临时目录
- **教训**：早期路径写死在脚本里，换机器就全崩；统一入口后再没出过

### 1.2 表级 ownership manifest 是机读合同

- `table_ownership_manifest.py` 不是文档——是可执行的机读合同
- 五库全部正式表的 owner_module / allowed_readers 登记在案
- 治理脚本直接消费 manifest 检测越权读写
- **教训**：trade 曾直接 import malf 内部函数取数，导致依赖反向穿透

### 1.3 run_output_families 是输出族治理清单

- 每个正式 runner 的输出表、run 表、关联键、归档族全部登记
- `DEPRECATED_RUN_OUTPUT_FAMILIES` 显式标记已弃用族（如 MSS）
- **教训**：MSS 曾被误认为主线 alpha sidecar，浪费数天排查

### 1.4 checkpoint + resumable 是断点续传基础设施

- `JsonCheckpointStore` 提供 load / save / update / clear 四动词
- `resumable.py` 提供指纹摘要、默认路径、指纹不匹配拒绝、未完成检测
- **铁律**：指纹不匹配时直接拒绝；未完成且没 resume=True 时也拒绝
- **教训**：早期无指纹校验，换参数后误复用旧 checkpoint，malf 数据错乱

### 1.5 v0.1 继承要点

- `lq.core` 必须继承 `mlq.core` 全部治理能力，不能简化
- 枚举集中化（跨模块枚举统一 `core.contracts`）是 v0.1 新增铁律
- 路径合同增加第五目录 `Validated`

---

## 二、data 模块：两级数据不只是"采集+加工"

### 2.1 用户已提到的

- 断点续传、增量更新
- mootdx 采集本地通达信 `.day` → `raw_market.duckdb`
- mootdx 复权算法 raw → 后复权 → `market_base.duckdb`
- base 需双源校验（tushare / baostock）

### 2.2 gbbq 复权算法是暗雷区

- mootdx 的 gbbq（股本变更权息）表是复权因子的唯一来源
- 复权路径需按除权除息日逐段累乘 adjustment_factor，不是简单乘除
- **教训**（卡 228）：窗口截断导致部分股票复权路径意外回退
- 根因：`window_start` 把除权基准日截掉，adjustment_factor 断链

### 2.3 raw → base 不是简单拷贝

- raw 只存原始 OHLCV；base 做后复权价、均线、量比、周线/月线聚合
- 四张 run 表（`base_build_run` / `base_incremental_entity` 等）记录每次 build 血统
- `selective_rebuild.py` 支持 stage 级选择性重建，不必每次全量
- `IncrementalWindow` 合同管控 window_start / window_end 语义

### 2.4 BJ（北交所）股票的特殊合同缺口

- **教训**（卡 230）：通达信本地有 BJ 的 `.day` 文件，但 mootdx 解析器对 `8xxxxx.BJ` / `4xxxxx.BJ` 市场代码映射不完整
- 表现："本地有文件、raw 几乎无镜像"——raw_market 里零行或几行
- 修复：显式补充 BJ 市场代码到 ingest 解析器的市场映射表

### 2.5 异常截断是真实存在的

- **教训**（卡 243）：`002357.SZ` raw 层完整但 base 层 adjusted 只有 5 行
- 根因：历史上极端股本变更（10 送 30），gbbq 复权因子在某节点产生断层
- 修复：定向 `factor_path_repair`，不动全库

### 2.6 数据新鲜度永远是下游扩样的瓶颈

- 从第 5 层到第 12 层扩样，每一层阻塞点最终都收敛回 data 历史覆盖
- 新候选股票如果 base 行数不够 `required_min_rows`，就过不了 readiness
- **铁律**：扩样前先跑 readiness 检查，不要先跑 system runner 再发现数据不够
- 当前（卡 244）仍有 8 只真实短历史候选在等 `403` 行门槛

### 2.7 双源校验的真实价值

- mootdx（主线）vs tushare/baostock（审计）：不是二选一，是互相验证
- **教训**：曾发现 mootdx 某些 ST 股的停牌日数据缺失，tushare 有但 mootdx 无
- 校验规则：backward adjusted close 的相对差异 < 0.5% 视为一致
- **铁律**：tushare / baostock 只用于审计，绝不进入主线 L2 构建

### 2.8 v0.1 继承要点

- raw → base 两级架构必须保留，禁止合并成单库
- gbbq 复权路径需加窗口完整性校验（不能截掉基准日）
- BJ 市场代码映射要在 bootstrap 时显式注册
- `factor_path_repair` 能力必须保留为独立入口
- 双源校验链路保留但可延后实现

---

## 三、malf 模块：不只是 16 种空间，而是六层纵深

### 3.1 用户已提到的

- 月线八种状态 × 周线顺逆 = 16 种空间
- 断点续传、增量更新
- 系统基石

### 3.2 六层纵深架构

用户说的"16 种空间"只是 malf 的最终产物。实际架构是六层流水线：

| 层 | 名称 | 输入 | 输出表 |
|---|---|---|---|
| L1 | 月线长期背景 | market_base 月线 | monthly_background_wave + monthly_background_snapshot |
| L2 | 周线长期背景 | market_base 周线 | weekly_background_wave + weekly_background_snapshot |
| L3 | 周线中级四表 | L1 + market_base 周线 | intermediate_wave + 四方向表 |
| L4 | 日线现象层 | L3 + market_base 日线 | extreme_event + wave_phenomenon_summary + phenomenon_snapshot |
| L5 | 16 场景面 | L4 + L1 | scene_surface + scene_snapshot |
| L6 | PAS 条件合同 | L5 + L1 | pas_trigger_registry + pas_context_snapshot |

- malf.duckdb 实际有 **22 张正式表**，不是几张
- official daily update 流水线按 L1→L2→L3→L4→L5→L6 顺序执行
- 每一层都有独立的 run_id 和 summary

### 3.3 monthly_state_8 的八种状态

```
BULL_FORMING    牛市形成中
BULL_PERSISTING 牛市持续中
BULL_EXHAUSTING 牛市衰竭中
BULL_REVERSING  牛市反转中
BEAR_FORMING    熊市形成中
BEAR_PERSISTING 熊市持续中
BEAR_EXHAUSTING 熊市衰竭中
BEAR_REVERSING  熊市反转中
```

- 兼容映射：旧的 `CONFIRMED_BULL` → `BULL_PERSISTING`，`CONFIRMED_BEAR` → `BEAR_PERSISTING`
- **教训**：枚举值一旦发布就不能改，只能通过兼容映射过渡

### 3.4 DuckDB checksum 损坏是真实威胁

- **教训**（卡 236-238）：正式 `malf.duckdb` 的 `lifespan_wave` 表发生 checksum 损坏
- 表现：读某些 block 时抛 `IOException: Stored checksum...`
- 损坏只影响一张表的部分 block，其余 21 张表完全正常
- 修复过程：导出可恢复数据（98.4%）→ DROP 损坏表 → 重建 schema → 导入 → 补算缺失 39 个实体
- **铁律**：DuckDB 无 WAL 保护的大量写入后必须做完整性校验

### 3.5 "库不坏" ≠ "全局刷新完成"

- **教训**（卡 239-241）：lifespan_wave 修复后以为一切恢复，实际全局 freshness 严重滞后
- 四张关键 STOCK 表族只有 792 / 5557 追平，4765 滞后，5 缺失
- 根因：incremental planner 只看 `source_signature_changed`，不看 downstream freshness
- 修复（卡 241）：planner 增加 `stale_freshness` 判定分支
- official 编排层增加 `_collect_official_refresh_stock_scope` 做二次兜底
- **铁律**：完整性和新鲜度是两个独立维度，修完整性后必须验新鲜度

### 3.6 incremental planner 的双层兜底设计

修复后的 planner 有两层防线：

1. **incremental 层**（`_plan_incremental_entities`）：
   - 看 source signature 变化 → `source_signature_changed`
   - 看下游 freshness 落后 → `stale_freshness`
   - 看下游表族缺失 → `stale_freshness`（materialized_table_count < expected）
2. **official 编排层**（`_collect_official_refresh_stock_scope`）：
   - 全库扫描，不限于单个 run_id
   - 兜底把 incremental 层漏掉的 stale/missing 股票补进 downstream scope

**已知残留边界**（卡 242 审查发现）：
- `freshness_state is None` 时旧实体在 incremental 层不被识别（被 official 层兜住）
- INDEX 的 `expected_table_count = 2` 缺注释
- `parameters * 4` 隐式依赖 UNION ALL 段数

### 3.7 official daily update 流水线

```
run_lifespan_official_daily_update
  ├─ 查找 latest market_base run
  ├─ run_lifespan_incremental_update（增量 wave/event/surface/snapshot）
  ├─ _collect_official_refresh_stock_scope（收集 stale/missing）
  └─ run_malf_official_stock_scope_refresh（下游六层全刷新）
       ├─ monthly_background_build（L1）
       ├─ weekly_background_build（L2）
       ├─ weekly_intermediate_build（L3）
       ├─ daily_phenomenon_build（L4）
       ├─ scene_surface_build（L5）
       └─ pas_contract_build（L6）
```

- 全市场 5562 只股票的完整六层刷新约需 8-10 小时
- shell 超时（3600s）不影响后台 python 进程继续运行
- **教训**：曾因 shell 超时误以为刷新失败，实际后台正常完成

### 3.8 5557 → 5562 的实体管理

- 全市场 STOCK 实体数随新股上市缓慢增长
- 四张关键表族必须对齐：monthly_background_snapshot / weekly_background_snapshot / scene_snapshot / pas_context_snapshot
- **铁律**：任何一张表族的 entity 缺失都意味着下游 alpha 拿不到完整条件合同

### 3.9 v0.1 继承要点

- 六层纵深架构必须保留，不能跳层
- incremental planner 必须同时看 source signature 和 downstream freshness
- DuckDB 大批量写入后必须加完整性校验步骤
- official daily update 需处理 shell 超时（用 nohup 或 detached 进程）
- 月线八态枚举已冻结，只允许兼容映射扩展
- checkpoint 指纹必须覆盖全部影响最终结果的输入参数

---

## 四、跨模块共性教训

### 4.1 断点续传不是可选功能

- core / data / malf 三个模块都已实现断点续传
- 全市场计算动辄数小时，任何中断都可能导致数据不一致
- **铁律**：新 runner 必须原生支持 checkpoint，不允许"跑完再说"

### 4.2 增量更新 ≠ 只看上游变化

- data 增量看 raw 变化 → 重建受影响的 base stage
- malf 增量看 base 变化 → 但还必须看自身下游的 freshness
- **教训**：只看上游变化会导致"增量跑完但下游没刷新"的隐蔽 bug

### 4.3 五目录纪律是生存底线

| 目录 | 用途 | 禁止 |
|---|---|---|
| 仓库根 | 代码、文档、测试 | 数据库、日志、缓存 |
| Data | 正式数据库 | 代码、临时文件 |
| temp | 临时产物、pytest | 正式代码/数据库 |
| report | 报告、图表 | 代码 |
| Validated | 跨版本验证资产 | 临时产物 |

- **教训**：早期把 malf.duckdb 放在仓库根目录，git 每次 diff 卡死

### 4.4 治理四件套是闭环保证

每个正式卡必须包含 card / evidence / record / conclusion：
- card 说意图和边界
- evidence 留可复述的命令和结果
- record 记过程和遇到的问题
- conclusion 给结论和后续入口

- **教训**：早期只有 card 没有 conclusion，半个月后回看完全不知道上次做到哪了

### 4.5 DuckDB 的优势与陷阱

**优势**：
- 单文件部署，无需服务器
- 列式存储，分析查询极快
- 支持 ATTACH 跨库查询

**陷阱**：
- 无 WAL 保护时大量写入可能导致 checksum 损坏
- 单文件损坏时定位困难（只能逐表扫描）
- VACUUM 后文件不一定缩小
- 并发写入不安全（单写多读可以）

---

## 五、从 v0.01 到 v0.1 的传承清单

| 编号 | 传承项 | 优先级 | 说明 |
|---|---|---|---|
| T1 | 五目录纪律 | 必须 | 目录名从 MarketLifespan-* 改为 Lifespan-* |
| T2 | 五库路径合同 | 必须 | `lq.core.paths` 继承 `mlq.core.paths` 全部能力 |
| T3 | 表级 ownership manifest | 必须 | 九模块版本，增加 structure/filter |
| T4 | checkpoint + resumable | 必须 | 指纹校验 + 未完成拒绝两条铁律 |
| T5 | raw → base 两级架构 | 必须 | 禁止合并，保留 selective_rebuild |
| T6 | gbbq 窗口完整性校验 | 必须 | window_start 不能截掉除权基准日 |
| T7 | BJ 市场代码映射 | 必须 | bootstrap 时显式注册 |
| T8 | malf 六层纵深 | 必须 | L1→L6 顺序不可跳层 |
| T9 | incremental + freshness 双检 | 必须 | planner 必须同时看 source 和 downstream |
| T10 | DuckDB 写后完整性校验 | 必须 | 大批量写入后全表扫描 |
| T11 | 双源校验 | 延后 | mootdx 主线 + tushare 审计 |
| T12 | 治理四件套 | 简化 | v0.1 用增量交付简化版 |

---

## 六、卡号速查：关键教训对应的历史卡

| 卡号 | 教训 |
|---|---|
| 228 | 窗口截断导致复权路径回退 |
| 230 | BJ 股票"有文件无镜像"合同缺口 |
| 236 | malf.duckdb checksum 损坏阻塞 official 刷新 |
| 237 | 595 样本范围下游刷新能力恢复 |
| 238 | lifespan_wave 完整性修复（DROP→重建→导入→补算） |
| 239 | 全局 freshness 未追平发现 |
| 240 | official catch-up 跑成功但 freshness 不变 |
| 241 | freshness trigger 修复（planner 增加 stale_freshness） |
| 242 | 241 代码审查残留三项修复 |
| 243 | 002357.SZ 异常截断定向修复 |
| 244 | 8 只真实短历史候选跨阈值跟踪 |
