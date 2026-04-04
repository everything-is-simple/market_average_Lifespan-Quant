"""data.providers.tdx_txt_reader — 通达信离线导出 txt 文件解析器。

数据来源：TDX_OFFLINE_DATA_ROOT（默认 H:\tdx_offline_Data）

目录结构：
  tdx_offline_Data/
    stock/
      Non-Adjusted/       SH#600000.txt, SZ#000001.txt, BJ#430047.txt
      Forward-Adjusted/   同上命名
      Backward-Adjusted/  同上命名
    index/
      Non-Adjusted/       SH#000001.txt ...

文件格式（TSV）：
  第1行：{code} {name} {period} {adjust_type}
  第2行：列头（日期 开盘 最高 最低 收盘 成交量 成交额）
  第3行起：数据行
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator

import pandas as pd


# ---------------------------------------------------------------------------
# 调整类型映射
# ---------------------------------------------------------------------------
_ADJUST_TYPE_MAP: dict[str, str] = {
    "不复权": "non_adjusted",
    "前复权": "forward",
    "后复权": "backward",
}

# 目录名 → adjust_type 映射
_DIR_TO_ADJUST_TYPE: dict[str, str] = {
    "Non-Adjusted": "non_adjusted",
    "Forward-Adjusted": "forward",
    "Backward-Adjusted": "backward",
}

# 市场前缀 → 标准化后缀
_MARKET_PREFIX_TO_SUFFIX: dict[str, str] = {
    "SH": "SH",
    "SZ": "SZ",
    "BJ": "BJ",
}

# 文件名正则：{MARKET}#{CODE}.txt
_FILENAME_PATTERN = re.compile(r"^(SH|SZ|BJ)#(\d{6})\.txt$", re.IGNORECASE)


@dataclass(frozen=True)
class TdxTxtFileInfo:
    """单个 txt 文件的元信息。"""

    path: Path
    market: str            # SH / SZ / BJ
    raw_code: str          # 6 位纯数字，如 600000
    normalized_code: str   # 标准化代码，如 600000.SH
    adjust_type: str       # non_adjusted / forward / backward
    security_type: str     # stock / index


@dataclass(frozen=True)
class TdxTxtMetadata:
    """从 txt 文件第一行解析出的元信息。"""

    code: str              # 6 位纯数字
    name: str              # 股票名称
    period: str            # 日线 / 周线 / 月线
    adjust_type_label: str # 不复权 / 前复权 / 后复权
    adjust_type: str       # non_adjusted / forward / backward


def parse_filename(filename: str) -> tuple[str, str] | None:
    """从文件名解析市场和代码。

    返回：
        (market, code) 或 None（文件名不匹配）
    """
    m = _FILENAME_PATTERN.match(filename)
    if not m:
        return None
    return m.group(1).upper(), m.group(2)


def parse_metadata_line(first_line: str) -> TdxTxtMetadata | None:
    """解析 txt 文件的第一行元信息。

    第一行格式：{code} {name} {period} {adjust_type}
    示例：600000 浦发银行 日线 不复权
    """
    parts = first_line.strip().split()
    if len(parts) < 4:
        return None

    code = parts[0]
    name = parts[1]
    period = parts[2]
    adjust_label = parts[3]

    adjust_type = _ADJUST_TYPE_MAP.get(adjust_label)
    if adjust_type is None:
        return None

    return TdxTxtMetadata(
        code=code,
        name=name,
        period=period,
        adjust_type_label=adjust_label,
        adjust_type=adjust_type,
    )


def discover_txt_files(
    root: Path,
    security_type: str = "stock",
    adjust_type: str | None = None,
    markets: tuple[str, ...] | None = None,
) -> list[TdxTxtFileInfo]:
    """扫描 TDX 离线导出目录，发现所有 txt 文件。

    参数：
        root          — TDX_OFFLINE_DATA_ROOT 路径
        security_type — "stock" 或 "index"
        adjust_type   — 限定调整类型（None = 全部）
        markets       — 限定市场（None = 全部）

    返回：
        TdxTxtFileInfo 列表，按 normalized_code 排序
    """
    base = root / security_type
    if not base.exists():
        return []

    results: list[TdxTxtFileInfo] = []

    # 遍历调整类型子目录
    for dir_name, adj_type in _DIR_TO_ADJUST_TYPE.items():
        if adjust_type is not None and adj_type != adjust_type:
            continue

        subdir = base / dir_name
        if not subdir.is_dir():
            continue

        for f in subdir.iterdir():
            if not f.is_file() or not f.name.endswith(".txt"):
                continue

            parsed = parse_filename(f.name)
            if parsed is None:
                continue

            market, code = parsed

            if markets is not None and market not in markets:
                continue

            suffix = _MARKET_PREFIX_TO_SUFFIX.get(market)
            if suffix is None:
                continue

            results.append(TdxTxtFileInfo(
                path=f,
                market=market,
                raw_code=code,
                normalized_code=f"{code}.{suffix}",
                adjust_type=adj_type,
                security_type=security_type,
            ))

    results.sort(key=lambda x: (x.adjust_type, x.normalized_code))
    return results


def parse_txt_file(
    file_info: TdxTxtFileInfo,
    encoding: str = "gbk",
) -> pd.DataFrame:
    """解析单个 txt 文件为 DataFrame。

    参数：
        file_info — 文件元信息
        encoding  — 文件编码（通达信导出默认 GBK）

    返回：
        DataFrame，列为 [trade_date, open, high, low, close, volume, amount]
        trade_date 为 datetime.date 类型
    """
    # 读取文件，跳过前2行（元信息行 + 列头行）
    try:
        df = pd.read_csv(
            file_info.path,
            sep="\t",
            skiprows=2,
            header=None,
            names=["trade_date", "open", "high", "low", "close", "volume", "amount"],
            encoding=encoding,
            engine="python",
        )
    except Exception:
        # 尝试 utf-8 兜底
        df = pd.read_csv(
            file_info.path,
            sep="\t",
            skiprows=2,
            header=None,
            names=["trade_date", "open", "high", "low", "close", "volume", "amount"],
            encoding="utf-8",
            engine="python",
        )

    if df.empty:
        return df

    # 清理：去掉全空行
    df = df.dropna(how="all").reset_index(drop=True)

    # 转换日期：YYYY/MM/DD → date
    df["trade_date"] = pd.to_datetime(
        df["trade_date"].astype(str).str.strip(), format="%Y/%m/%d", errors="coerce"
    ).dt.date
    df = df.dropna(subset=["trade_date"]).reset_index(drop=True)

    # 转换数值列
    for col in ["open", "high", "low", "close", "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

    # 添加标准化代码
    df["code"] = file_info.normalized_code

    return df


def iter_txt_dataframes(
    root: Path,
    security_type: str = "stock",
    adjust_type: str | None = None,
    markets: tuple[str, ...] | None = None,
    encoding: str = "gbk",
) -> Iterator[tuple[TdxTxtFileInfo, pd.DataFrame]]:
    """迭代式解析全部 txt 文件，逐文件 yield。

    用于大批量灌入时避免一次性加载全市场数据到内存。
    """
    files = discover_txt_files(root, security_type, adjust_type, markets)
    for fi in files:
        try:
            df = parse_txt_file(fi, encoding=encoding)
            if not df.empty:
                yield fi, df
        except Exception:
            # 静默跳过损坏文件，由调用方决定是否打印
            continue
