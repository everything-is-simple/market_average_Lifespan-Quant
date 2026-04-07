"""初始化 Lifespan-Quant 所有数据库存储层。

用法：
    python scripts/data/bootstrap_storage.py
    python scripts/data/bootstrap_storage.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 把 src/ 加到 sys.path，允许不安装包直接运行
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from lq.core.paths import default_settings
from lq.alpha.pas.bootstrap import bootstrap_research_lab
from lq.data.bootstrap import bootstrap_data_storage
from lq.filter.pipeline import bootstrap_filter_storage
from lq.malf.pipeline import bootstrap_malf_storage
from lq.structure.pipeline import bootstrap_structure_storage
from lq.trade.pipeline import bootstrap_trade_storage


def main(dry_run: bool = False) -> None:
    ws = default_settings()

    print("=" * 60)
    print("Lifespan-Quant — 存储初始化")
    print("=" * 60)
    print(f"  仓库根目录:  {ws.repo_root}")
    print(f"  数据根目录:  {ws.data_root}")
    print(f"  临时目录:    {ws.temp_root}")
    print(f"  报告目录:    {ws.report_root}")
    print(f"  验证目录:    {ws.validated_root}")
    print()

    dbs = ws.databases
    print("数据库路径：")
    for name, path in dbs.as_dict().items():
        status = "✓ 已存在" if path.exists() else "  将创建"
        print(f"  [{status}] {name}: {path}")
    print()

    if dry_run:
        print("[dry-run] 未执行任何写入操作。")
        return

    # 确保所有目录存在
    ws.ensure_directories()

    # 初始化 data 层数据库
    bootstrap_data_storage(dbs.raw_market, dbs.market_base)
    print("✓ raw_market + market_base 数据库 schema 初始化完成")

    # 初始化 malf 数据库
    bootstrap_malf_storage(dbs.malf)
    print("✓ malf 数据库 schema 初始化完成")

    # 初始化 structure 数据库
    bootstrap_structure_storage(dbs.structure)
    print("✓ structure 数据库 schema 初始化完成")

    # 初始化 filter 数据库
    bootstrap_filter_storage(dbs.filter)
    print("✓ filter 数据库 schema 初始化完成")

    # 初始化 research_lab 数据库（alpha/pas 正式信号表）
    bootstrap_research_lab(dbs.research_lab)
    print("✓ research_lab 数据库 schema 初始化完成")

    # 初始化 trade_runtime 数据库
    bootstrap_trade_storage(dbs.trade_runtime)
    print("✓ trade_runtime 数据库 schema 初始化完成")

    print()
    print("存储初始化完成。七库 schema 全部就绪。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化 Lifespan-Quant 存储层")
    parser.add_argument("--dry-run", action="store_true", help="仅打印路径，不实际写入")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
