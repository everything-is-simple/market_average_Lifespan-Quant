# 015. 复权因子单测补全 记录

## 对应关系

1. 对应卡：`docs/03-execution/015-unit-test-adjust-factor-card-20260406.md`
2. 对应证据：`docs/03-execution/evidence/015-unit-test-adjust-factor-evidence-20260408.md`

## 本轮执行记录

1. 复核并重写了 `015` 卡，将其收敛为当前系统口径的复权因子单测补全卡。
2. 在卡内固定了问题边界：本卡只补关键路径的最小单测保护，不直接扩写完整 data 测试体系。
3. 在卡内明确：所有测试必须使用固定输入数据，不依赖正式数据库与网络。
4. 在卡内补入闭环文件段，明确 evidence / record / conclusion 的路径约定。
5. 创建了本次 evidence 文档，用于记录当前已完成的 execution 准备动作与待补测试证据。
6. 已把当前正式补测锚点收敛到 `adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()`。
7. 已明确当前仓库中未确认现成 `adjust_factor` 单测文件，因此真实关闭动作应从“新建测试文件”开始，而不是补跑旧测试。
8. 已新建 `tests/unit/data/test_adjust_factor.py`，覆盖无事件、单事件、复合事件、多事件累乘与 `apply_backward_adjustment()` 输出校验。
9. 已执行 `python -m pytest tests/unit/data/test_adjust_factor.py -q`，结果为 `5 passed in 2.17s`。

## 当前运行口径

1. 本卡已具备真实测试执行结果，可转为 `closed`。
2. 本卡当前可以明确宣告：复权因子链已具备最小关键路径测试保护。
3. 本卡的后续工作不再是“补最小单测”，而是如 `014` 抽样发现异常，再按需扩展边界场景。

## 未完成项

1. 当前无阻塞未完成项；本卡已完成闭环。

## 首张真实关闭候选判断

1. 当前最适合优先推进到真实关闭的卡是 `015`。
2. 原因不是它最重要，而是它的关闭路径最短、边界最清楚、验收最客观。
3. 已确认的直接入口是 `src/lq/data/compute/adjust.py` 中的 `compute_backward_factors()` 与 `apply_backward_adjustment()`。
4. 本轮已按该路径完成：先补测试，再跑 pytest，最后进入 conclusion 收口。

## 正式关闭路线

1. 已在 `tests/unit/data/` 下新增针对 `adjust.py` 的测试文件。
2. 已覆盖五类最小场景：无事件、单一分红、单一复合事件、多事件累乘、`apply_backward_adjustment()` 输出校验。
3. 已执行 pytest，并把通过结果写入 evidence。
4. 已新建 `015-unit-test-adjust-factor-conclusion-20260408.md`，并明确回答“复权因子链是否已具备最小单测保护”。
