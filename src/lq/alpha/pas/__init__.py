"""alpha/pas — PAS 五触发（BOF/BPB/PB/TST/CPB）与 16 格正式验证框架。"""

from .contracts import PasSignal, PasDetectTrace, PasBatchResult
from .detectors import (
    detect_bof,
    detect_bpb,
    detect_pb,
    detect_tst,
    detect_cpb,
    run_all_detectors,
)
from .validation import SixteenCellMatrix, build_16cell_matrix

__all__ = [
    "PasSignal",
    "PasDetectTrace",
    "PasBatchResult",
    "detect_bof",
    "detect_bpb",
    "detect_pb",
    "detect_tst",
    "detect_cpb",
    "run_all_detectors",
    "SixteenCellMatrix",
    "build_16cell_matrix",
]
