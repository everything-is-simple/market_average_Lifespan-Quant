"""Lifespan-Quant 文件系统与数据库路径合同。

路径读取顺序：
1. 环境变量覆盖（LQ_DATA_ROOT 等）
2. 默认值：仓库根目录同级目录命名约定
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# 内部常量：目录名称约定（可被环境变量覆盖）
# ---------------------------------------------------------------------------
_DATA_DIRNAME = "Lifespan-Quant-data"
_TEMP_DIRNAME = "Lifespan-temp"
_REPORT_DIRNAME = "Lifespan-Quant-report"
_VALIDATED_DIRNAME = "Lifespan-Quant-Validated"

# 通达信本地目录默认路径（可被 TDX_ROOT 环境变量覆盖）
_DEFAULT_TDX_ROOT = Path(r"H:\new_tdx64")

# 通达信离线导出数据目录（可被 TDX_OFFLINE_DATA_ROOT 环境变量覆盖）
_DEFAULT_TDX_OFFLINE_DATA_ROOT = Path(r"H:\tdx_offline_Data")


def discover_repo_root(start: Path | None = None) -> Path:
    """从当前路径向上查找仓库根目录（有 pyproject.toml 的目录）。"""
    current = (start or Path(__file__)).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    raise FileNotFoundError("无法从当前路径向上定位仓库根目录。")


@dataclass(frozen=True)
class DatabasePaths:
    """正式五数据库路径合同。"""

    raw_market: Path       # L1 原始日线（mootdx）+ xdxr（gbbq）
    market_base: Path      # L2 复权价、均线、量比
    research_lab: Path     # L3 PAS 信号、选中 trace
    malf: Path             # L3 MALF 三层主轴输出
    trade_runtime: Path    # L4 执行合同、回测结果

    def as_dict(self) -> dict[str, Path]:
        return {
            "raw_market": self.raw_market,
            "market_base": self.market_base,
            "research_lab": self.research_lab,
            "malf": self.malf,
            "trade_runtime": self.trade_runtime,
        }


@dataclass(frozen=True)
class WorkspaceRoots:
    """系统五目录根路径。"""

    repo_root: Path
    data_root: Path
    temp_root: Path
    report_root: Path
    validated_root: Path

    @property
    def databases(self) -> DatabasePaths:
        """返回正式五数据库路径（不自动创建目录）。"""
        return DatabasePaths(
            raw_market=self.data_root / "raw" / "raw_market.duckdb",
            market_base=self.data_root / "base" / "market_base.duckdb",
            research_lab=self.data_root / "research" / "research_lab.duckdb",
            malf=self.data_root / "malf" / "malf.duckdb",
            trade_runtime=self.data_root / "trade" / "trade_runtime.duckdb",
        )

    def ensure_directories(self) -> None:
        """确保所有目录（含数据库父目录）存在，若不存在则创建。"""
        for root in (
            self.repo_root,
            self.data_root,
            self.temp_root,
            self.report_root,
            self.validated_root,
        ):
            root.mkdir(parents=True, exist_ok=True)
        # 数据库文件由 bootstrap 创建，但目录合同应在 settings 解析后立即存在
        for db_path in self.databases.as_dict().values():
            db_path.parent.mkdir(parents=True, exist_ok=True)


def _default_sibling_root(repo_root: Path, dirname: str) -> Path:
    """仓库同级目录作为默认外部目录。"""
    return repo_root.parent / dirname


def tdx_root() -> Path:
    """解析通达信本地目录路径。优先读 TDX_ROOT 环境变量，否则用默认值。"""
    return Path(os.getenv("TDX_ROOT", str(_DEFAULT_TDX_ROOT))).resolve()


def tdx_offline_data_root() -> Path:
    """解析通达信离线导出数据目录。优先读 TDX_OFFLINE_DATA_ROOT 环境变量。"""
    return Path(os.getenv("TDX_OFFLINE_DATA_ROOT", str(_DEFAULT_TDX_OFFLINE_DATA_ROOT))).resolve()


def tushare_token_path() -> Path | None:
    """解析 tushare token 配置文件路径。读 TUSHARE_TOKEN_PATH 环境变量，未设置时返回 None。"""
    raw = os.getenv("TUSHARE_TOKEN_PATH")
    return Path(raw).resolve() if raw else None


def default_settings(repo_root: Path | None = None) -> WorkspaceRoots:
    """解析正式工作区根目录，允许环境变量覆盖默认值。

    环境变量：
    - LQ_REPO_ROOT       覆盖仓库根目录
    - LQ_DATA_ROOT       覆盖数据目录
    - LQ_TEMP_ROOT       覆盖临时目录
    - LQ_REPORT_ROOT     覆盖报告目录
    - LQ_VALIDATED_ROOT  覆盖验证资产目录
    - TDX_ROOT               通达信本地目录（由 tdx_root() 独立解析）
    - TDX_OFFLINE_DATA_ROOT   通达信离线导出数据目录（由 tdx_offline_data_root() 独立解析）
    - TUSHARE_TOKEN_PATH      tushare token 配置文件路径（由 tushare_token_path() 独立解析）
    """
    resolved_repo = Path(
        os.getenv("LQ_REPO_ROOT", str(repo_root or discover_repo_root()))
    ).resolve()

    data_root = Path(
        os.getenv("LQ_DATA_ROOT", str(_default_sibling_root(resolved_repo, _DATA_DIRNAME)))
    ).resolve()
    temp_root = Path(
        os.getenv("LQ_TEMP_ROOT", str(_default_sibling_root(resolved_repo, _TEMP_DIRNAME)))
    ).resolve()
    report_root = Path(
        os.getenv("LQ_REPORT_ROOT", str(_default_sibling_root(resolved_repo, _REPORT_DIRNAME)))
    ).resolve()
    validated_root = Path(
        os.getenv(
            "LQ_VALIDATED_ROOT",
            str(_default_sibling_root(resolved_repo, _VALIDATED_DIRNAME)),
        )
    ).resolve()

    return WorkspaceRoots(
        repo_root=resolved_repo,
        data_root=data_root,
        temp_root=temp_root,
        report_root=report_root,
        validated_root=validated_root,
    )
