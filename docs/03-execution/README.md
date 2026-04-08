# 执行闭环区 / 03-execution

## 用途

执行卡、证据、记录、结论。每一刀实现都必须在这里留下闭环痕迹。

## 闭环四件套

每个执行任务必须包含：

1. **card** — 任务卡（目标、边界、关闭条件）
2. **evidence** — 执行证据（命令、参数、输出摘要）
3. **record** — 执行记录（实际发生了什么）
4. **conclusion** — 结论（是否达成目标，下一步是什么）

## 当前状态

当前系统处于 **v0.1.0 主线纠偏中段**。

## 卡目录

卡文件平铺于本目录，格式：`{NNN}-{title}-card-{YYYYMMDD}.md`；
证据落入 `evidence/`，执行记录落入 `records/`，结论与卡同目录。

## 历史卡

- `001` — data 全链路 bootstrap（`historical`，早期 txt 全量导入路线，现仅供追溯）→ `001-data-full-pipeline-bootstrap-card-20260404.md`
- `007` — malf 端到端验证（`superseded`，旧 MALF 主轴验证卡，已不适配 `016` 之后的正式主轴）→ `007-malf-end-to-end-validation-card-20260406.md`
- `012` — CPB 语义收敛 + 独立验证（`historical`，当前主线已将 `CPB` 归为 `REJECTED`）→ `012-cpb-semantic-convergence-validation-card-20260406.md`

## 已闭环卡

- `002-006` — 七库持久化 pipeline 合并闭环 → `002-006-persistence-pipeline-conclusion-20260407.md`

  - 证据：`evidence/002-006-persistence-pipeline-evidence-20260407.md`
  - 记录：`records/002-006-persistence-pipeline-record-20260407.md`
  - 结论：`002-006-persistence-pipeline-conclusion-20260407.md`

- `015` — 复权因子单测补全 → `015-unit-test-adjust-factor-conclusion-20260408.md`

  - 证据：`evidence/015-unit-test-adjust-factor-evidence-20260408.md`
  - 记录：`records/015-unit-test-adjust-factor-record-20260408.md`
  - 结论：`015-unit-test-adjust-factor-conclusion-20260408.md`

- `002` — malf 持久化 bootstrap（`superseded`，已被 `002-006` 合并闭环覆盖）→ `002-malf-persistence-bootstrap-card-20260406.md`
- `003` — structure 持久化 bootstrap（`superseded`，已按当前系统口径纠偏，闭环地位由 `002-006` 承接）→ `003-structure-persistence-bootstrap-card-20260406.md`
- `004` — filter 持久化 bootstrap（`superseded`，已按当前系统口径纠偏，闭环地位由 `002-006` 承接）→ `004-filter-persistence-bootstrap-card-20260406.md`
- `005` — research_lab 持久化 bootstrap（`superseded`，已按当前系统口径纠偏，闭环地位由 `002-006` 承接）→ `005-research-lab-persistence-bootstrap-card-20260406.md`
- `006` — trade_runtime 持久化 bootstrap（`superseded`，已按当前系统口径纠偏，闭环地位由 `002-006` 承接）→ `006-trade-runtime-persistence-bootstrap-card-20260406.md`
- `016` — MALF 四格上下文与生命周期执行合同重定向 → `016-malf-four-context-lifecycle-contract-reset-card-20260407.md`
- `017` — MALF 兼容桥接与 PAS 准入修正 → `017-malf-compatibility-bridge-and-pas-gate-fix-card-20260407.md`
- `018` — system 解释链 MALF 摘要收敛 → `018-system-trace-malf-summary-convergence-card-20260407.md`
- `019` — filter A4-5 背景合同收敛 → `019-filter-a45-background-contract-convergence-card-20260407.md`
- `020` — MALF execution_context_snapshot bootstrap → `020-malf-execution-context-snapshot-bootstrap-card-20260407.md`
- `021` — PAS / position execution_context_snapshot 消费迁移 → `021-pas-position-execution-context-consumer-migration-card-20260407.md`

## 待重写卡

- 当前为空。

## 待执行验证卡

说明：当前仍保留为 `pending-validation` 的卡，已陆续补入“准备态” `evidence / record` 文件；只有真实执行统计或测试完成后，才允许创建各自的 `conclusion` 并转为 closed。

- `008` — BOF 在 BULL_MAINSTREAM 格的独立三年验证（`pending-validation`）→ `008-bof-bull-mainstream-three-year-validation-card-20260406.md`
- `009` — structure 与 BOF 联合验证（`pending-validation`，已按当前系统口径纠偏）→ `009-structure-bof-joint-validation-card-20260406.md`
- `010` — filter 不利条件过滤器效果评估（`pending-validation`，已按当前系统口径纠偏）→ `010-filter-adverse-condition-evaluation-card-20260406.md`
- `011` — TST 独立正式验证（`pending-validation`）→ `011-tst-independent-validation-card-20260406.md`
- `013` — 第一 PB 假说独立验证（`pending-validation`）→ `013-first-pb-hypothesis-validation-card-20260406.md`
- `014` — L2 后复权抽样验证（`pending-validation`，已按当前系统口径纠偏）→ `014-l2-backward-adjust-sampling-validation-card-20260406.md`
