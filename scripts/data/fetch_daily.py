"""日线数据增量拉取脚本（baostock）。

用法：
    python scripts/data/fetch_daily.py --window-start 2026-01-01 --window-end 2026-03-31
    python scripts/data/fetch_daily.py --full-refresh
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

# 把 src/ 加到 sys.path，允许不安装包直接运行
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from lq.core.paths import default_settings
from lq.data.contracts import IncrementalWindow


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def main(window_start: date | None, window_end: date | None) -> None:
    ws = default_settings()
    dbs = ws.databases

    window = IncrementalWindow(window_start=window_start, window_end=window_end)
    mode = "全量刷新" if window.is_full_refresh else f"{window_start} ~ {window_end}"

    print("=" * 60)
    print(f"Lifespan-Quant — 日线数据拉取 ({mode})")
    print("=" * 60)
    print(f"  目标数据库: {dbs.raw_market}")
    print()

    # TODO: 在此接入 baostock 拉取逻辑
    # 参考父系统 G:\MarketLifespan-Quant\src\mlq\data\providers\
    print("[stub] 数据拉取逻辑待实现，参考父系统 data.providers 模块。")
    print("       需要 baostock 账号（环境变量 BAOSTOCK_USER / BAOSTOCK_PWD）。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="日线数据增量拉取")
    parser.add_argument("--window-start", type=str, help="增量起始日期 YYYY-MM-DD")
    parser.add_argument("--window-end", type=str, help="增量结束日期 YYYY-MM-DD")
    parser.add_argument("--full-refresh", action="store_true", help="全量刷新")
    args = parser.parse_args()

    if args.full_refresh:
        start, end = None, None
    else:
        start = _parse_date(args.window_start) if args.window_start else None
        end = _parse_date(args.window_end) if args.window_end else None

    main(start, end)
