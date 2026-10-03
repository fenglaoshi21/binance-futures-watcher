"""
股票/ETF/商品过滤模块
====================
从 coins-markets 返回的币种中剔除非加密货币合约。
过滤规则：黑名单匹配 + OI/成交量阈值过滤低流动性垃圾币。
"""
import re
from typing import List, Dict, Any

# ============================================================
# 黑名单：明确的股票、ETF、指数、商品、贵金属
# ============================================================

# 股票代码（币安上的股票代币）
STOCK_SYMBOLS = {
    # 美股科技
    "TSLA", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX",
    "AMD", "INTC", "AVGO", "MSTR", "COIN", "ORCL", "CRM", "ADBE",
    "PYPL", "SHOP", "SQ", "UBER", "LYFT", "SNAP", "PINS", "ZM",
    "DOCU", "PLTR", "SNOW", "CRWD", "PANW", "NET", "DDOG", "MDB",
    "NOW", "WDAY", "TEAM", "RNG", "ZS", "OKTA", "MNDY", "ASAN",
    # 美股金融/消费
    "JPM", "V", "JNJ", "WMT", "PG", "KO", "PEP", "XOM", "CVX",
    "DIS", "NKE", "BA", "BABA", "JD", "PDD", "BIDU", "NIO",
    "XPEV", "LI", "TME", "BILI", "FUTU", "TIGR",
    # 其他股票
    "MU", "AMGN", "GILD", "MRNA", "BNTX", "PFE", "MRK", "BMY",
    "LLY", "ABBV", "TMO", "DHR", "UNH", "CVS", "WBA",
    "GM", "F", "RIVN", "LCID", "ARKK", "SOFI", "HOOD",
    "COIN", "MARA", "RIOT", "HUT", "BITF", "CLSK",
    # OPENAI / ANTHROPIC 可能是股票代币也可能是meme币，保守起见不在这里过滤
}

# 后缀匹配：XXXSTOCK、XXXINDEX 等
STOCK_SUFFIXES = ("STOCK", "INDEX")

# ETF / 指数代码
ETF_SYMBOLS = {
    "QQQ", "SPY", "DIA", "IWM", "VTI", "VOO", "QQQM",
    "ARKK", "ARKW", "ARKG", "ARKQ", "ARKF",
    "TQQQ", "SQQQ", "UPRO", "SPXL", "SDS", "SH", "PSQ", "QID",
    "SOXL", "SOXS", "LABU", "LABD", "NUGT", "DUST",
    "SP500", "SPX500", "NDX", "NQ", "DJI", "DAX", "FTSE",
    "HSI", "HSCEI", "SSE", "SZSE", "CSI300", "CSI500",
    "NIFTY", "NIKKEI", "ASX200", "XYZ100", "VIX",
    "UVXY", "SVXY", "TVIX",
    # 行业ETF
    "XLK", "XLF", "XLE", "XLI", "XLY", "XLP", "XLU", "XLRE", "XLB", "XLC",
    "SMH", "SOXX", "VGT", "IGV", "FTEC", "CIBR", "HACK",
    "SKYY", "WCLD", "BUG", "XSD", "PSI", "FTXL",
    # 债券ETF
    "TLT", "IEF", "SHY", "HYG", "LQD", "JNK", "MUB", "TIP",
    "TMV", "TMF", "TBT", "UBT", "UST",
}

# 贵金属 / 商品
COMMODITY_SYMBOLS = {
    "XAU", "GOLD", "XAUT", "PAXG", "IAU", "GLD",
    "XAG", "SILVER", "SLV", "SIVR",
    "BRENTOIL", "CL", "OIL", "USO", "BNO", "DBO", "OIH",
    "NATGAS", "UNG", "BOIL", "KOLD",
    "COPPER", "CPER", "JJC",
    "PLAT", "PLTM", "PPLT",
    "PALL", "PALLD", "PALL",
    "LIT", "URA", "UCO", "SCO", "USO",
    "DBA", "DBC", "GSG", "WEAT", "CORN", "SOYB", "CANE",
    # 外汇
    "DXY", "EURUSD", "GBPUSD", "USDJPY", "USDCNH",
    # 半导体指数（非个股）
    "SKHY", "SKHYNIX", "SKHX", "SOX",
}

# 合并所有黑名单
ALL_BLACKLIST = STOCK_SYMBOLS | ETF_SYMBOLS | COMMODITY_SYMBOLS


def is_stock_or_etf(symbol: str) -> bool:
    """
    判断一个币种是否是股票/ETF/商品（非加密货币）
    返回 True 表示应该过滤掉
    """
    sym = symbol.upper().strip()

    # 1. 精确匹配黑名单
    if sym in ALL_BLACKLIST:
        return True

    # 2. 后缀匹配（XXXSTOCK、XXXINDEX）
    if sym.endswith(STOCK_SUFFIXES):
        return True

    # 3. 包含 INDEX 但不是加密货币（如 SP500INDEX）
    if "INDEX" in sym and sym not in ("DEX",):
        return True

    return False


def filter_cryptocurrency(
    items: List[Dict[str, Any]],
    min_oi_usd: float = 5_000_000,  # 最低OI 500万USDT
    min_24h_volume: float = 1_000_000,  # 最低24h成交量 100万USDT
) -> List[Dict[str, Any]]:
    """
    过滤币种列表：
    1. 剔除股票/ETF/商品
    2. 剔除低流动性（OI或成交量过低）
    3. 剔除24h涨跌幅为空的
    """
    result = []
    for item in items:
        sym = item.get("symbol", "")

        # 过滤股票/ETF/商品
        if is_stock_or_etf(sym):
            continue

        # 过滤24h涨跌幅为空
        chg = item.get("price_change_percent_24h")
        if chg is None:
            continue

        # 过滤低流动性
        oi = item.get("open_interest_usd", 0) or 0
        vol = item.get("volume_change_usd_24h", 0) or 0
        # volume_change_usd_24h 可能是变化量不是绝对值，用 market_cap 辅助判断
        mcap = item.get("market_cap_usd", 0) or 0

        # 至少满足 OI > 阈值 或 市值 > 阈值
        if oi < min_oi_usd and mcap < 50_000_000:  # 市值低于5000万也过滤
            continue

        result.append(item)

    return result


def get_top_gainers(
    items: List[Dict[str, Any]],
    top_n: int = 1,
    period: str = "24h",
) -> List[Dict[str, Any]]:
    """
    按指定周期涨跌幅排序，取涨幅前 N 名
    period: 5m, 15m, 30m, 1h, 4h, 12h, 24h
    """
    field = f"price_change_percent_{period}"
    sorted_items = sorted(
        items,
        key=lambda x: x.get(field, -9999),
        reverse=True
    )
    return sorted_items[:top_n]
