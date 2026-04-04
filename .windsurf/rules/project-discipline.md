---
trigger: always_on
---

# Lifespan-Quant 项目开发纪律

## 改代码前必须先读文档

改任何正式模块前，按下列顺序阅读，**不得跳过**：

1. `docs/03-execution/` 下的 conclusion 与目录索引（当前状态）
2. 对应模块的 `docs/01-design/modules/<module>/`（章程与设计）
3. 对应模块的 `docs/02-spec/modules/<module>/`（规格）

只有排障、纯文字修正、或用户明确说"只改这一行"，才可以跳过上述步骤。

## 五目录纪律（强制）

| 目录 | 用途 | 禁止放入 |
|---|---|---|
| `H:\Lifespan-Quant` | 代码、文档、脚本、治理 | 数据库、日志、临时文件、缓存 |
| `H:\Lifespan-Quant-data` | 正式七数据库（全持久化 DuckDB） | 代码 |
| `H:\Lifespan-temp` | 临时文件、pytest 产物、中间产物 | 正式代码或文档 |
| `H:\Lifespan-Quant-report` | 报告、图表、正式导出 | 代码 |
| `H:\Lifespan-Quant-Validated` | 跨版本验证资产快照 | 代码 |

## 模块依赖矩阵（冻结，禁止反向）

```
core（基础层，所有模块依赖）
data      → core
malf      → core, data
structure → core
filter    → core, malf
alpha     → core, data, malf, structure, filter
position  → core, data, alpha
trade     → core, data, position
system    → core, data, malf, alpha, position, trade
```

禁止反向依赖：下游模块不得 import 上游模块的内部实现。

## 代码规范

- 注释和文档：**中文**
- 函数/方法/模块：`snake_case`
- 类名：`PascalCase`
- 单文件硬上限：**1000 行**；目标上限：**800 行**
- 模块间只传结果契约（dataclass / pydantic），禁止传内部中间特征

## 执行语义

- `signal_date = T`，`execute_date = T+1`，成交价 = `T+1` 开盘价

## 数据源口径

- **主线（离线）**：mootdx 读通达信本地 `.day` 文件 + gbbq 除权除息
- **辅助（在线）**：tushare HTTP API，仅用于复权因子审计，不参与主线 L2 构建
- `TDX_ROOT` 环境变量指定通达信目录；`TUSHARE_TOKEN_PATH` 指定 token 文件路径

## 任务闭环规则

涉及正式模块行为、schema、runner、输出合同或治理文档的变更，必须包含：

1. **card**（任务卡，说明意图与边界）
2. **evidence**（可复述的命令、参数、测试结果）
3. **record**（本次执行过程与遇到的问题）
4. **conclusion**（结论，可被后续任务直接引用）

缺任意一件，不得视为完成。纯文字修正或排障可免。

## 七库全持久化纪律

**核心原则**：历史一旦发生就是永恒的瞬间——绝不重算。磁盘空间换内存，小批量断点续传。

- 七个 DuckDB 全部持久化：raw_market / market_base / malf / structure / filter / research_lab / trade_runtime
- 每行带 `config_hash`，参数冻结则跳过已有数据；参数变更则 selective rebuild
- 按日期区间分批处理，checkpoint 标记完成，中断后从断点恢复
- 禁止把任何库改为内存库或每次重建

## 禁止行为

- 没读当前 conclusion 就改代码
- 没开卡就增加正式行为
- 把临时数据库、缓存或 benchmark 产物堆在仓库根目录
- 让一个模块越权写另一个模块拥有的正式输出表
