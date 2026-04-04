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

已开卡：
- `001` — **data 全链路 bootstrap**（txt 全量灌入 + 路径修正，2026-04-04）→ `data/card-001-*`

待开卡：
- `002` — malf 三层主轴端到端验证（月线、周线、表面标签）
- `003` — BOF 在 BULL_MAINSTREAM 格的独立三年验证
- `004` — structure 模块与 BOF 联合验证（结构位 + BOF 信号）
- `005` — filter 不利条件过滤器效果评估
- `006` — TST 独立正式验证卡
- `007` — CPB 语义收敛 + 独立正式验证卡
- `008` — 第一 PB 假说独立验证卡（A3）
- `009` — L2 后复权抽样验证（待 L1 灌入后）
- `010` — 单测补全：test_adjust_factor.py
