# Lifespan-Quant 执行纪律

## 总则

在 `H:\Lifespan-Quant` 内做正式工作时使用本 skill。
不要把这个仓库当成普通代码仓库，而要把它当成受治理约束的系统；
默认遵守仓库既有执行闭环，而不是临时想到什么改什么。

需要确认阅读顺序时，先看 `docs/03-execution/` 下的 conclusion 目录索引。

## 硬规则

改任何正式内容前都先应用下面这些规则：

1. 先读现行 `conclusion`，再读执行目录纪律，再读对应 `design` 和 `spec`。
2. 严守五目录边界：
   `Quant` 放仓库本体，`data` 放正式数据库，`temp` 放中间运行产物，`report` 放人读报告，`Validated` 放长期验证资产快照。
3. 严守冻结依赖矩阵：
   `data → core`，`trade → core, data`，`alpha → core, data`，`malf → core, data`。
4. 正式文档默认中文；正式 Python 文件必须带必要的中文注释。
5. 缺任意一件 `card / evidence / record / conclusion`，默认算未收口。
6. 如果任务涉及正式回测、正式 runner、三年窗口或全市场批处理，卡面里必须先写"性能与库复用前置检查"。

## 执行顺序

除非用户明确要求"只读分析"，否则默认按这个顺序推进：

1. 判断任务影响的模块，以及它是否改变行为、schema、runner、正式输出或治理文档。
2. 先读现行 `conclusion`，再读相关 `docs/01-design/...` 和 `docs/02-spec/...`。
3. 判断是否必须先开正式卡。
4. 只在允许的模块边界和数据边界内实现。
5. 跑测试或执行命令，形成可复核证据。
6. 先写 `evidence`，再写 `record`，再写 `conclusion`。
7. 回填索引、目录和账本，保证新状态能从执行入口文档找到。

## 必须先开卡的场景

遇到下面这些场景，必须停下来先走开卡流程：

1. 新增或改变正式 runner 行为。
2. 改 schema、合同、路径纪律或模块边界。
3. 新增正式输出表、正式报告、benchmark 或执行主流程。
4. 把研究逻辑往正式主线迁移。
5. 在 `docs/03-execution` 里新开、重开或关闭一条执行线。

纯错字修正、纯排版调整、或用户明确说"只改这一行"，可以不开卡；但即使这样，也不能与现行 conclusion 冲突。

## 禁止靠代码收口

如果你正准备做下面这些事，必须停下来纠正流程：

1. 没读当前 `conclusion` 就改代码。
2. 没开卡就增加正式行为。
3. 没有 evidence 或 record 就宣称完成。
4. 新卡已落地，但索引或目录里看不见。
5. 把临时数据库、缓存或 benchmark 产物堆在仓库根目录。
6. 让一个模块越权写另一个模块拥有的正式输出表。

## 默认交付集合

实现类任务默认收口集合是：

1. 代码或正式文档变更
2. 可复述的命令、测试或运行证据
3. `record`
4. `conclusion`
5. 索引、目录、账本回填

把 `docs/03-execution/` 下的模板包当作最低结构要求，而不是"可选参考"。

## 常用命令

```bash
# 运行全部单元测试
pytest tests/unit -q

# 运行指定模块测试
pytest tests/unit/data -q

# 运行开发治理检查
python scripts/system/check_development_governance.py

# 对全仓所有文件跑 pre-commit
pre-commit run --all-files

# 安装依赖（含开发依赖）
python -m pip install -e .[dev]
```
