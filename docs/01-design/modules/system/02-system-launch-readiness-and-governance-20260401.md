# system 模块 — 上线成熟度与治理设计 / 2026-04-01

## 1. 设计目标

本文定义 `system` 模块的上线成熟度评估框架与治理脚本清单，包括：

1. 三层上线定义的具体门控条件
2. 四档信任分级的当前能力评估
3. 概念边界三档裁定表（来源书义 vs 系统实现）
4. 治理脚本清单与职责
5. 当前阻塞项 / 非阻塞研究储备

来源：父系统 `15-system-launch-readiness-matrix-charter-20260329.md` + `11-system-selected-concept-definition-boundary-20260328.md`

---

## 2. 三层上线定义与门控条件

### 2.1 L1 研究验证正式上线（当前目标）

**定义**：系统可稳定支持 `data → malf → structure(filter) → alpha/pas → position → trade` 研究验证主线，可做正式 readout。

**门控条件（全部满足才算 L1 达成）**：

| 门控项 | 验证方式 | 当前状态 |
|---|---|---|
| G1 data 层可用 | `market_base.adj_daily_bar` 有近 3 年数据 | 已完成 |
| G2 malf 三层可用 | `build_malf_context_for_stock()` 对抽样股票无报错 | 已完成 |
| G3 structure/filter 可用 | `build_structure_snapshot()` + `check_adverse_conditions()` 可运行 | 已完成 |
| G4 PAS 至少 1 个主线触发器可用 | BOF 或 PB 探测器正确识别信号 | 已完成（BOF/PB） |
| G5 position sizing 可用 | `compute_position_plan()` 产出合法 lot_count | 已完成 |
| G6 trade 回测可运行 | `BacktestEngine` 在 30 日窗口无崩溃 | 待验证 |
| G7 system closeout 通过 | `run_system_closeout()` 返回 `closeout_ready=True` | 待实现 |
| G8 BPB 全链路未出现 | grep 全量代码无 BPB 调用路径 | 需治理脚本确认 |

**禁止混用**：L1 达成 ≠ 可以声称"零售散户照做也差不多"，必须在所有报告中显式标注"研究验证层结论"。

### 2.2 L2 执行仿真正式上线（待开卡）

**定义**：在 L1 基础上，补齐 raw-execution 价格对齐与数据可信度重验。

**必须补齐的项**（当前均未开卡）：

| 待补项 | 说明 |
|---|---|
| M1 raw-execution 价格对齐 | 用真实 T+1 开盘价（非后复权）验证止损计算不失真 |
| M2 数据可信度重验 | mootdx 本地数据与通达信原始数据交叉验证 |
| M3 流动性过滤 | 实盘最低成交量门槛（防止无法成交的股票入选） |
| M4 A 股涨跌停处理 | 涨跌停日无法以开盘价成交的场景 |

### 2.3 L3 零售可执行正式上线（远期）

**定义**：在 L2 基础上，补齐可面向普通交易者稳定解释和执行的完整合同。

当前**不应讨论** L3 上线条件，以免污染 L1/L2 目标的执行焦点。

---

## 3. 四档信任分级——当前能力评估

### 3.1 Lifespan-Quant 各能力信任分级

| 能力 | 信任档 | 说明 |
|---|---|---|
| mootdx 本地日线数据 | T1 | 有 design/spec/conclusion，直接支撑主线 |
| 后复权因子（gbbq）计算 | T1 | 已正式实现并测试 |
| MALF 月线状态 8 分类 | T1 | 已正式冻结，直接支撑 PAS 背景层 |
| MALF 周线流向 | T1 | 已正式冻结 |
| MALF 日线现象（触发位） | T1 | 已正式冻结 |
| BOF 触发器 | T1 | 已正式验证（继承自父系统结论） |
| PB 触发器 | T2 | 有边界可用，需独立 16 格验证才升 T1 |
| TST 触发器 | T2 | 有边界可用，待独立验证 |
| CPB 触发器 | T2 | 有边界可用，待独立验证 |
| BPB 触发器 | T3 | 已研究验证，**永久禁止进入主线 system 层** |
| structure 结构位语言 | T2 | 有边界可用，filter 已实现，但结构位精度待验 |
| adverse conditions filter | T2 | 有边界可用，过滤逻辑已实现，参数待回测优化 |
| position sizing（FIXED_NOTIONAL） | T1 | 已正式冻结，operating 控制基线 |
| position sizing（SINGLE_LOT） | T1 | 已正式冻结，floor sanity 基线 |
| partial exit（FIRST_TARGET_TRAIL） | T2 | 有边界可用，exit 合同已定义，回测验证待补 |
| TradeManager 5 阶段状态机 | T1 | 已实现，有单元测试 |
| BacktestEngine（T+1 开盘撮合） | T2 | 设计已冻结，待完整实现 |
| A 股成本模型 | T1 | 公式已冻结，实现待补 |
| run_daily_signal_scan | T1 | 已实现可运行 |
| run_backtest_window | T3 | 设计完成，代码待实现 |
| run_system_closeout | T3 | 设计完成，代码待实现 |

### 3.2 当前 T1（核心可信）能力摘要

系统已具备以下核心可信能力链：

```
mootdx 本地数据（T1）
  → MALF 三层背景（T1）
    → BOF 触发器（T1）
      → FIXED_NOTIONAL position sizing（T1）
        → TradeManager 5阶段状态机（T1）
          → run_daily_signal_scan（T1）
```

这条链是 L1 上线的核心骨干，其余 T2/T3 能力作为边界条件或研究补充。

---

## 4. 概念边界三档裁定表

