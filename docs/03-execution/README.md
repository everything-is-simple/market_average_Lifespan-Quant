# 执行闭环区 / 03-execution

## 用途

执行卡、证据、记录、结论。每一刀实现都必须在这里留下闭环痕迹。

## 闭环四件套

每个执行任务必须包含：
1. **card** — 任务卡（目标、前置、验收标准）
2. **evidence** — 执行证据（命令、参数、输出摘要）
3. **record** — 执行记录（实际发生了什么）
4. **conclusion** — 结论（是否达成目标，下一步是什么）

## 当前状态

当前系统处于**初始构建阶段（v0.1.0）**。

已完成：
- 系统架构冻结（`docs/01-design/`）
- 核心模块实现（`src/lq/`：core/data/malf/structure/alpha/filter/position/trade/system）
- 基础单测覆盖（`tests/unit/`）
- 首次提交至 GitHub
- `core` 模块补全：`checkpoint.py`（JsonCheckpointStore）+ `resumable.py`（6 个续跑工具），203 passed（2026-04-02）
- 全模块 `__init__.py` 填充对齐（core/data/malf/alpha.pas/position，2026-04-02）
- 核心设计文档同步更新（`docs/01-design/modules/core/`，2026-04-02）
- **七库全持久化架构审查（2026-04-05）**：确认七库全部必要；修复 `paths.py` 缺失 `structure`/`filter` 两路径；修复 `00-system-overview` 模块职责表矛盾；落盘空间换时间设计决策备忘（§6.1）、批处理内存控制合同（`01-system-architecture` §5）、`config_hash` 机制规格（`02-spec` §3.1/3.2）

## 卡目录

卡文件平铺于本目录，格式：`{NNN}-{title}-card-{YYYYMMDD}.md`；
证据落入 `evidence/`，执行记录落入 `records/`，结论与卡同目录。

已开卡：
- `001` — **data 全链路 bootstrap**（txt 全量灌入 + 路径修正，2026-04-04）→ `001-data-full-pipeline-bootstrap-card-20260404.md`
- `002` — **malf 六层流水线持久化 bootstrap** → `002-malf-persistence-bootstrap-card-20260406.md` ✅ Closed（2026-04-07）
- `003` — **structure 持久化层 bootstrap** → `003-structure-persistence-bootstrap-card-20260406.md` ✅ Closed（2026-04-07）
- `004` — **filter 持久化层 bootstrap** → `004-filter-persistence-bootstrap-card-20260406.md` ✅ Closed（2026-04-07）
- `005` — **research_lab 持久化 bootstrap**（alpha/pas） → `005-research-lab-persistence-bootstrap-card-20260406.md` ✅ Closed（2026-04-07）
- `006` — **trade_runtime 持久化 bootstrap** → `006-trade-runtime-persistence-bootstrap-card-20260406.md` ✅ Closed（2026-04-07）
- `016` — **MALF 四格上下文与生命周期执行合同重定向**（design-reset / lifecycle-contract，2026-04-07）→ `016-malf-four-context-lifecycle-contract-reset-card-20260407.md` ✅ Closed

002-006 合并闭环：
- 证据：`evidence/002-006-persistence-pipeline-evidence-20260407.md`
- 记录：`records/002-006-persistence-pipeline-record-20260407.md`
- 结论：`002-006-persistence-pipeline-conclusion-20260407.md`

待开卡（验证层，待 002-006 完成后启动）：
- `007` — **malf 端到端验证**（四格上下文 / 月线八态诊断 / 周线流向 / 生命周期排位）→ `007-malf-end-to-end-validation-card-20260406.md`；依赖 002
- `008` — **BOF 在 BULL_MAINSTREAM 格的独立三年验证**（2020-2022 胜率 / R 倍数 / 净收益）→ `008-bof-bull-mainstream-three-year-validation-card-20260406.md`；依赖 006
- `009` — **structure 与 BOF 联合验证**（结构位区分力 / available_space_pct 阈值）→ `009-structure-bof-joint-validation-card-20260406.md`；依赖 006
- `010` — **filter 不利条件过滤器效果评估**（五类条件触发率 / 三组对比 / 逐类贡献）→ `010-filter-adverse-condition-evaluation-card-20260406.md`；依赖 006
- `011` — **TST 独立正式验证**（年度拆分 / 16 格拆分 / 与 v0.01 对比）→ `011-tst-independent-validation-card-20260406.md`；依赖 006
- `012` — **CPB 语义收敛 + 独立验证**（与 BOF 重叠度 / 独有信号表现 / REJECTED 确认或升级）→ `012-cpb-semantic-convergence-validation-card-20260406.md`；依赖 006
- `013` — **第一 PB 假说独立验证**（pb_sequence_number=1 vs ≥2 / 假说判定）→ `013-first-pb-hypothesis-validation-card-20260406.md`；依赖 006
- `014` — **L2 后复权抽样验证**（20 只抽样 / 通达信对照 / gbbq 因子链）→ `014-l2-backward-adjust-sampling-validation-card-20260406.md`；依赖 001
- `015` — **单测补全 test_adjust_factor.py**（≥10 用例 / 四类权益事件 / 边界条件）→ `015-unit-test-adjust-factor-card-20260406.md`；依赖 001
