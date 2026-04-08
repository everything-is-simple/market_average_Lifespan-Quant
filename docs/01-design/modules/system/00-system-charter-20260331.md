# system 模块章程 / 2026-03-31（2026-04-01 增补）

## 1. 血统与来源

| 层代 | 系统 | 状态 | 主要吸收点 |
|---|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma\src\run_metadata.py + config.py` | 思想原型，无正式 system 模块 | run_id 格式规范、config_hash、RunDescriptor、start/finish_run 生命周期 |
| 父系统 | `G:\MarketLifespan-Quant\src\mlq\system\` | 正式定型，4 个 runner + 13 个治理脚本 | runner 编排模式（子模块串联）、三层上线成熟度、四档信任分级、system 无自有数据库原则 |
| 本系统 | `H:\Lifespan-Quant\src\lq\system\` | 继承演进 | 新增 `structure/filter` 层、3 个 runner（已实现 1 个）、BPB 永久禁止 |

### 1.1 从各代系统吸收的核心结论

**爷爷系统（EQ-gamma）：**
1. 没有独立 `system` 模块，编排逻辑散落在 scripts 和 `backtest/engine.py`；**教训：必须有正式 system 模块**
2. `run_id` 格式：`{scope}_{mode}_{variant}_{date_tag}_{time_tag}`，是整个 trace 体系的根锚点
3. `config_hash`（Settings 序列化 SHA-256）是参数变更追踪的基础，任何配置变化都产生不同 hash
4. `start_run / finish_run` 生命周期模式：运行开始写 `RUNNING`，结束写 `COMPLETED / FAILED`，静默失败是不可接受的

**父系统（MarketLifespan）：**
1. `system` 只做编排、调用子模块 runner、汇总摘要、生成报告，**不拥有自己的正式数据库**
2. 父系统 `mlq.system` 的正式 runner 设计：
   - `run_system_daily_scan` — 单日扫描
   - `run_system_closeout` — 单股主线闭环验证
   - `run_system_{pattern}_16cell_backtest` — 单触发器分格回测
   - `run_system_windowed_pas_backtest` — 时间窗多触发器回测
3. runner 内部串联模式：`PAS build → position bootstrap → sizing migration → partial exit migration → trade bridge → matrix readout`
4. 父系统 runner 普遍产出 JSON summary + markdown report 落入 `temp/` 或 `report/` 目录；本系统当前只把该产物形态冻结为目标态，不冒充已实现
5. 三层上线成熟度（见 §9）、四档信任分级（见 §9），来自 `15-system-launch-readiness-matrix-charter`
6. 关键概念原则：书本来源 ≠ 系统实现，必须按三档（已实现/部分实现/未实现）严格区分

**本系统（Lifespan-Quant）当前实现：**
1. `run_daily_signal_scan()` — 每日全市场信号扫描，已实现
2. 主链路：data → MALF 摘要/兼容背景 → structure_snapshot → adverse_conditions → PAS detectors → PasSignal
3. **待补**：`run_backtest_window`（时间窗回测）、`run_system_closeout`（主线验证）、run metadata 落库

### 1.2 与父系统的主要差异

| 差异点 | 父系统（MarketLifespan） | 本系统（Lifespan-Quant） |
|---|---|---|
| 链路 | data → malf → PAS → position → trade | data → malf → **structure(filter)** → alpha/pas → position → trade |
| Runner 数量 | 4 个 | 3 个（scan / backtest / closeout） |
| BPB 状态 | 已正式验证但非主线 | **永久禁止于 system 层** |
| 治理脚本 | 13 个 | 精简为 4 个核心脚本 |
| Run 元数据 | 写入 research_lab | 目标态为 `_meta_runs` + JSON 文件；当前代码尚未核实持久化写入 |

---

## 2. 模块定位

`system` 是**唯一的主线编排层**，是系统价值的最终交付入口。

**核心职责**：按序调用各业务模块的公开接口。当前已核实到的是“单日扫描编排 + 解释链汇总”；批量回测、closeout、run metadata 落库仍属于目标态 runner。

**`system` 只做编排，不做计算。** 所有业务逻辑必须在对应模块中实现。

---

## 3. 主线链路（冻结）

```
data → malf → structure(filter) → alpha/pas → position → trade → system
```

| 环节 | 对应模块 | 职责 |
|---|---|---|
| data | `lq.data` | 拉取、清洗、复权价构建 |
| malf | `lq.malf` | 正式 MALF 摘要 + 兼容背景字段生成 |
| structure | `lq.structure` | 结构位语言识别 |
| filter | `lq.filter` | 不利条件过滤（adverse conditions） |
| alpha/pas | `lq.alpha.pas` | PAS 触发器检测（默认主线仅启用 `MAINLINE / CONDITIONAL`；`BPB / CPB` 不进入默认主线） |
| position | `lq.position` | 仓位规划（1R sizing + 退出合同） |
| trade | `lq.trade` | 交易执行 + 回测引擎 |
| system | `lq.system` | 编排总控 |

---

## 4. 三级 Runner（正式入口）

| Runner | 模式 | 职责 | 状态 |
|---|---|---|---|
| `run_daily_signal_scan` | SCAN | 单日全市场信号扫描，输出 `SystemRunSummary` | 已实现 |
| `run_backtest_window` | BACKTEST | 时间窗全链路回测（PAS→position→trade）| 待实现 |
| `run_system_closeout` | CLOSEOUT | 主线 smoke 验证，确认主线可重跑 | 待实现 |

---

## 5. 正式输入

1. `run_date`（扫描日）或 `[start_date, end_date]`（回测窗口）
2. `codes: list[str]`（待扫描股票池）
3. `enabled_patterns: list[str]`（允许的 PAS 触发器；默认仅启用 `MAINLINE / CONDITIONAL`，因此 `BPB / CPB` 不进入默认主线）
4. `workspace: WorkspaceRoots`（数据库路径集合，来自环境变量）
5. `RunMode`（SCAN / BACKTEST / CLOSEOUT）

---

## 6. 正式输出

**system 不拥有自己的正式数据库**。目标态只向已有数据库写运行元数据；当前最小实现未核实任何持久化写入。

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `SystemRunSummary` | `dataclass` | 当前返回内存对象；未核实 JSON 落盘 |
| `SystemBacktestSummary` | `dataclass` | 目标态输出（report 目录），当前未实现 |
| `SystemCloseoutSummary` | `dataclass` | 目标态输出（report 目录），当前未实现 |
| run_id 流水 | 行记录 | 目标态写入 `_meta_runs`；当前未核实 |

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
2. 当前已实现 `run_daily_signal_scan`；冻结 `run_backtest_window / run_system_closeout` 的目标态边界，但不把它们冒充为完成事实
3. 运行日志与错误捕获（当前至少以 `scan_errors` 形式返回，不允许静默失败）
4. 冻结 run_id / `_meta_runs` / summary 文件输出的目标态合同
5. 治理脚本入口（`scripts/system/`）作为目标态预留，当前未核实完整实现

### 8.2 不负责

1. 任何业务计算（属于各业务模块）
2. 数据库 schema 创建（属于各模块 bootstrap）
3. 报告可视化（属于 report 脚本）
4. MSS/IRS 计算（不在 Lifespan-Quant 主线）
5. 自有正式数据库（system 无状态库；目标态也只允许写 `_meta_runs`，不拥有独立业务库）

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
3. **REJECTED trigger 不得进入主线**：当前至少 `BPB / CPB` 不得进入 `system` 默认调用路径；其中 BPB 仍需显式视为永久禁止
4. **system 无自有数据库**：目标态只允许写已有数据库中的 `_meta_runs` 与 temp/report 产物；在当前未实现持久化前，不得把这条写权表述成既成事实
5. **run_id 必须存在**：当前已实现 runner `run_daily_signal_scan()` 必须生成 run_id；未来其他 runner 也必须遵守
6. **禁止静默失败**：任何业务模块调用异常必须被捕获；当前最小实现至少要进入 `scan_errors`
7. **来源 ≠ 实现**：书本概念不自动等于系统已实现能力，三档严格区分
8. **上线层级显式声明**：提到"系统上线"必须同时标明 L1/L2/L3 中的哪一层

---

## 11. 成功标准

1. `run_daily_signal_scan` 端到端运行，覆盖主线全链路（已完成）
2. 当前 `SystemRunSummary` 能返回 `pattern_counts / top_signals / scan_errors / stock_traces`
3. `BPB / CPB` 在任何 system 默认调用路径中均不出现
4. `run_backtest_window / run_system_closeout / _meta_runs` 若后续补齐，必须另开卡并同步升级本文档
5. 运行失败时必须有可读错误轨迹；当前最小实现不能静默吞掉 scan 级异常

---

## 12. 设计文档索引

| 文档 | 内容 |
|---|---|
| `00-system-charter-20260331.md`（本文） | 模块章程、血统、架构、铁律 |
| `01-system-orchestration-design-20260401.md` | 三级 runner 设计、run_id 规范、run metadata、全链路伪代码 |
| `02-system-launch-readiness-and-governance-20260401.md` | 上线成熟度矩阵、信任分级当前状态、治理脚本清单 |
