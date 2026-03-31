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

# 当前治理裁决（True = 主线准入，False = 拒绝，None = 尚无充分证据）
# 注意：surface_label 只有 4 层。对于条件格 trigger（PB/TST/CPB），
# 表面标签准入 + monthly_state 过滤共同构成完整准入判断。
# 请使用 cell_gate_check() 进行精确 16 格判断。
#
# 父系统冻结来源：93（BOF）/ 110,121（PB）/ 126（TST）/ 129（CPB）/ 131（BPB）
ADMISSION_TABLE: dict[str, dict[str, bool | None]] = {
    "BOF": {
        # core trigger，持续态四格均为主力；FORMING/EXHAUSTING/REVERSING 格为辅助
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": True,
        "BEAR_MAINSTREAM": True,
        "BEAR_COUNTERTREND": True,
    },
    "BPB": {
        # 三年样本全面拒绝，永久禁止主线
        "BULL_MAINSTREAM": False,
        "BULL_COUNTERTREND": False,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": False,
    },
    "PB": {
        # 条件格准入：BULL_PERSISTING+with_flow / BEAR_PERSISTING+against_flow
        # surface_label 层面 True 为必要条件，还需结合 monthly_state 过滤（见 cell_gate_check）
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": False,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": True,
    },
    "TST": {
        # 条件格准入，父系统 126 号卡冻结：BULL_PERSISTING+MAINSTREAM / BEAR_PERSISTING+COUNTERTREND
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": False,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": True,
    },
    "CPB": {
        # 条件格准入，父系统 129 号卡冻结：BULL_PERSISTING+MAINSTREAM / BEAR_PERSISTING+COUNTERTREND
        "BULL_MAINSTREAM": True,
        "BULL_COUNTERTREND": False,
        "BEAR_MAINSTREAM": False,
        "BEAR_COUNTERTREND": True,
    },
}

# ---------------------------------------------------------------------------
# 精确 16 格准入表（monthly_state_8 × weekly_flow × pattern）
# 每个元素 = (monthly_state, weekly_flow) -> 允许模式集
# ---------------------------------------------------------------------------

# 所有条件格 trigger（PB/TST/CPB）共享相同的小准入集
_CONDITIONAL_ADMITTED_CELLS: frozenset[tuple[str, str]] = frozenset({
    ("BULL_PERSISTING", "with_flow"),      # BULL_PERSISTING__MAINSTREAM
    ("BEAR_PERSISTING", "against_flow"),   # BEAR_PERSISTING__COUNTERTREND
})

# BOF 在持续态四格都是主力，其他态也可触发但较稀疏
CELL_GATE_TABLE: dict[str, frozenset[tuple[str, str]]] = {
    "BOF": frozenset({
        ("BULL_PERSISTING", "with_flow"),
        ("BULL_PERSISTING", "against_flow"),
        ("BEAR_PERSISTING", "with_flow"),
        ("BEAR_PERSISTING", "against_flow"),
    }),
    "BPB": frozenset(),  # 全面拒绝
    "PB":  _CONDITIONAL_ADMITTED_CELLS,
    "TST": _CONDITIONAL_ADMITTED_CELLS,
    "CPB": _CONDITIONAL_ADMITTED_CELLS,
}


def cell_gate_check(pattern: str, monthly_state: str, weekly_flow: str) -> bool:
    """16 格精确准入判断（父系统冻结结论）。

    参数：
        pattern       — PasTriggerPattern 字符串屖
        monthly_state — MonthlyState8 值（来自 MalfContext.monthly_state）
        weekly_flow   — WeeklyFlowRelation 屖（来自 MalfContext.weekly_flow）

    返回：True = 允许进入主线 trigger 探测
    """
    admitted_cells = CELL_GATE_TABLE.get(pattern)
    if admitted_cells is None:
        return False
    return (monthly_state, weekly_flow) in admitted_cells


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
