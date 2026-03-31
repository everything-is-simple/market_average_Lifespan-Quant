"""检查正式文件长度治理规则。

规则：
  - 单文件硬上限：1000 行（超过则阻断提交）
  - 单文件目标上限：800 行（超过则警告，不阻断）
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HARD_MAX_LINES = 1000
TARGET_MAX_LINES = 800


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查单文件长度治理规则。")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="仓库根目录。")
    parser.add_argument("--hard-max-lines", type=int, default=HARD_MAX_LINES, help="单文件硬上限。")
    parser.add_argument("--target-max-lines", type=int, default=TARGET_MAX_LINES, help="单文件目标上限。")
    parser.add_argument("--report-path", help="可选，把检查结果写入 Markdown 报告。")
    parser.add_argument(
        "paths",
        nargs="*",
        help="可选，只检查本次新增或改动文件；常用于 pre-commit 和 CI。",
    )
    return parser


def _git_tracked_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [repo_root / line for line in result.stdout.splitlines() if line.strip()]


def _candidate_files(repo_root: Path, paths: list[str] | None) -> list[Path]:
    if not paths:
        return _git_tracked_files(repo_root)

    candidates: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        resolved = path.resolve() if path.is_absolute() else (repo_root / path).resolve()
        if not resolved.exists() or not resolved.is_file():
            continue
        candidates.append(resolved)
    return candidates


def _read_text_line_count(path: Path) -> int | None:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (UnicodeDecodeError, OSError):
        return None


def run_check(
    repo_root: Path,
    *,
    hard_max_lines: int = HARD_MAX_LINES,
    target_max_lines: int = TARGET_MAX_LINES,
    paths: list[str] | None = None,
) -> tuple[list[str], bool]:
    """检查文件长度是否符合治理规则。"""
    strict_mode = bool(paths)
    hard_failures: list[str] = []
    soft_warnings: list[str] = []

    for path in _candidate_files(repo_root, paths):
        rel = path.relative_to(repo_root).as_posix()
        line_count = _read_text_line_count(path)
        if line_count is None:
            continue
        if line_count > hard_max_lines:
            hard_failures.append(f"{rel} ({line_count} 行)")
        elif line_count > target_max_lines:
            soft_warnings.append(f"{rel} ({line_count} 行)")

    lines = ["[file-length]"]
    ok = not hard_failures
    if hard_failures:
        lines.append(f"  - 超过 {hard_max_lines} 行硬上限，必须拆分再提交：")
        lines.extend(f"    - {entry}" for entry in sorted(hard_failures))
    else:
        scope_label = "本次改动范围" if strict_mode else "全仓已跟踪文件"
        lines.append(f"  - 通过：{scope_label}没有文件超过 {hard_max_lines} 行硬上限。")

    if soft_warnings:
        lines.append(f"  - 超过 {target_max_lines} 行目标上限（建议拆分，当前不阻断）：")
        lines.extend(f"    - {entry}" for entry in sorted(soft_warnings))

    return lines, ok


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    lines, ok = run_check(
        repo_root,
        hard_max_lines=args.hard_max_lines,
        target_max_lines=args.target_max_lines,
        paths=args.paths,
    )
    output_text = "\n".join(lines)
    print(output_text)

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(["# file length governance report", "", "```text", output_text, "```", ""]),
            encoding="utf-8",
        )

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
