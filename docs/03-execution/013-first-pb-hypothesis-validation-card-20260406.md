# CARD-013 第一 PB 假说独立验证卡（A3）/ 2026-04-06

**状态**: `pending-validation`
**类型**: `alpha / validation / pb-hypothesis`
**模块**: `alpha/pas`, `trade`

## 1. 定位

这张卡只解决一件事：

验证“`BOF` 确认后的第一笔 `PB` 是否显著优于后续 `PB`”这一假说，并为 `PB` 维持或收缩 `CONDITIONAL` 定位提供量化依据。

## 2. 固定因素

1. `PB` 当前定位是 `CONDITIONAL`，本卡不是为了预设其成立，而是为了确认它应如何保留。
2. 本卡必须依赖正式可读的序号字段，例如 `pb_sequence_number`；如果当前正式结果合同中没有该字段，本卡不得伪关闭。
3. 背景拆分若有需要，只允许使用当前正式执行合同字段，不再以旧 `surface_label` 作为正式主轴。
4. 本卡不直接改 `PB` detector、不改 `position` sizing、不改 `trade` 执行模板。

## 3. 输出要求

1. 将 `PB` 信号至少分为两组：`pb_sequence_number = 1` 与 `pb_sequence_number >= 2`。
2. 对两组分别统计样本数、胜率、平均 `R`、净 `R`、年度表现。
3. 如果样本足够，补充按正式背景合同的分组比较，判断“第一 `PB` 优势”是否只在特定背景下成立。
4. 结论必须明确回答：是否只保留第一 `PB`，还是维持全部 `PB` 作为 `CONDITIONAL`。

## 4. 本卡回答的问题

1. 第一笔 `PB` 是否显著优于后续 `PB`？
2. 这种优势是稳定优势，还是仅在个别背景或个别年份成立？
3. `PB` 的保留策略应该是“只保留第一笔”还是“全部保留但降权观察”？

## 5. 非目标

1. 不在本卡重新定义 `PB` 形态语义。
2. 不在本卡直接升级或下线 `PB`。
3. 不在本卡验证 `BOF / TST / CPB`。

## 6. 证据目标

1. 两组对比表：样本数、胜率、平均 `R`、净 `R`。
2. 年度拆分表：第一 `PB` 与后续 `PB` 的逐年表现。
3. 若可行，再补一组正式背景拆分表。
4. record / conclusion 中明确给出“假说成立 / 部分成立 / 不成立”的判断。

## 7. 关闭条件

1. `pb_sequence_number` 或等价字段已被确认可读且样本口径可复述。
2. evidence / record / conclusion 四件套补齐。
3. 结论能明确回答 `PB` 的保留边界，而不是只给描述性比较。

## 8. 闭环文件

1. 证据：`docs/03-execution/evidence/013-first-pb-hypothesis-validation-evidence-20260408.md`
2. 记录：`docs/03-execution/records/013-first-pb-hypothesis-validation-record-20260408.md`
3. 结论：待真实执行关闭时按实际日期创建 `013-first-pb-hypothesis-validation-conclusion-YYYYMMDD.md`
