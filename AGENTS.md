# AGENTS.md — Lifespan-Quant

## 系统定位

`Lifespan-Quant` 是面向中国 A 股的市场平均寿命量化系统（第二代重构版）。

- 个人项目，单开发者
- 执行模型：增量交付，每步产出可独立验证的交付物
- 文档服务实现，不追求文档完美

## 主线铁律

1. **主线链路**：`data → malf → structure(filter) → alpha/pas → position → trade → system`
2. **执行语义**：`signal_date=T`，`execute_date=T+1`，成交价 = `T+1` 开盘价
3. **模块间只传结果合同**，不传内部中间特征（`dataclass` / `pydantic`）
4. **路径/密钥禁止硬编码**，统一经 `core/paths.py` 注入或环境变量
5. **structure 模块是新增核心**，统一结构位语言后才能扩充 trigger 语义
6. **filter 模块是准入门槛**，先通过不利条件过滤才进入 trigger 检测
7. **5 个 PAS trigger 代码状态**：BOF/PB 已验证可用，BPB 拒绝主线，TST/CPB 待独立验证

## 代码规范

- 代码注释使用**中文**
- 函数/方法命名：`snake_case`
- 类命名：`PascalCase`
- 模块包名：`lq`（短名，Lifespan-Quant）

## 目录纪律（强制）

| 目录 | 用途 |
|------|------|
| `G:\Lifespan-Quant` | 代码、文档、测试、治理 — 不放运行时缓存或临时 DB |
| `G:\Lifespan-data` | 正式数据库与数据产物 |
| `G:\Lifespan-temp` | 临时文件、pytest、中间产物 |
| `G:\Lifespan-report` | 报表、图表、正式导出 |
| `G:\Lifespan-Validated` | 跨版本验证资产快照 |

## 数据层（5 个 DuckDB 数据库）

| DB | 路径 | 内容 |
|----|------|------|
| `raw_market` | `Lifespan-data/raw/` | baostock 原始日线 |
| `market_base` | `Lifespan-data/base/` | 复权价、均线、量比 |
| `research_lab` | `Lifespan-data/research/` | PAS 信号、选中 trace |
| `malf` | `Lifespan-data/malf/` | MALF 三层主轴输出 |
| `trade_runtime` | `Lifespan-data/trade/` | 执行合同、回测结果 |

## 测试目录规范

```
tests/
  unit/<module>/     单元测试
  integration/<module>/  集成测试
  patches/<module>/  回归/补丁测试
```

## 开发命令

```bash
python -m pip install -e .[dev]
pytest tests/unit -q
python scripts/data/bootstrap_storage.py
```

## 仓库远端

- `origin`: `https://github.com/everything-is-simple/market_average_Lifespan-Quant`
- 推送策略：同时推送到所有活跃远端
