# CARD-004 structure 模块与 BOF 联合验证（结构位 + BOF 信号）/ 2026-04-06

## 目标

验证 structure 模块输出的支撑/阻力/突破分类对 BOF 信号质量的提升效果：
1. 对比"有结构位过滤"与"无结构位过滤"两组 BOF 信号的胜率差异
2. 确认 `StructureSnapshot` 的关键字段（`has_clear_structure`、`available_space_pct`）对 BOF 质量有正向区分力

## 前置条件

- [ ] card-012 完成：`structure.duckdb` 已填充
- [ ] card-014 完成：`research_lab.duckdb` 已填充（BOF 信号可读）
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充

## 执行步骤

1. 从 `research_lab` 筛选 2020-2023 年全部 BOF 信号
2. 用 `structure.duckdb` 关联每个信号日的 `StructureSnapshot`
3. 分组统计：
   - A 组：`has_clear_structure=True AND available_space_pct > 5%`
   - B 组：`has_clear_structure=False OR available_space_pct <= 5%`
4. 对比两组的胜率、平均 R 倍数、净收益
5. 评估 `available_space_pct` 的最优阈值（3%/5%/8% 三档）

## 验收标准

1. A 组胜率 > B 组胜率（差距 ≥ 5 个百分点方有实质意义）
2. A 组平均 R 倍数 > B 组
3. 最优阈值有清晰拐点或单调趋势
4. 若无区分力，记录为"structure 对 BOF 无增益"，不强行美化

## 产出物

- evidence（分组对比表 + 阈值敏感性图）
- record + conclusion
