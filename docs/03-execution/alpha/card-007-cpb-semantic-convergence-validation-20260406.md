# CARD-007 CPB 语义收敛 + 独立正式验证卡 / 2026-04-06

## 目标

对 CPB（Count Price Bar）trigger 做语义收敛分析和独立验证：
1. 明确 CPB 的当前状态（REJECTED）是否仍然成立
2. 如果 v0.1 新增的 structure/filter 能改善 CPB 质量，评估是否有必要重新考虑

## 前置条件

- [ ] card-014 完成：`research_lab.duckdb` 已填充（CPB 信号可读，如果 enabled）
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充

## 执行步骤

1. **语义收敛**：审查 CPB 的 detector 逻辑，明确 CPB 与 BOF 的信号重叠度
2. 从 `research_lab` 筛选 `pattern=CPB`（需要在 card-014 时临时启用 CPB）
3. 统计 CPB 与 BOF 的信号重叠率（同一 code+date 出现两个 trigger）
4. 独立统计 CPB 的胜率、R 倍数、净收益
5. 对比"CPB 独有信号"（不与 BOF 重叠的部分）的表现
6. 与 v0.01 CPB 拒绝结论对照

## 验收标准

1. 如果 CPB 独有信号净收益 > 0 且胜率 > 45% → 建议升级为 CONDITIONAL
2. 如果 CPB 独有信号净收益 ≤ 0 → 维持 REJECTED，记录为正式确认
3. 无论结论如何，必须给出量化依据

## 产出物

- evidence（重叠分析 + 独有信号统计表）
- record + conclusion（含最终状态建议）
