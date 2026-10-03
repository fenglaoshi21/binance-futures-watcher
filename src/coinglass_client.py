"""
Coinglass/LSR API 客户端（主力：vip2.coinglass.site）
====================================================
封装 vip2 API 的调用，支持：
- coins-markets：全币种市场数据（74字段）
- lsr/signal/{symbol}：单币聪明钱/大户多空比
- gateway/account：账户额度查询（不消耗业务额度）

频率限制：Coinglass 10次/60秒，LSR 10次/60秒（独立额度）
鉴权：Header X-API-Key
"""
import os
import time
import requests
from typing import Dict, Any, Optional, List


class CoinglassClient:
    """Coinglass/LSR API 客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 30,
    ):
        self.api_key = api_key or os.getenv("VIP2_API_KEY", "")
        self.base_url = (base_url or os.getenv("VIP2_API_URL", "https://vip2.coinglass.site")).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Accept-Encoding": "gzip",
            "accept": "application/json",
        })
        # 简单的调用计数（用于本地调试）
        self.call_count = 0

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """统一GET请求，处理错误和频率限制"""
        url = f"{self.base_url}{path}"
        try:
            r = self.session.get(url, params=params, timeout=self.timeout)
            self.call_count += 1

            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", 5))
                raise RateLimitError(f"频率限制，需等待 {retry_after} 秒", retry_after=retry_after)

            if r.status_code != 200:
                raise ApiError(f"HTTP {r.status_code}: {r.text[:500]}", status_code=r.status_code)

            data = r.json()

            # Coinglass 接口：code="0" 表示成功
            if isinstance(data, dict) and "code" in data:
                if str(data.get("code")) != "0":
                    raise ApiError(f"业务码错误: code={data.get('code')}, msg={data.get('msg', data.get('message', ''))}")

            # LSR 接口：success=true 表示成功
            if isinstance(data, dict) and "success" in data:
                if not data.get("success"):
                    raise ApiError(f"LSR接口失败: {data}")

            return data

        except requests.exceptions.Timeout:
            raise ApiError(f"请求超时: {path}")
        except requests.exceptions.RequestException as e:
            raise ApiError(f"请求异常: {e}")

    # ----------------------------------------------------------
    # Coinglass 接口
    # ----------------------------------------------------------

    def get_coins_markets(self, per_page: int = 100) -> List[Dict[str, Any]]:
        """
        获取全币种市场数据（74字段）
        返回 data 列表
        """
        data = self._get("/api/futures/coins-markets", params={"per_page": per_page})
        return data.get("data", [])

    def get_account(self) -> Dict[str, Any]:
        """查询账户额度（不消耗业务额度）"""
        return self._get("/api/gateway/account")

    # ----------------------------------------------------------
    # LSR 接口（多空比）
    # ----------------------------------------------------------

    def get_lsr_signal(self, symbol: str, mode: str = "trader") -> Dict[str, Any]:
        """
        获取单个币种的 LSR 多空比信号
        symbol: BTC 或 BTCUSDT（不区分大小写）
        mode: trader（聪明钱）或 whale（大户）
        返回顶层字典（不包在data中）
        """
        # 统一去掉 USDT 后缀，接口两种都支持
        sym = symbol.upper().replace("USDT", "")
        data = self._get(f"/api/lsr/signal/{sym}", params={"mode": mode})
        return data

    def get_lsr_trader_and_whale(self, symbol: str) -> Dict[str, Any]:
        """
        同时获取聪明钱和大户两种模式的LSR信号
        返回 {"trader": {...}, "whale": {...}}
        """
        trader = self.get_lsr_signal(symbol, mode="trader")
        # 等待1秒避免频率问题（虽然10次/60秒很宽松）
        time.sleep(0.5)
        whale = self.get_lsr_signal(symbol, mode="whale")
        return {"trader": trader, "whale": whale}


class ApiError(Exception):
    """API调用错误"""
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(ApiError):
    """频率限制错误"""
    def __init__(self, message, retry_after=5):
        super().__init__(message)
        self.retry_after = retry_after
