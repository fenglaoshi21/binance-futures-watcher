"""
核心采集模块（双数据源）
========================
涨幅榜：币安官方 API（准确、免费、无频率限制，国外服务器直连）
专业数据：Coinglass coins-markets + LSR 聪明钱/大户多空比

每轮调用：
- 币安 exchangeInfo + ticker/24hr（2次，免费）
- Coinglass coins-markets（1次，10次/60秒额度）
- LSR signal trader + whale（2次，LSR独立额度10次/60秒）

⚠️ 免责声明：本模块仅采集行情数据用于分析，不构成投资建议。
"""
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coinglass_client import CoinglassClient, ApiError, RateLimitError
from binance_client import BinanceFuturesClient
from filters import filter_cryptocurrency, get_top_gainers


class MarketCollector:
    """市场数据采集器（双数据源）"""

    def __init__(
        self,
        vip2_api_key: Optional[str] = None,
        binance_proxy: Optional[str] = None,
        per_page: int = 100,
    ):
        self.coinglass = CoinglassClient(api_key=vip2_api_key)
        self.binance = BinanceFuturesClient(proxy=binance_proxy)
        self.per_page = per_page

    def _get_top_gainer_from_binance(self, top_n: int = 1) -> List[Dict[str, Any]]:
        """从币安官方API获取涨幅榜前N名"""
        try:
            return self.binance.get_top_gainers(top_n=top_n, exclude_stock_etf=True)
        except Exception as e:
            print(f"  [币安] 涨幅榜获取失败: {e}")
            return []

    def _find_coinglass_data(self, symbol: str, coinglass_list: List[Dict]) -> Optional[Dict]:
        """在 Coinglass 列表中匹配币种（BTCUSDT → BTC）"""
        base_symbol = symbol.upper().replace("USDT", "")
        for item in coinglass_list:
            if item.get("symbol", "").upper() == base_symbol:
                return item
        return None

    def collect(self, top_n: int = 1, period: str = "24h") -> Dict[str, Any]:
        """执行一轮完整采集（双数据源）"""
        observe_time = datetime.now(timezone.utc).isoformat()
        print(f"[{observe_time}] 开始采集（双数据源）...")

        # Step 1: 币安官方API涨幅榜
        print("  Step 1: 币安官方API获取涨幅榜...")
        binance_top = self._get_top_gainer_from_binance(top_n=top_n)

        if not binance_top:
            print("  币安API失败，回退到Coinglass coins-markets")
            all_coins = self.coinglass.get_coins_markets(per_page=self.per_page)
            filtered = filter_cryptocurrency(all_coins)
            top_list = get_top_gainers(filtered, top_n=top_n, period=period)
            binance_top = [
                {"symbol": c["symbol"] + "USDT", "priceChangePercent": c.get(f"price_change_percent_{period}")}
                for c in top_list
            ]

        top_symbol = binance_top[0]["symbol"]
        top_change = binance_top[0].get("priceChangePercent", 0)
        print(f"    币安涨幅第一: {top_symbol} ({top_change}%)")

        # Step 2: Coinglass 专业数据
        print("  Step 2: Coinglass coins-markets 获取专业数据...")
        coinglass_data = self.coinglass.get_coins_markets(per_page=self.per_page)
        print(f"    获取到 {len(coinglass_data)} 个币种")

        market_data = self._find_coinglass_data(top_symbol, coinglass_data)
        if market_data:
            print(f"    匹配到 Coinglass 数据: {market_data.get('symbol')}")
        else:
            print(f"    警告: Coinglass 中未找到 {top_symbol}，使用币安基础数据")
            market_data = {
                "symbol": top_symbol.replace("USDT", ""),
                "current_price": float(binance_top[0].get("lastPrice", 0)),
                "price_change_percent_24h": float(top_change),
                "volume_change_usd_24h": float(binance_top[0].get("quoteVolume", 0)),
            }

        # Step 3: LSR 聪明钱/大户多空比
        print(f"  Step 3: 获取 {top_symbol} 的 LSR 多空比...")
        try:
            lsr_data = self.coinglass.get_lsr_trader_and_whale(top_symbol)
            trader_ratio = lsr_data["trader"].get("ratio", "N/A")
            whale_ratio = lsr_data["whale"].get("whale_ratio", lsr_data["whale"].get("ratio", "N/A"))
            print(f"    聪明钱 ratio={trader_ratio}, 大户 ratio={whale_ratio}")
        except (ApiError, RateLimitError) as e:
            print(f"    LSR获取失败: {e}")
            lsr_data = {"trader": None, "whale": None, "error": str(e)}

        winner = {
            "symbol": top_symbol.replace("USDT", ""),
            "symbol_full": top_symbol,
            "binance_data": binance_top[0],
            "market_data": market_data,
            "lsr": lsr_data,
        }

        result = {
            "observe_time": observe_time,
            "period": period,
            "data_source": "binance_gainers + coinglass_market + lsr",
            "top_symbols": [t["symbol"] for t in binance_top],
            "winner": winner,
            "binance_top_list": binance_top,
        }

        print(f"  采集完成: 涨幅第一 = {winner['symbol']}")
        return result

    def collect_and_save(self, output_dir: str = ".", top_n: int = 1, period: str = "24h") -> Dict[str, Any]:
        """采集并保存到本地JSON文件"""
        result = self.collect(top_n=top_n, period=period)
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(output_dir, f"observation_{timestamp}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"  已保存到: {filepath}")
        return result


if __name__ == "__main__":
    vip2_key = os.getenv("VIP2_API_KEY", "cg_84079e88fece703fca404b89e5743050b682c642cd733be7")
    binance_proxy = os.getenv("BINANCE_PROXY", "http://127.0.0.1:7890")

    collector = MarketCollector(vip2_api_key=vip2_key, binance_proxy=binance_proxy, per_page=100)

    try:
        result = collector.collect_and_save(
            output_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"),
            top_n=1, period="24h",
        )
        if result["winner"]:
            w = result["winner"]
            md = w["market_data"]
            print("\n" + "=" * 60)
            print(f"涨幅榜第一名: {w['symbol_full']}")
            print(f"  24h涨幅: {md.get('price_change_percent_24h')}%")
            print(f"  当前价格: {md.get('current_price')}")
            print(f"  持仓量OI: {md.get('open_interest_usd', 0)/1e8:.2f}亿 USDT")
            print(f"  资金费率: {md.get('avg_funding_rate_by_oi')}")
            print(f"  24h爆仓: {md.get('liquidation_usd_24h', 0)/1e6:.2f}M USDT")
            print("=" * 60)
    except Exception as e:
        print(f"采集失败: {e}")
        import traceback; traceback.print_exc()
