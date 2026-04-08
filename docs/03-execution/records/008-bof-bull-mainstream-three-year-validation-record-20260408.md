# 008. BOF 在 BULL_MAINSTREAM 格的独立三年验证 记录（准备态）

## 对应关系

1. 对应卡：`docs/03-execution/008-bof-bull-mainstream-three-year-validation-card-20260406.md`
2. 对应证据：`docs/03-execution/evidence/008-bof-bull-mainstream-three-year-validation-evidence-20260408.md`

## 本轮执行记录

1. 复核并重写了 `008` 卡，收敛为当前系统口径的 `BOF` 主线验证卡。
2. 在卡内明确：旧 `BULL_MAINSTREAM` 仅保留为历史命名，正式背景拆分不得继续依赖旧 `surface_label` 主轴。
3. 在卡内明确了本卡只验证 `BOF` 表现，不直接修改 detector、position sizing 或 trade 执行模板。
4. 在卡内补入闭环文件段，明确 evidence / record / conclusion 的路径约定。
5. 创建了本次 evidence 文档，记录当前已完成的 execution 准备动作与待补统计证据。

## 当前运行口径

1. 本卡属于 `pending-validation`，尚未转为 closed。
2. 本卡当前不产生任何统计结论，不宣告 `BOF` 已被重新验证通过。
3. 正式关闭前，必须补齐三年窗口样本提取、年度拆分、正式背景拆分与结论文档。

## 未完成项

1. 确认真实三年窗口的样本筛选口径与时间边界。
2. 提取正式 `BOF` 信号、仓位计划、交易结果。
3. 生成总表、年度拆分表、正式背景拆分表。
4. 真实执行完成后创建 conclusion 文件，并回填最终判断。
