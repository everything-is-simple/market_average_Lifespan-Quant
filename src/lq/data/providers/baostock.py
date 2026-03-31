"""BaoStock 第二校准源 provider 边界与代码格式转换。

角色定位（继承父系统 139 号卡冻结口径）：
  - second calibration source（第二校准源）
  - fallback provider（保底补洞）
  - 禁止替代 tdx_local 主源
  - 禁止未经审计直接反写正式五库

双源校准五类事件规则表（父系统 138/139 号卡冻结，不可随意修改）：
  category 1 — provisional_dual_source_comparable_with_mild_drift_watch
  category 2 — conditional_comparable_with_mild_drift_watch
  category 3 — stable_baostock_boundary_use_tushare_fill
  category 5 — boundary_fill_with_mild_drift_watch
  category 9 — holdout_pending_factor_path_resolution

当前仅覆盖以下接口：
  query_adjust_factor   — 复权因子（用于 cross-source diff）
  query_dividend_data   — 分红数据（用于 cross-source diff）

后续若要做全量 batch audit 或阈值冻结，必须另开独立执行卡，不允许在此文件内直接越级扩展。
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# BaoStock 职责边界声明
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BaoStockProviderBoundary:
    """BaoStock 在本系统中的职责边界说明对象。"""

    provider_name: str = "baostock"
    role: str = "second_calibration_source"          # 第二校准源，不是主源
    responsibilities: tuple[str, ...] = (
        "保底补洞",
        "缺口修复",
        "复权因子交叉校验",
        "dividend_data 对比",
    )
    calibration_scope: tuple[str, ...] = (
        "adjust_factor",     # query_adjust_factor 接口
        "dividend_data",     # query_dividend_data 接口
    )
    forbidden_roles: tuple[str, ...] = (
        "替代 tdx_local 主源",
        "直接充当默认日更主入口",
        "未经审计直接反写正式五库",
        "升格为 Tushare 同等级主校准源（需另开独立卡）",
    )


def get_baostock_boundary() -> BaoStockProviderBoundary:
    """返回 BaoStock 的正式边界声明。"""
    return BaoStockProviderBoundary()


# ---------------------------------------------------------------------------
# 证券代码格式转换（本地格式 ↔ BaoStock 格式）
# ---------------------------------------------------------------------------

def to_baostock_code(code: str) -> str:
    """把本地 `600000.SH` 格式转换为 BaoStock 习惯的 `sh.600000`。

    支持输入格式：
      "600000.SH" / "600000.sh" → "sh.600000"
      "sh.600000"（已经是 BaoStock 格式）→ 直接返回归一化结果
    """
    normalized = code.strip().lower()
    if "." not in normalized:
        raise ValueError(f"无法识别的证券代码格式: {code!r}")
    left, right = normalized.split(".", maxsplit=1)

    # 已经是 BaoStock 格式：sh.600000
    if len(left) == 2 and len(right) == 6:
        if left not in {"sh", "sz", "bj"}:
            raise ValueError(f"不支持的交易所前缀: {code!r}")
        return f"{left}.{right}"

    # 本地格式：600000.SH
    if len(left) == 6 and len(right) == 2:
        if right not in {"sh", "sz", "bj"}:
            raise ValueError(f"不支持的交易所后缀: {code!r}")
        return f"{right}.{left}"

    raise ValueError(f"无法识别的证券代码格式: {code!r}")


def from_baostock_code(code: str) -> str:
    """把 BaoStock 代码 `sh.600000` 转回本地格式 `600000.SH`。"""
    normalized = to_baostock_code(code)
    market, symbol = normalized.split(".", maxsplit=1)
    return f"{symbol}.{market.upper()}"
