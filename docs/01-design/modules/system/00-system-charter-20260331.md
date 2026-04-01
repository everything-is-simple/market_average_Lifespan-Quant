# system 模块章程 / 2026-03-31（2026-04-01 增补）

## 1. 血统与来源

| 层代 | 系统 | 状态 | 主要吸收点 |
|---|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma\src\run_metadata.py + config.py` | 思想原型，无正式 system 模块 | run_id 格式规范、config_hash、RunDescriptor、start/finish_run 生命周期 |
| 父系统 | `G:\MarketLifespan-Quant\src\mlq\system\` | 正式定型，4 个 runner + 13 个治理脚本 | runner 编排模式（子模块串联）、三层上线成熟度、四档信任分级、system 无自有数据库原则 |
| 本系统 | `G:\Lifespan-Quant\src\lq\system\` | 继承演进 | 新增 `structure/filter` 层、3 个 runner（已实现 1 个）、BPB 永久禁止 |

### 1.1 从各代系统吸收的核心结论

**爷爷系统（EQ-gamma）：**
1. 没有独立 `system` 模块，编排逻辑散落在 scripts 和 `backtest/engine.py`；**教训：必须有正式 system 模块**
2. `run_id` 格式：`{scope}_{mode}_{variant}_{date_tag}_{time_tag}`，是整个 trace 体系的根锚点
3. `config_hash`（Settings 序列化 SHA-256）是参数变更追踪的基础，任何配置变化都产生不同 hash
4. `start_run / finish_run` 生命周期模式：运行开始写 `RUNNING`，结束写 `COMPLETED / FAILED`，静默失败是不可接受的

**父系统（MarketLifespan）：**
1. `system` 只做编排、调用子模块 runner、汇总摘要、生成报告，**不拥有自己的正式数据库**
2. 三级 runner 模式：
   - `run_system_mainline_closeout` — 主线 smoke 验证
   - `run_system_{pattern}_16cell_backtest` — 单触发器分格回测
   - `run_system_windowed_pas_backtest` — 时间窗多触发器回测
3. runner 内部串联模式：`PAS build → position bootstrap → sizing migration → partial exit migration → trade bridge → matrix readout`
4. 每个 runner 产出 JSON summary + markdown report 落入 `temp/` 或 `report/` 目录
5. 三层上线成熟度（见 §9）、四档信任分级（见 §9），来自 `15-system-launch-readiness-matrix-charter`
6. 关键概念原则：书本来源 ≠ 系统实现，必须按三档（已实现/部分实现/未实现）严格区分

**本系统（Lifespan-Quant）当前实现：**
1. `run_daily_signal_scan()` — 每日全市场信号扫描，已实现
2. 主链路：data → malf_context → structure_snapshot → adverse_conditions → PAS detectors → PasSignal
3. **待补**：`run_backtest_window`（时间窗回测）、`run_system_closeout`（主线验证）、run metadata 落库

### 1.2 与父系统的主要差异

| 差异点 | 父系统（MarketLifespan） | 本系统（Lifespan-Quant） |
|---|---|---|
| 链路 | data → malf → PAS → position → trade | data → malf → **structure(filter)** → alpha/pas → position → trade |
| Runner 数量 | 4 个 | 3 个（scan / backtest / closeout） |
| BPB 状态 | 已正式验证但非主线 | **永久禁止于 system 层** |
| 治理脚本 | 13 个 | 精简为 4 个核心脚本 |
| Run 元数据 | 写入 research_lab | 写入 `trade_runtime.duckdb` + JSON 文件 |

---

## 2. 模块定位

`system` 是**唯一的主线编排层**，是系统价值的最终交付入口。

**核心职责**：按序调用各业务模块的公开接口，驱动完整的信号扫描流程和批量回测，输出可审计、可追溯的运行摘要。

**`system` 只做编排，不做计算。** 所有业务逻辑必须在对应模块中实现。

---

## 3. 主线链路（冻结）

```
data → malf → structure(filter) → alpha/pas → position → trade → system
```

| 环节 | 对应模块 | 职责 |
|---|---|---|
| data | `lq.data` | 拉取、清洗、复权价构建 |
| malf | `lq.malf` | 月线状态/周线流向/日线现象三层背景 |
| structure | `lq.structure` | 结构位语言识别 |
| filter | `lq.filter` | 不利条件过滤（adverse conditions） |
| alpha/pas | `lq.alpha.pas` | PAS 触发器检测（BOF/PB/TST/CPB；BPB 禁止） |
| position | `lq.position` | 仓位规划（1R sizing + 退出合同） |
| trade | `lq.trade` | 交易执行 + 回测引擎 |
| system | `lq.system` | 编排总控 |

---

## 4. 三级 Runner（正式入口）

| Runner | 模式 | 职责 | 状态 |
|---|---|---|---|
| `run_daily_signal_scan` | SCAN | 单日全市场信号扫描，输出 `SystemScanSummary` | 已实现 |
| `run_backtest_window` | BACKTEST | 时间窗全链路回测（PAS→position→trade）| 待实现 |
| `run_system_closeout` | CLOSEOUT | 主线 smoke 验证，确认主线可重跑 | 待实现 |

---

## 5. 正式输入

1. `run_date`（扫描日）或 `[start_date, end_date]`（回测窗口）
2. `codes: list[str]`（待扫描股票池）
3. `enabled_patterns: list[str]`（允许的 PAS 触发器，默认排除 BPB）
4. `workspace: WorkspaceRoots`（数据库路径集合，来自环境变量）
5. `RunMode`（SCAN / BACKTEST / CLOSEOUT）

---

## 6. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `SystemScanSummary` | `dataclass` | JSON 文件（temp 目录）|
| `SystemBacktestSummary` | `dataclass` | JSON + markdown（report 目录） |
| `SystemCloseoutSummary` | `dataclass` | JSON + markdown（report 目录） |
| run_id 流水 | 行记录 | `trade_runtime.duckdb` 的 `_meta_runs` 表 |

**system 不拥有自己的正式数据库**，只向已有数据库写运行元数据。

---

## 7. run_id 规范

```
{scope}_{runmode}_{date_tag}_{time_tag}_{hex8}