来源：父系统 `11-system-selected-concept-definition-boundary-20260328.md`

原则：**书本来源 ≠ 系统实现**。下表按三档裁定（已实现 / 部分承接 / 未实现）。

| 概念 | 来源书义 | 系统承接状态 | 系统实现证据 |
|---|---|---|---|
| 市场平均寿命（MALF） | YTC 卷 2 波浪结构 + 《交易圣经》生命周期 | **已实现** | `lq.malf` 三层矩阵，`MalfContext` 合同 |
| PAS 触发形态（BOF） | YTC 卷 3 BOF 策略 | **已实现** | `lq.alpha.pas.detectors.BOFDetector` |
| PAS 触发形态（PB/TST/CPB） | YTC 卷 3 | **部分承接** | 代码存在，独立 16 格验证未全部完成 |
| 1R 仓位规模（固定风险） | 《交易圣经》第 8 章 | **已实现** | `compute_position_plan()` + `FIXED_NOTIONAL_CONTROL` |
| 止损移位（保本止损） | 《交易圣经》第 8 章 | **已实现** | `TradeManager.BREAKEVEN_TRIGGER_R=0.5` |
| 跟踪止损（runner） | 《交易圣经》第 8 章 | **已实现** | `TradeManager.TRAILING_STEP_PCT=0.06` |
| 时间止损 | 《专业投机原理》 | **已实现** | `TradeManager.MAX_HOLD_DAYS=20` |
| 市场结构位语言 | YTC 卷 2 | **部分承接** | `lq.structure` 已实现，精度验证待补 |
| MSS 市场状态分级 | 爷爷系统 | **未实现** | Lifespan-Quant 主线不引入 |
| IRS 行业轮动 | 爷爷系统 | **未实现** | Lifespan-Quant 主线不引入 |
| 多资产组合优化 | 专业量化文献 | **未实现** | 当前单票独立管理 |
| 实盘下单（easytrader） | — | **未实现** | BrokerAdapter Protocol 已定义但未实现 |
| 小时线早预警 | YTC | **未实现** | 数据层仅有日线 |

---

## 5. 治理脚本清单

位置：`scripts/system/`

父系统有 13 个治理脚本，本系统精简为 4 个核心脚本，覆盖最关键的治理检查。

| 脚本 | 职责 | 触发时机 |
|---|---|---|
| `check_file_length_governance.py` | 检查所有 `.py` 文件是否超过 1000 行（目标 800 行）| 每次提交前 |
| `check_chinese_governance.py` | 检查正式模块是否有必要的中文注释 | 每次提交前 |
| `check_dependency_matrix.py` | 检查模块依赖矩阵是否有违规横向依赖 | 每次提交前 |
| `check_bpb_absence.py` | grep 全量代码确认 BPB 未出现在 system 调用路径 | 每次提交前 |

### 5.1 check_dependency_matrix.py 规则

```python
ALLOWED_DEPS = {
    "core":     set(),
    "data":     {"core"},
    "malf":     {"core", "data"},
    "structure":{"core", "data"},
    "filter":   {"core", "data", "malf", "structure"},
    "alpha":    {"core", "data", "malf"},
    "position": {"core", "data"},
    "trade":    {"core", "data", "position"},
    "system":   {"core", "data", "malf", "structure", "filter", "alpha", "position", "trade"},
    "report":   {"core", "data", "trade"},   # 只读消费
}
# 任何不在上表中的 import 都视为违规
```

### 5.2 check_bpb_absence.py 规则

```python
# 检查范围：src/lq/system/
# 检查关键字：BPB, "bpb", PasTriggerPattern.BPB
# 例外：注释中说明"BPB 禁止"的行（以 # 开头）不报错
```

---

## 6. 阻塞项与非阻塞研究储备

### 6.1 L1 上线阻塞项（必须补齐）

| 项目 | 说明 | 优先级 |
|---|---|---|
| B1 `run_backtest_window` 实现 | 时间窗全链路回测 runner | 高 |
| B2 `run_system_closeout` 实现 | 主线 smoke 验证 runner | 高 |
| B3 `BacktestEngine` 完整实现 | Broker 类 + 日循环 + 成本模型 | 高 |
| B4 `_meta_runs` bootstrap | trade_runtime.duckdb 初始化新增此表 | 中 |
| B5 BPB 治理脚本通过 | `check_bpb_absence.py` 零报告 | 中 |

### 6.2 非阻塞研究储备（当前不卡 L1）

| 项目 | 说明 | 对应信任档 |
|---|---|---|
| R1 PB/TST/CPB 独立 16 格验证 | 升 T1 需要，但不卡 L1 | T2 |
| R2 structure 精度验证 | 结构位识别回测优化 | T2 |
| R3 adverse conditions 参数优化 | 过滤参数回测调优 | T2 |
| R4 raw-execution 价格对齐 | L2 必须项 | T3 |
| R5 easytrader 实盘适配 | L3 方向 | T3 |
| R6 小时线早预警 | 需增加日内数据源 | T4 |
| R7 MSS/IRS 恢复 | 历史 EQ-gamma 能力，可选 sidecar | T4 |

---

## 7. 上线声明规范

任何在文档、报告、代码注释中出现"系统已上线"类说法，必须同时标注：

```
上线层级：L1（研究验证正式上线）
信任分级：[具体引用 T1/T2 能力]
价格口径：研究层后复权价格，非 raw-execution 真实价格
适用范围：个人研究验证，非零售交易建议
```

禁止出现的混说法：
- "研究层已跑通，所以实盘应该也差不多"
- "三年回测通过，可以直接按信号操作"
- "系统已经完成，可以给别人用"
