"""16 格正式验证框架 — PAS 信号在不同市场背景下的统计分析。

16 格 = 4 个表面标签 × BOF/BPB/PB/TST/CPB 组合。
正式框架中只保留 4 个表面标签：
    BULL_MAINSTREAM / BULL_COUNTERTREND / BEAR_MAINSTREAM / BEAR_COUNTERTREND
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


# 四个合法表面标签
SURFACE_LABELS = (
    "BULL_MAINSTREAM",
    "BULL_COUNTERTREND",
    "BEAR_MAINSTREAM",
    "BEAR_COUNTERTREND",
)

# 五个触发模式
TRIGGER_PATTERNS = ("BOF", "BPB", "PB", "TST", "CPB")

# 当前治理裁决（True = 主线准入，False = 拒绝，None = 待验证）
ADMISSION_TABLE: dict[str, dict[str, bool | None]] = {
    "BOF": {
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": None,
        "BEAR_MAINSTREAM": None,
        "BEAR_COUNTERTREND": None,
    },
    "BPB": {
        "BULL_MAINSTREAM": False,
        "BULL_COUNTERTREND": False,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": False,
    },
    "PB": {
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": None,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": False,
    },
    "TST": {
        "BULL_MAINSTREAM": None,
        "BULL_COUNTERTREND": None,
        "BEAR_MAINSTREAM": None,
        "BEAR_COUNTERTREND": None,
    },
    "CPB": {
        "BULL_MAINSTREAM": None,
        "BULL_COUNTERTREND": None,
        "BEAR_MAINSTREAM": None,
        "BEAR_COUNTERTREND": None,
    },
}


@dataclass
class CellStats:
    """单个格子（pattern × surface_label）的统计数据。"""

    pattern: str
    surface_label: str
    signal_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    avg_return_pct: float | None = None
    avg_r_multiple: float | None = None   # 平均 R 倍数
    admission: bool | None = None         # 治理裁决

    @property
    def win_rate(self) -> float | None:
        total = self.win_count + self.loss_count
        if total == 0:
            return None
        return self.win_count / total

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "surface_label": self.surface_label,
            "signal_count": self.signal_count,
            "win_count": self.win_count,
            "loss_count": self.loss_count,
            "win_rate": self.win_rate,
            "avg_return_pct": self.avg_return_pct,
            "avg_r_multiple": self.avg_r_multiple,
            "admission": self.admission,
        }


@dataclass
class SixteenCellMatrix:
    """16 格验证矩阵 — PAS 信号系统级 readout。"""

    cells: dict[str, dict[str, CellStats]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # 初始化所有格子（pattern × surface_label）
        for pattern in TRIGGER_PATTERNS:
            self.cells[pattern] = {}
            for label in SURFACE_LABELS:
                self.cells[pattern][label] = CellStats(
                    pattern=pattern,
                    surface_label=label,
                    admission=ADMISSION_TABLE.get(pattern, {}).get(label),
                )

    def get_cell(self, pattern: str, surface_label: str) -> CellStats | None:
        return self.cells.get(pattern, {}).get(surface_label)

    def is_admitted(self, pattern: str, surface_label: str) -> bool:
        cell = self.get_cell(pattern, surface_label)
        return cell is not None and cell.admission is True

    def summary_table(self) -> list[dict[str, Any]]:
        """返回所有格子的摘要列表。"""
        rows = []
        for pattern in TRIGGER_PATTERNS:
            for label in SURFACE_LABELS:
                cell = self.cells[pattern][label]
                rows.append(cell.as_dict())
        return rows

    def admitted_patterns_for_surface(self, surface_label: str) -> list[str]:
        """返回指定表面标签下所有准入的 pattern。"""
        return [
            pattern
            for pattern in TRIGGER_PATTERNS
            if self.is_admitted(pattern, surface_label)
        ]


def build_16cell_matrix(
    signal_records: list[dict[str, Any]],
) -> SixteenCellMatrix:
    """根据历史信号记录构建 16 格验证矩阵。

    参数：
        signal_records — 每条记录需含 {pattern, surface_label, pnl_pct, r_multiple, is_win}

    返回：
        SixteenCellMatrix 对象（已填充统计数据）
    """
    matrix = SixteenCellMatrix()

    for record in signal_records:
        pattern = record.get("pattern", "")
        label = record.get("surface_label", "")
        cell = matrix.get_cell(pattern, label)
        if cell is None:
            continue

        cell.signal_count += 1
        if record.get("is_win"):
            cell.win_count += 1
        else:
            cell.loss_count += 1

        # 累积收益（简化：仅做最后均值，实际应迭代更新）
        pnl = record.get("pnl_pct")
        r_mult = record.get("r_multiple")

        if pnl is not None:
            current_avg = cell.avg_return_pct or 0.0
            n = cell.signal_count
            cell.avg_return_pct = (current_avg * (n - 1) + pnl) / n

        if r_mult is not None:
            current_avg_r = cell.avg_r_multiple or 0.0
            n = cell.signal_count
            cell.avg_r_multiple = (current_avg_r * (n - 1) + r_mult) / n

    return matrix