示例：
scan_scan_d20240315_t143022_a1b2c3d4
backtest_backtest_w20230101_20231231_t090000_e5f6a7b8
closeout_closeout_d20240401_t120000_c9d0e1f2
```

| 字段 | 含义 |
|---|---|
| scope | scan / backtest / closeout |
| runmode | 与 scope 同义 |
| date_tag | `d{YYYYMMDD}` 单日 \| `w{start}_{end}` 时间窗 |
| time_tag | `t{HHMMSS}` UTC 时间 |
| hex8 | 8 位随机十六进制（防同秒冲突） |

---

## 8. 模块边界

### 8.1 负责

1. 主线链路编排（按序调用各模块公开接口）
2. 三级 runner 实现（scan / backtest / closeout）
3. run_id 生成与 `_meta_runs` 写入
4. 系统级 summary JSON + markdown report 生成
5. 运行日志与错误捕获（失败必须有可读 error_summary，不允许静默失败）
6. 治理脚本入口（scripts/system/）

### 8.2 不负责

1. 任何业务计算（属于各业务模块）
2. 数据库 schema 创建（属于各模块 bootstrap）
3. 报告可视化（属于 report 脚本）
4. MSS/IRS 计算（不在 Lifespan-Quant 主线）
5. 自有正式数据库（system 无状态库，只写 _meta_runs）

---

## 9. 上线成熟度分层（冻结框架）

来源：父系统 `15-system-launch-readiness-matrix-charter-20260329.md`

### 9.1 三层上线定义

| 层级 | 定义 | 当前状态 |
|---|---|---|
| L1 研究验证正式上线 | 主线可稳定支持 MALF→PAS→position→trade 的研究验证，可做正式 readout | **当前目标** |
| L2 执行仿真正式上线 | 在 L1 基础上，补齐 raw-execution 价格对齐与数据可信度重验 | 待开卡 |
| L3 零售可执行正式上线 | 在 L2 基础上，补齐面向普通交易者的稳定可执行合同 | 远期 |

禁止混用层级说法：**研究层跑通 ≠ 散户照做也差不多**。

### 9.2 四档信任分级

| 档位 | 含义 | 判断标准 |
|---|---|---|
| T1 核心可信 | 已有代码 + design/spec/conclusion，直接支撑当前主线 | 可直接使用 |
| T2 有边界可用 | 正式存在，但只能在明确边界内使用，不可过度外推 | 带条件使用 |
| T3 部分承接 | 系统吸收了一部分，但不是完整可对外承诺的能力 | 研究层使用 |
| T4 研究储备 | 想法 / 阅读沉淀 / 研究命题 / 未来方向 | 不使用 |

---

## 10. 铁律

1. **system 是唯一可依赖全部模块的模块**，其他模块禁止互相横向依赖
2. **主线链路顺序冻结**：filter 必须在 alpha/pas 之前，不允许跳过
3. **BPB 永久禁止**：`system` 层任何调用路径不得出现 BPB；代码注释必须标明原因
4. **system 无自有数据库**：只写各模块已有数据库的 `_meta_runs` 表和 JSON 文件
5. **run_id 必须存在**：每次 runner 运行必须生成 run_id，失败必须有 error_summary
6. **禁止静默失败**：任何业务模块调用异常必须被捕获并写入 error_summary
7. **来源 ≠ 实现**：书本概念不自动等于系统已实现能力，三档严格区分
8. **上线层级显式声明**：提到"系统上线"必须同时标明 L1/L2/L3 中的哪一层

---

## 11. 成功标准

1. `run_daily_signal_scan` 端到端运行，覆盖主线全链路（已完成）
2. `run_backtest_window` 在三年历史窗口正确推进，产出 `SystemBacktestSummary`
3. `run_system_closeout` 验证主线可重跑，产出 `SystemCloseoutSummary`
4. BPB 在任何 system 调用路径中均不出现
5. `_meta_runs` 表有每次 runner 运行的完整记录
6. 运行失败时 error_summary 有可读内容，不会静默失败

---

## 12. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-system-charter-20260331.md`（本文） | 模块章程、血统、架构、铁律 |
| `01-system-orchestration-design-20260401.md` | 三级 runner 设计、run_id 规范、run metadata、全链路伪代码 |
| `02-system-launch-readiness-and-governance-20260401.md` | 上线成熟度矩阵、信任分级当前状态、治理脚本清单 |
