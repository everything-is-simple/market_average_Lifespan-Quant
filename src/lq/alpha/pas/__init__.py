"""alpha/pas — PAS 五触发（BOF/BPB/PB/TST/CPB）与 16 格正式验证框架。"""

from .bootstrap import RESEARCH_LAB_SCHEMA_STATEMENTS, bootstrap_research_lab
from .contracts import PasSignal, PasDetectTrace, PasBatchResult
from .detectors import (
    detect_bof,
    detect_bpb,
    detect_pb,
    detect_tst,
    detect_cpb,
    run_all_detectors,
)
from .pipeline import run_pas_batch, run_pas_build, PasBuildResult, list_stock_codes
from .validation import SixteenCellMatrix, build_16cell_matrix

__all__ = [
    # bootstrap
    "RESEARCH_LAB_SCHEMA_STATEMENTS",
    "bootstrap_research_lab",
    # contracts
    "PasSignal",
    "PasDetectTrace",
    "PasBatchResult",
    # detectors
    "detect_bof",
    "detect_bpb",
    "detect_pb",
    "detect_tst",
    "detect_cpb",
    "run_all_detectors",
    # pipeline
    "run_pas_batch",
    "run_pas_build",
    "PasBuildResult",
    "list_stock_codes",
    # validation
    "SixteenCellMatrix",
    "build_16cell_matrix",
]
