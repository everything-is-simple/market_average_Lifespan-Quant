# 执行闭环区 / 03-execution

## 用途

执行卡、证据、记录、结论。每一刀实现都必须在这里留下闭环痕迹。

## 闭环四件套

每个执行任务必须包含：
1. **card** — 任务卡（目标、前置、验收标准）
2. **evidence** — 执行证据（命令、参数、输出摘要）
3. **record** — 执行记录（实际发生了什么）
4. **conclusion** — 结论（是否达成目标，下一步是什么）

## 当前状态

当前系统处于**初始构建阶段（v0.1.0）**。

已完成：
- 系统架构冻结（`docs/01-design/`）
- 核心模块实现（`src/lq/`：core/data/malf/structure/alpha/filter/position/trade/system）
- 基础单测覆盖（`tests/unit/`）
- 首次提交至 GitHub
- `core` 模块补全：`checkpoint.py`（JsonCheckpointStore）+ `resumable.py`（6 个续跑工具），203 passed（2026-04-02）
- 全模块 `__init__.py` 填充对齐（core/data/malf/alpha.pas/position，2026-04-02）
- 核心设计文档同步更新（`docs/01-design/modules/core/`，2026-04-02）
- **七库全持久化架构审查（2026-04-05）**：确认七库全部必要；修复 `paths.py` 缺失 `structure`/`filter` 两路径；修复 `00-system-overview` 模块职责表矛盾；落盘空间换时间设计决策备忘（§6.1）、批处理内存控制合同（`01-system-architecture` §5）、`config_hash` 机制规格（`02-spec` §3.1/3.2）

已开卡：
- `001` — **data 全链路 bootstrap**（txt 全量灌入 + 路径修正，2026-04-04）→ `data/card-001-*`

待开卡（持久化主线实施，按依赖顺序）：
- `011` — **malf 六层流水线持久化 bootstrap**（schema + batch runner + config_hash + checkpoint）→ `malf/card-011-*`；所有下游依赖，优先级 P0
- `012` — **structure 持久化层 bootstrap**（schema + batch runner + config_hash + checkpoint）→ `structure/card-012-*`；依赖 011
- `013` — **filter 持久化层 bootstrap**（schema + batch runner + config_hash + checkpoint）→ `filter/card-013-*`；依赖 011 + 012
- `014` — **research_lab 持久化 bootstrap**（alpha/pas + position；config_hash trigger 参数域 + batch runner）→ `alpha/card-014-*`；依赖 013
- `015` — **trade_runtime 持久化 bootstrap**（TradeManager 批量回测 + config_hash + checkpoint）→ `trade/card-015-*`；依赖 014

待开卡（验证层，待 011-015 完成后启动）：
- `002` — malf 三层主轴端到端验证（月线、周线、表面标签）
- `003` — BOF 在 BULL_MAINSTREAM 格的独立三年验证
- `004` — structure 模块与 BOF 联合验证（结构位 + BOF 信号）
- `005` — filter 不利条件过滤器效果评估
- `006` — TST 独立正式验证卡
- `007` — CPB 语义收敛 + 独立正式验证卡
- `008` — 第一 PB 假说独立验证卡（A3）
- `009` — L2 后复权抽样验证（待 L1 灌入后）
- `010` — 单测补全：test_adjust_factor.py
