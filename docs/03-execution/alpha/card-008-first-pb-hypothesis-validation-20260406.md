# CARD-008 第一 PB 假说独立验证卡（A3）/ 2026-04-06

## 目标

独立验证"第一 PB"假说：在 BOF 确认后的第一次 PB（Pullback）信号质量显著优于后续 PB：
1. 使用 `pb_sequence_number` 字段区分第一 PB 与后续 PB
2. 确认"第一 PB 胜率更高"的假说是否成立
3. 为 PB trigger 的 CONDITIONAL 定位提供量化依据

## 前置条件

- [ ] card-014 完成：`research_lab.duckdb` 已填充（PB 信号 + `pb_sequence_number` 可读）
- [ ] card-015 完成：`trade_runtime.duckdb` 已填充

## 执行步骤

1. 从 `research_lab` 筛选 `pattern=PB` 的全部信号，按 `pb_sequence_number` 分组
2. 从 `trade_runtime` 匹配交易记录
3. 分组统计：
   - A 组：`pb_sequence_number = 1`（第一 PB）
   - B 组：`pb_sequence_number >= 2`（后续 PB）
4. 对比两组：胜率、平均 R 倍数、净收益
5. 按表面标签拆分，看第一 PB 在哪些格子最强
6. 与 v0.01 PB 数据对比（v0.01 PB 保留段仅 15 万，量大质弱）

## 验收标准

1. A 组胜率 > B 组胜率（差距 ≥ 5 个百分点方有实质意义）
2. A 组平均 R 倍数 > B 组
3. 如果假说成立 → 建议：PB trigger 只保留 `pb_sequence_number = 1`
4. 如果假说不成立 → 记录为"第一 PB 无显著优势"，PB 维持 CONDITIONAL 全保留

## 产出物

- evidence（分组对比表 + 表面标签拆分）
- record + conclusion（含假说最终判定）
