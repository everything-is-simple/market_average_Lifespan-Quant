# core 模块 — paths 设计 / 2026-04-01

## 1. 设计目标

本文定义 `core/paths.py` 的完整设计，包括：

1. 两层路径合同（WorkspaceRoots + DatabasePaths）的字段与职责
2. 五目录协作规范与默认命名约定
3. 七数据库路径规范（全持久化）
4. 环境变量覆盖机制（完整清单）
5. 特殊数据源路径（TDX / Tushare）
6. 与父/爷爷系统的对比与取舍

---

## 2. 两层路径合同

### 2.1 WorkspaceRoots — 系统五目录根路径

```python
@dataclass(frozen=True)
class WorkspaceRoots:
    repo_root:      Path   # 代码仓库根目录
    data_root:      Path   # 正式数据与数据库
    temp_root:      Path   # 临时文件、pytest 产物、benchmark 中间产物
    report_root:    Path   # 人读报告、图表、正式导出
    validated_root: Path   # 跨版本验证资产快照（本系统新增第5根）
```

与父系统（MarketLifespan）的差异：父系统只有 4 个根（无 `validated_root`），本系统新增第 5 个。`validated_root` 用于存放已经验证的长期资产快照（如 PAS 三年验证、MALF 冻结快照），不混入 `temp_root` 的临时产物。

**`ensure_directories()` 方法**（已实现）：一键创建所有根目录和数据库父目录，适合在 bootstrap 和 runner 开始时调用。

### 2.2 DatabasePaths — 七数据库路径合同（全持久化）

```python
@dataclass(frozen=True)
class DatabasePaths:
    raw_market:    Path   # L1 原始日线 + gbbq（由 data 模块独占写）
    market_base:   Path   # L2 复权价、均线、量比（由 data 模块独占写）
    malf:          Path   # L3 MALF 三层主轴输出（由 malf 模块独占写）
    structure:     Path   # L3 结构位快照（由 structure 模块独占写）
    filter:        Path   # L3 不利条件结果（由 filter 模块独占写）
    research_lab:  Path   # L3 PAS 信号 + 仓位计划（由 alpha+position 独占写）
    trade_runtime: Path   # L4 交易记录 + 权益曲线（由 trade+system 写）
```

通过 `WorkspaceRoots.databases` 属性计算：

```python
@property
def databases(self) -> DatabasePaths:
    return DatabasePaths(
        raw_market    = self.data_root / "raw"       / "raw_market.duckdb",
        market_base   = self.data_root / "base"      / "market_base.duckdb",
        malf          = self.data_root / "malf"      / "malf.duckdb",
        structure     = self.data_root / "structure" / "structure.duckdb",
        filter        = self.data_root / "filter"    / "filter.duckdb",
        research_lab  = self.data_root / "research"  / "research_lab.duckdb",
        trade_runtime = self.data_root / "trade"     / "trade_runtime.duckdb",
    )
```

---

## 3. 五目录协作规范

### 3.1 目录职责边界（强制）

| 目录根 | 环境变量 | 默认名称 | 存放内容 | 禁止存放 |
|---|---|---|---|---|
| `repo_root` | LQ_REPO_ROOT | `Lifespan-Quant` | 代码、文档、测试、脚本 | 数据库、日志、缓存 |
| `data_root` | LQ_DATA_ROOT | `Lifespan-data` | 正式数据库、正式数据产物 | 代码、临时文件 |
| `temp_root` | LQ_TEMP_ROOT | `Lifespan-temp` | 临时产物、pytest、benchmark | 正式代码/数据库 |
| `report_root` | LQ_REPORT_ROOT | `Lifespan-report` | 人读报告、图表、导出物 | 代码 |
| `validated_root` | LQ_VALIDATED_ROOT | `Lifespan-Validated` | 长期验证资产快照 | 普通临时产物 |

### 3.2 默认目录位置规则

默认值是**仓库同级目录**（与 repo_root 同一 parent 下）：

```
parent/
  Lifespan-Quant/    ← repo_root（代码仓库）
  Lifespan-data/     ← data_root（正式数据）
  Lifespan-temp/     ← temp_root（临时产物）
  Lifespan-report/   ← report_root（报告）
  Lifespan-Validated/← validated_root（验证快照）
```

在 Windows 实际环境（本机）：

```
H:\Lifespan-Quant\           ← repo_root
H:\Lifespan-Quant-data\      ← data_root
H:\Lifespan-temp\            ← temp_root
H:\Lifespan-Quant-report\    ← report_root
H:\Lifespan-Quant-Validated\ ← validated_root
```

---

## 4. 五数据库路径规范

### 4.1 分层归属与写权规则

| 数据库 | 层级 | Owner 模块 | 允许读取的模块 |
|---|---|---|---|
| raw_market.duckdb | L1 | data | data |
| market_base.duckdb | L2 | data | data, malf, alpha, position, trade, system |
| research_lab.duckdb | L3 | alpha | alpha, position, trade（bridge 白名单内） |
| malf.duckdb | L3 | malf | malf, alpha, system |
| trade_runtime.duckdb | L4 | trade + system | trade, system, report（只读） |

**写权独占原则**：每个数据库只有 owner 模块可写，其他模块只能通过 owner 提供的 Python 接口读取，禁止跨模块直接写入。

### 4.2 数据库文件实际路径

