# 019. filter A4-5 背景合同收敛 记录

## 对应关系

1. 对应卡：`docs/03-execution/019-filter-a45-background-contract-convergence-card-20260407.md`
2. 对应证据：`docs/03-execution/evidence/019-filter-a45-background-contract-convergence-evidence-20260407.md`

## 执行记录

1. 先复核 `filter` 设计文档与现有实现，确认 A4-5 仍把 `monthly_state / weekly_flow` 写成正式主轴，这与 `016` 冻结后的 MALF 正式摘要不一致。
2. 修订 `01-filter-adverse-conditions-design-20260401.md`，将 A4-5 的正式表述改为：
   - 正式背景摘要：`long_background_2 / intermediate_role_2 / malf_context_4`
   - 兼容细粒度：`monthly_state / weekly_flow`
3. 同步修订 `00-filter-charter-20260401.md`，避免章程与细则之间出现口径撕裂。
4. 修订 `src/lq/filter/adverse.py`：
   - 先以 `long_background_2 != "BEAR"` 快速放行非熊市背景
   - 将“熊市持续 + 逆势反弹”的表达从 `weekly_flow` 收敛到 `intermediate_role_2`
   - 保留 `monthly_state` 对 `BEAR_FORMING / BEAR_PERSISTING` 的细粒度区分
5. 为 A4-5 新增 `COUNTERTREND` 回归测试，并跑通过 `tests/patches/filter/test_bear_forming_block.py`。

## 结果摘要

1. `filter` A4-5 现在在文档和实现两侧都不再把 `weekly_flow` 表述为正式主轴。
2. `monthly_state` 仍保留，但职责已降级为细粒度兼容补充。
3. 本轮没有放松任何现有保守过滤语义：`BEAR_PERSISTING` 仍屏蔽，`BEAR_FORMING` 仍由开关控制。

## 未完成项 / 风险

1. A4-5 仍未使用生命周期三轴读数；这属于下一阶段，不在本卡范围内。
2. `MalfContext` 合同本身仍带旧字段，这是全仓兼容桥的一部分，本卡未触碰。
3. 相关设计文档存在既有 markdownlint 排版警告，本卡未做无关格式清扫。
