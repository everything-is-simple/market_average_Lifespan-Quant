"""data 数据来源 providers 包。

主线（离线）：
  tdx_txt_reader — 通达信离线导出 txt 文件解析（一次性全量灌入）
  tdx_local      — mootdx 读取通达信本地.day 文件 + gbbq 除权除息（日增量）
辅助（在线，校准用）：
  tushare_http   — tushare HTTP API（第一校准：复权因子审计 / 基本面 / 交易日历）
  baostock       — BaoStock API（第二校准：adjust_factor / dividend_data，fallback）
"""

from lq.data.providers.baostock import (
    BaoStockProviderBoundary,
    from_baostock_code,
    get_baostock_boundary,
    to_baostock_code,
)
from lq.data.providers.tdx_txt_reader import (
    TdxTxtFileInfo,
    TdxTxtMetadata,
    discover_txt_files,
    iter_txt_dataframes,
    parse_txt_file,
)
from lq.data.providers.tdx_local import (
    TdxLocalDailyFile,
    classify_tdx_daily_file,
    create_tdx_reader,
    discover_tdx_daily_files,
    load_tdx_daily_dataset,
    parse_tdx_day_file,
)
from lq.data.providers.tushare_http import (
    TushareApiResponse,
    call_tushare_api,
    extract_tushare_token,
    load_tushare_token_from_file,
)

__all__ = [
    "BaoStockProviderBoundary",
    "from_baostock_code",
    "get_baostock_boundary",
    "to_baostock_code",
    "TdxTxtFileInfo",
    "TdxTxtMetadata",
    "discover_txt_files",
    "iter_txt_dataframes",
    "parse_txt_file",
    "TdxLocalDailyFile",
    "classify_tdx_daily_file",
    "create_tdx_reader",
    "discover_tdx_daily_files",
    "load_tdx_daily_dataset",
    "parse_tdx_day_file",
    "TushareApiResponse",
    "call_tushare_api",
    "extract_tushare_token",
    "load_tushare_token_from_file",
]