```
H:\Lifespan-Quant-data\raw\raw_market.duckdb
H:\Lifespan-Quant-data\base\market_base.duckdb
H:\Lifespan-Quant-data\malf\malf.duckdb
H:\Lifespan-Quant-data\structure\structure.duckdb
H:\Lifespan-Quant-data\filter\filter.duckdb
H:\Lifespan-Quant-data\research\research_lab.duckdb
H:\Lifespan-Quant-data\trade\trade_runtime.duckdb
```

---

## 5. 环境变量覆盖机制

### 5.1 完整环境变量清单

| 环境变量 | 覆盖目标 | 示例值 |
|---|---|---|
| LQ_REPO_ROOT | WorkspaceRoots.repo_root | `H:\Lifespan-Quant` |
| LQ_DATA_ROOT | WorkspaceRoots.data_root | `H:\Lifespan-Quant-data` |
| LQ_TEMP_ROOT | WorkspaceRoots.temp_root | `H:\Lifespan-temp` |
| LQ_REPORT_ROOT | WorkspaceRoots.report_root | `H:\Lifespan-Quant-report` |
| LQ_VALIDATED_ROOT | WorkspaceRoots.validated_root | `H:\Lifespan-Quant-Validated` |
| TDX_ROOT | 通达信本地目录 | `D:\new-tdx\new-tdx` |
| TUSHARE_TOKEN_PATH | tushare token 配置文件路径 | `H:\keys\tushare_token.txt` |

### 5.2 解析优先级

```
1. 环境变量（运行时覆盖，最高优先级）
2. 仓库同级目录约定名称（默认值）
```

无 `.env` 文件依赖，无 pydantic 依赖。所有路径解析通过 `os.getenv()` 直接完成。

### 5.3 `default_settings()` 调用示例

```python
from lq.core.paths import default_settings

# 正常使用（使用默认约定目录）
ws = default_settings()
conn = duckdb.connect(ws.databases.market_base)

# CI / 测试环境（通过环境变量重定向到临时目录）
# 在 pytest conftest 中：os.environ["LQ_DATA_ROOT"] = str(tmp_path / "data")
ws = default_settings()
# → 数据库路径自动指向临时目录
```

---

## 6. 特殊数据源路径

### 6.1 tdx_root() — 通达信本地目录

```python
def tdx_root() -> Path:
    """解析通达信本地目录。优先 TDX_ROOT 环境变量，否则用 G:\new-tdx\new-tdx。"""
    return Path(os.getenv("TDX_ROOT", r"G:\new-tdx\new-tdx")).resolve()
```

**设计约束**：
- 返回 `Path` 对象（不自动验证存在性），调用方负责检查
- 默认值 `G:\new-tdx\new-tdx` 是本机通达信安装路径，生产机器必须通过 `TDX_ROOT` 覆盖
- `data` 模块通过 `mootdx` 库读取此目录下的 `.day` 文件

### 6.2 tushare_token_path() — Token 配置文件路径

```python
def tushare_token_path() -> Path | None:
    """解析 tushare token 配置文件路径。未设置时返回 None（表示不使用 tushare）。"""
    raw = os.getenv("TUSHARE_TOKEN_PATH")
    return Path(raw).resolve() if raw else None
```

**设计约束**：
- 只返回路径，不读取 token 内容（读取由 `data` 模块负责）
- 返回 `None` 表示 tushare 不可用（主线仅 mootdx，tushare 是备用审计渠道）
- **禁止**把 token 字符串放入环境变量或代码（只允许路径指向独立文件）

---

## 7. discover_repo_root() 实现规范

```python
def discover_repo_root(start: Path | None = None) -> Path:
    """从当前路径向上查找仓库根目录（有 pyproject.toml 的目录）。"""
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("无法从当前路径向上定位仓库根目录。")
```

**优于 `__file__.parents[N]`**：不依赖目录深度固定，在包安装模式（`pip install -e .`）和直接运行脚本两种场景下均可正确工作。

---

## 8. 与父/爷爷系统对比

| 特征 | EQ-gamma（爷爷） | MarketLifespan（父） | Lifespan-Quant（本系统） |
|---|---|---|---|
| 配置机制 | pydantic_settings（重） | 纯 env var（轻） | 纯 env var（继承父系统） |
| workspace 根数 | 3（data/temp/log） | 4（repo/data/temp/report） | **5**（+validated） |
| 数据库数量 | 1（单库分层） | 5（独立文件） | 5（独立文件，继承父系统） |
| TDX 路径 | 无（tushare 主线） | 无（tushare 主线） | **有**（mootdx 主线） |
| Tushare | Settings.tushare_token（直接存储） | 不在 core 层 | **只存路径**（安全升级） |
| validated 目录 | 无 | 无 | **有**（新增） |

---

## 9. 铁律

1. **路径不硬编码**：所有业务代码必须通过 `default_settings().databases.xxx` 获取路径
2. **`core/paths.py` 无第三方依赖**：只允许 `os / pathlib / dataclasses`，禁止 import duckdb 或 pandas
3. **数据库路径不跨越所有者边界**：业务模块只能直接使用自己 owner 的数据库，读他人数据库必须通过接口
4. **TDX_ROOT 生产环境必须显式设置**：默认值只适合本机开发，不适合任何部署场景
5. **Token 不进环境变量**：`TUSHARE_TOKEN_PATH` 指向文件，文件内容不得 commit 到仓库
