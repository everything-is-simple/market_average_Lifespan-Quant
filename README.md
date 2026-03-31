# Lifespan-Quant

`Lifespan-Quant` 是基于**市场平均寿命框架（MALF）**重构的本地优先 A 股研究执行系统。

它在继承 MarketLifespan-Quant 主线能力的基础上，吸收了以下优先级 A 研究方向：

1. **结构位统一合同**（A1）— 水平关键位、波段高低点、测试/回踩点、突破后新支撑/阻力
2. **突破家族语义**（A2）— 有效突破 / 假突破 / 测试 / 回踩确认语言正式化
3. **二次入场 / 第一 PB**（A3）— 追踪 PB 序号，第一 PB 假说进入正式验证轨道
4. **不利市场条件过滤器**（A4）— "不做"语言冻结成统一过滤合同
5. **交易管理模板**（A5）— 入场后演化生命周期正式化

## 模块职责

| 模块 | 职责 |
|------|------|
| `core` | 公共类型、路径合同、ID、跨模块枚举 |
| `data` | 市场数据采集（baostock）、清洗、落盘、增量更新 |
| `malf` | 市场平均寿命框架：`monthly_state_8 / weekly_flow_relation / pas_context` |
| `structure` | 统一结构位合同：关键位识别、突破分类（新增） |
| `alpha/pas` | 五 trigger：`BOF / BPB / PB / TST / CPB` + 16 格验证框架 + 第一 PB 追踪 |
| `filter` | 不利市场条件过滤器（新增） |
| `position` | 1R 风险单位、头寸规模、退出合同 |
| `trade` | 交易管理模板、执行 runtime（新增模板层） |
| `system` | 编排、回测、治理检查 |

## 外部目录口径（五目录纪律）

| 目录 | 用途 |
|------|------|
| `G:\Lifespan-Quant` | 代码、文档、测试、治理 |
| `G:\Lifespan-data` | 正式数据库（`raw_market / market_base / research_lab / malf / trade_runtime`） |
| `G:\Lifespan-temp` | working DB、缓存、试跑产物 |
| `G:\Lifespan-report` | 报表、图表、正式导出 |
| `G:\Lifespan-Validated` | 跨版本验证资产快照 |

## 当前主线

```
data → malf → structure(filter) → alpha/pas → position → trade → system
```

执行语义：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价。

## 快速开始

```bash
python -m pip install -e .[dev]
pytest tests/unit -q
python scripts/data/bootstrap_storage.py
```

## 参考来源

- `G:\MarketLifespan-Quant\docs\04-reference\` 下系统参考总图
- MarketLifespan-Quant（父系统）验证能力与 BOF/PB 三年数据
