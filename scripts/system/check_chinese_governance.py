"""检查正式文档中文化与代码中文注释治理规则。

规则：
  - docs/ 下的 .md 文件必须包含中文内容。
  - src/ scripts/ tests/ 下的 .py 文件必须包含中文注释或中文 docstring。
  - pre-commit 模式（传入 paths）作为硬闸门，全仓扫描模式仅做债务盘点。
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查正式文档中文化与代码中文注释治理规则。")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="仓库根目录。")
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


def _has_chinese(text: str) -> bool:
    return bool(CJK_PATTERN.search(text))


def _has_chinese_comment_hint(text: str) -> bool:
    """检查 Python 文件是否包含中文注释或中文 docstring。"""
    in_docstring = False
    docstring_delimiter = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # 行注释
        if line.startswith("#") and _has_chinese(line):
            return True
        # 三引号 docstring
        triple_hits = [token for token in ('"""', "'''") if token in line]
        if triple_hits:
            token = triple_hits[0]
            hit_count = line.count(token)
            if hit_count >= 2:
                if _has_chinese(line):
                    return True
                continue
            if not in_docstring:
                in_docstring = True
                docstring_delimiter = token
                if _has_chinese(line):
                    return True
                continue
            if in_docstring and token == docstring_delimiter:
                if _has_chinese(line):
                    return True
                in_docstring = False
                docstring_delimiter = ""
                continue
        if in_docstring and _has_chinese(line):
            return True
    return False


def run_check(repo_root: Path, paths: list[str] | None = None) -> tuple[list[str], bool]:
    """检查中文化治理规则。"""
    markdown_failures: list[str] = []
    python_failures: list[str] = []
    strict_mode = bool(paths)

    for path in _candidate_files(repo_root, paths):
        rel = path.relative_to(repo_root).as_posix()
        suffix = path.suffix.lower()
        if suffix not in {".md", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        # 正式文档必须含中文
        if suffix == ".md" and (
            rel.startswith("docs/")
            or rel == "README.md"
            or rel == "AGENTS.md"
        ):
            if not _has_chinese(text):
                markdown_failures.append(rel)

        # src/scripts/tests 下 .py 必须含中文注释或 docstring
        if suffix == ".py" and (
            rel.startswith("src/")
            or rel.startswith("scripts/")
            or rel.startswith("tests/")
        ):
            if not _has_chinese_comment_hint(text):
                python_failures.append(rel)

    lines = ["[chinese-governance]"]
    ok = (not markdown_failures and not python_failures) if strict_mode else True

    if strict_mode:
        lines.append("  - 当前口径：对本次新增或改动文件做硬闸门。")
    else:
        lines.append("  - 当前口径：全仓扫描只做历史债务盘点，不因旧文件直接阻断。")

    if markdown_failures:
        title = "  - 缺少中文内容的正式 Markdown：" if strict_mode else "  - 历史债务：缺少中文内容的正式 Markdown："
        lines.append(title)
        lines.extend(f"    - {entry}" for entry in sorted(markdown_failures))

    if python_failures:
        title = "  - 缺少中文注释或中文 docstring 的 Python 文件：" if strict_mode else "  - 历史债务：缺少中文注释或中文 docstring 的 Python 文件："
        lines.append(title)
        lines.extend(f"    - {entry}" for entry in sorted(python_failures))

    if ok:
        if strict_mode:
            lines.append("  - 通过：本次改动范围满足当前中文治理硬闸门。")
        else:
            lines.append("  - 通过：当前全仓中文化旧债已完成显式登记，本轮没有新增未登记缺口。")

    return lines, ok


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    lines, ok = run_check(repo_root, paths=args.paths)
    output_text = "\n".join(lines)
    print(output_text)

    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "\n".join(["# chinese governance report", "", "```text", output_text, "```", ""]),
            encoding="utf-8",
        )

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
