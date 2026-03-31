"""通达信本地目录 provider。

主要功能：
  1. 扫描本地 vipdoc/{sh,sz,bj}/lday/ 目录，发现所有 .day 文件
  2. 通过 mootdx.reader.Reader 读取日线数据
  3. mootdx 失败时回退到直接解析 .day 二进制（兜底）
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from struct import Struct

import pandas as pd

# mootdx 可选导入：若未安装则只能走兜底解析路径
try:
    from mootdx.reader import Reader as _MootdxReader
    _HAS_MOOTDX = True
except ImportError:
    _HAS_MOOTDX = False
    _MootdxReader = None  # type: ignore[assignment,misc]


_SUPPORTED_MARKETS = ("sh", "sz", "bj")
# 通达信 .day 文件单条记录格式：date/open/high/low/close/amount/volume/reserve
_TDX_DAY_RECORD = Struct("<IIIIIfII")


@dataclass(frozen=True)
class TdxLocalDailyFile:
    """单个通达信本地日线文件的元数据。"""

    market: str
    code: str
    file_path: Path
    security_type: str   # "stock" | "index" | "unsupported"

    @property
    def qualified_symbol(self) -> str:
        """mootdx reader 使用的 sh000001 / sz000001 格式。"""
        return f"{self.market}{self.code}"

    @property
    def normalized_code(self) -> str:
        """统一码格式 000001.SH / 000001.SZ。"""
        return f"{self.code}.{self.market.upper()}"


def create_tdx_reader(tdx_root: Path):
    """创建 mootdx 本地读取器。tdx_root 为通达信安装根目录。"""
    if not _HAS_MOOTDX:
        raise ImportError("mootdx 未安装，无法创建 reader，请先 pip install mootdx。")
    return _MootdxReader.factory(market="std", tdxdir=str(tdx_root))


def classify_tdx_daily_file(market: str, code: str) -> str:
    """按交易所与代码前缀判断股票还是指数，返回 'stock' / 'index' / 'unsupported'。"""
    if market == "sh":
        if code.startswith(("000", "880", "999")):
            return "index"
        if code.startswith(("600", "601", "603", "605", "688", "689", "900")):
            return "stock"
        return "unsupported"
    if market == "sz":
        if code.startswith("399"):
            return "index"
        if code.startswith(("000", "001", "002", "003", "200", "300", "301")):
            return "stock"
        return "unsupported"
    if market == "bj":
        if code.startswith(("4", "8")):
            return "stock"
        return "unsupported"
    raise ValueError(f"不支持的市场目录: {market}")


def discover_tdx_daily_files(
    tdx_root: Path,
    markets: tuple[str, ...] = _SUPPORTED_MARKETS,
    limit_files: int | None = None,
    stock_codes: list[str] | None = None,
) -> list[TdxLocalDailyFile]:
    """扫描通达信本地目录下的 lday .day 文件，返回 TdxLocalDailyFile 列表。

    Args:
        tdx_root:    通达信安装根目录（含 vipdoc/ 子目录）
        markets:     要扫描的市场，默认 sh/sz/bj
        limit_files: 最多返回多少个文件（调试用）
        stock_codes: 若指定，则只返回指定代码（normalized_code 格式，如 ["000001.SZ"]）
    """
    root = Path(tdx_root)
    normalized_code_set = {
        item.strip().upper() for item in (stock_codes or []) if item.strip()
    }
    discovered: list[TdxLocalDailyFile] = []
    for market in markets:
        market_dir = root / "vipdoc" / market / "lday"
        if not market_dir.exists():
            continue
        for file_path in sorted(market_dir.glob(f"{market}*.day")):
            code = file_path.stem[len(market):]
            daily_file = TdxLocalDailyFile(
                market=market,
                code=code,
                file_path=file_path,
                security_type=classify_tdx_daily_file(market, code),
            )
            if daily_file.security_type == "unsupported":
                continue
            if normalized_code_set and daily_file.normalized_code not in normalized_code_set:
                continue
            discovered.append(daily_file)
            if limit_files is not None and len(discovered) >= limit_files:
                return discovered
    return discovered


def _parse_trade_date(raw_value: int):
    """将 TDX 整数日期（如 20240101）解析为 date 对象。"""
    try:
        return datetime.strptime(str(raw_value), "%Y%m%d").date()
    except ValueError:
        return None


def parse_tdx_day_file(file_path: Path) -> pd.DataFrame:
    """直接解析通达信 .day 二进制文件（mootdx 失败时的兜底路径）。

    返回列：open / high / low / close / volume / amount（index 为 trade_date）
    """
    payload = file_path.read_bytes()
    if not payload:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])
    if len(payload) % _TDX_DAY_RECORD.size != 0:
        raise ValueError(f"非法 .day 文件长度: {file_path}")

    rows: list[dict] = []
    for offset in range(0, len(payload), _TDX_DAY_RECORD.size):
        record = payload[offset: offset + _TDX_DAY_RECORD.size]
        raw_date, raw_open, raw_high, raw_low, raw_close, raw_amount, raw_volume, _ = (
            _TDX_DAY_RECORD.unpack(record)
        )
        trade_date = _parse_trade_date(raw_date)
        if trade_date is None:
            continue
        rows.append({
            "trade_date": trade_date,
            "open":   raw_open / 100.0,
            "high":   raw_high / 100.0,
            "low":    raw_low / 100.0,
            "close":  raw_close / 100.0,
            "volume": float(raw_volume),
            "amount": float(raw_amount),
        })

    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "amount"])

    df = pd.DataFrame(rows)
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    return df[["open", "high", "low", "close", "volume", "amount"]]


def load_tdx_daily_dataset(reader, daily_file: TdxLocalDailyFile) -> pd.DataFrame:
    """加载单个股票/指数的日线数据。

    优先走 mootdx reader；读不到时回退到 .day 二进制解析，
    避免单个市场 reader 缺口拖垮全量导入。
    """
    if reader is not None:
        try:
            dataset = reader.daily(symbol=daily_file.qualified_symbol)
            if dataset is not None and not dataset.empty:
                return dataset
        except Exception:
            pass
    # mootdx 失败 → 直接解析二进制
    return parse_tdx_day_file(daily_file.file_path)
