# alpha / PAS 模块章程 / 2026-03-31

## 1. 血统与来源

| 层代 | 系统 | 状态 |
|---|---|---|
| 爷爷系统 | `G:\。backups\EmotionQuant-gamma` 的 `normandy` 模块（PAS 五形态原型） | 思想原型，仅参考 |
| 父系统 | `G:\MarketLifespan-Quant\docs\01-design\modules\alpha\` | 正式定型，完整设计 |
| 本系统 | `G:\Lifespan-Quant\src\lq\alpha\` | 继承父系统 PAS 五 trigger，新增 `structure` 前置层与第一 PB 追踪 |

## 2. 模块定位

`alpha` 是研究信号模块。
它负责把通过过滤器的候选股票与冻结后的 MALF 背景，转化为可验证、可审计的 PAS 触发信号。

当前正式范围：

1. `selector`（最小候选集筛选）
2. `PAS`（五 trigger 探测，当前主线只用 BOF + PB）
3. `IRS-minimal`（行业分桶约束，避免组合过度集中）

## 3. PAS 五 Trigger 冻结地位（继承父系统全部结论）

| Trigger | 地位 | 有效准入格 | 父系统结论卡 |
|---|---|---|---|
| `BOF` | **core / primary_trend_driver** | persisting 四格为主力（non-sparse 集中于 BULL/BEAR_PERSISTING × MAINSTREAM/COUNTERTREND） | 93 |
| `PB` | **conditional / conditional_assist_driver** | `BULL_PERSISTING + with_flow`，`BEAR_PERSISTING + against_flow` | 110, 121 |
| `TST` | **conditional / conditional_assist_driver** | `BULL_PERSISTING + with_flow`，`BEAR_PERSISTING + against_flow` | 126 ✅ |
| `CPB` | **conditional / conditional_assist_driver** | `BULL_PERSISTING + with_flow`，`BEAR_PERSISTING + against_flow` | 129 ✅ |
| `BPB` | **excluded / not_for_long_alpha** | — | 93, 131 |

**说明：**
- TST 和 CPB 均已完成父系统三年独立验证，不再是"待验证"。
- 条件格准入：必须同时满足 `monthly_state ∈ {BULL_PERSISTING, BEAR_PERSISTING}` + 正确 `weekly_flow`，才允许进入主线。
- BPB 永久禁止进入主线，无论测试结果如何。
- 价格口径：信号层以 `backward-adjusted` 为准（研究层合同），尚未对齐 raw-execution 口径（父系统 130 号卡边界说明）。

## 4. 正式输入

1. 日线 `DataFrame`（来自 `market_base.duckdb`，已通过 `filter` 模块的不利条件检查）
2. `MalfContext`（来自 `malf` 模块，三层主轴快照）
3. `StructureSnapshot`（来自 `structure` 模块，结构位识别结果）

**必须先经过 `filter` 模块的不利条件过滤，才能进入 trigger 探测。**

## 5. 正式输出

| 输出对象 | 类型 | 去向 |
|---|---|---|
| `PasSignal` | `dataclass`（冻结合同） | 落入 `research_lab.duckdb`（L3） |

`PasSignal` 是本模块对外唯一正式合同。包含信号日期、trigger 类型、MALF 表面标签、第一 PB 序号等。

## 6. 与父系统的核心差异

| 项目 | 父系统 | 本系统 |
|---|---|---|
| 前置过滤 | 月线背景过滤（局部） | 独立 `filter` 模块（五类不利条件） |
| 结构位 | trigger 内部隐含 | 独立 `structure` 模块，统一 `BreakoutEvent` 合同 |
| 第一 PB 追踪 | 未实现 | `pb_sequence_number` 字段，区分初次 / 二次入场 |
| 突破语义 | 各 trigger 自定义 | `BreakoutType` 枚举统一分类 |
| 包名 | `mlq.alpha` | `lq.alpha.pas` |

## 7. 模块边界

### 7.1 负责

1. 候选集初步筛选（selector）
2. PAS 五 trigger 探测与状态机
3. 第一 PB 序号追踪
4. 研究 trace、signal registry 与 run 元数据
5. IRS 行业分桶约束（最小化）

### 7.2 不负责

1. `market_base` 的拥有与构建（属于 `data`）
2. MALF 三层矩阵计算（属于 `malf`）
3. 结构位识别（属于 `structure`）
4. 不利条件过滤（属于 `filter`）
5. 仓位规划与退出（属于 `position`）
6. 直接写 `trade_runtime`（必须经过 `position` 桥接）

## 8. 铁律

1. 任何 trigger 探测必须在通过 `filter` 之后，不允许绕过过滤器。
2. `BPB` 禁止在 `system` 层启用，无论测试结果如何。
3. `PasSignal` 的 `signal_id` 必须全局唯一（格式：`PAS_{version}_{code}_{date}_{pattern}`）。
4. `alpha` 不直接写 `trade_runtime`；研究结果只能经冻结桥接后才进入正式交易。
5. `TST` / `CPB` 已完成独立三年验证（父系统 126 / 129 号卡），仅限条件格准入，不得扩展到全 16 格。

## 9. 成功标准

1. `BOF` 和 `PB`/`TST`/`CPB` trigger 的准入格 cell gate 函数正确实现
2. `PasSignal` 合同冻结，含 `pb_sequence_number` 字段
3. `filter` 前置通过后的股票才触发 trigger 探测
4. IRS 行业分桶约束能防止组合过度集中单一行业
5. 研究结果可追溯到具体 run、窗口、参数和证据
6. `ADMISSION_TABLE` 和 `cell_gate_check()` 均对齐父系统 93/110/126/129/131 冻结结论

## 10. 本模块设计文档索引

| 文档 | 内容 | 继承父系统来源 |
|---|---|---|
| `00-alpha-charter-20260331.md` | 模块章程（本文） | 父系统 `00 / 01` |
| `01-pas-five-trigger-frozen-hierarchy-20260401.md` | 五 trigger 冻结层级与地位（全部结论汇总） | 父系统 93/110/121/126/129/131 |
| `02-pas-cell-gate-and-16cell-admission-design-20260401.md` | 16 格准入表与 cell_gate_check 设计 | 父系统 110/126/129/131 |
| `03-pas-contracts-and-output-governance-20260401.md` | PasSignal 合同冻结、pas_selected_trace 表名治理 | 父系统 `01-pas-selected-trace` |
