"""
币安合约公开 API 客户端（可选模块，需代理）
==========================================
用于获取币安USDT永续合约的专属涨幅榜（比Coinglass全交易所聚合更准确）。
当前网络环境直连超时，需配置代理后启用。

环境变量：
- BINANCE_PROXY: 代理地址，如 http://127.0.0.1:7890
- BINANCE_API_KEY / BINANCE_API_SECRET: 可选，公开行情不需要
"""
import os
import requests
from typing import List, Dict, Any, Optional


class BinanceFuturesClient:
    """币安USDT永续合约公开API客户端"""

    def __init__(self, proxy: Optional[str] = None, timeout: int = 15):
        self.base_url = "https://fapi.binance.com"
        self.timeout = timeout
        self.proxies = None
        proxy = proxy or os.getenv("BINANCE_PROXY", "")
        if proxy:
            self.proxies = {"http": proxy, "https": proxy}
        self.session = requests.Session()
        if self.proxies:
            self.session.proxies.update(self.proxies)

    def _get(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        if r.status_code != 200:
            raise Exception(f"币安API HTTP {r.status_code}: {r.text[:300]}")
        return r.json()

    def get_perpetual_symbols(self) -> List[str]:
        """获取所有USDT永续合约交易对列表"""
        data = self._get("/fapi/v1/exchangeInfo")
        symbols = [
            s["symbol"] for s in data.get("symbols", [])
            if s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") == "USDT"
            and s.get("status") == "TRADING"
        ]
        return symbols

    def get_ticker_24hr(self) -> List[Dict[str, Any]]:
        """获取所有交易对24h行情"""
        return self._get("/fapi/v1/ticker/24hr")

    def get_top_gainers(
        self,
        top_n: int = 10,
        exclude_stock_etf: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        获取币安USDT永续合约涨幅榜
        返回按24h涨幅降序的交易对列表
        """
        symbols = set(self.get_perpetual_symbols())
        tickers = self.get_ticker_24hr()

        # 只保留USDT永续
        usdt_tickers = [t for t in tickers if t["symbol"] in symbols]

        # 过滤股票/ETF/商品
        if exclude_stock_etf:
            stock_keywords = [
                "TSLA", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX",
                "STOCK", "INDEX", "ETF", "SP500", "SPX", "QQQ", "SPY", "DIA",
                "XAU", "GOLD", "SILVER", "XAG", "OIL", "BRENT", "COPPER",
                "AMD", "INTC", "AVGO", "MSTR", "COIN", "ORCL", "CRM", "ADBE",
                "PYPL", "SHOP", "UBER", "NKE", "BA", "DIS", "JPM", "V",
            ]
            usdt_tickers = [
                t for t in usdt_tickers
                if not any(k in t["symbol"].upper() for k in stock_keywords)
            ]

        # 按24h涨幅排序
        sorted_tickers = sorted(
            usdt_tickers,
            key=lambda x: float(x["priceChangePercent"]),
            reverse=True,
        )
        return sorted_tickers[:top_n]

    def is_available(self) -> bool:
        """检测币安API是否可访问"""
        try:
            self._get("/fapi/v1/ping")
            return True
        except Exception:
            return False
