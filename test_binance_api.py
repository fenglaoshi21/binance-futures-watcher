"""
测试币安合约公开 API
====================
不需要 API Key，免费获取币安USDT永续合约涨幅榜
接口：
- GET /fapi/v1/exchangeInfo  交易对信息（过滤永续合约）
- GET /fapi/v1/ticker/24hr    所有交易对24h行情
"""
import requests
import json

BASE_URL = "https://fapi.binance.com"

def test_exchange_info():
    """获取交易对信息，过滤USDT永续合约"""
    print("=" * 60)
    print("测试: /fapi/v1/exchangeInfo")
    r = requests.get(f"{BASE_URL}/fapi/v1/exchangeInfo", timeout=15)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        symbols = data.get("symbols", [])
        # 过滤 USDT 永续合约
        perpetual_usdt = [
            s for s in symbols
            if s.get("contractType") == "PERPETUAL"
            and s.get("quoteAsset") == "USDT"
            and s.get("status") == "TRADING"
        ]
        print(f"总交易对数: {len(symbols)}")
        print(f"USDT永续合约数: {len(perpetual_usdt)}")
        # 看看有没有股票/ETF代币
        stock_keywords = ["TSLA", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "STOCK", "INDEX", "ETF"]
        stock_tokens = [s["symbol"] for s in perpetual_usdt if any(k in s["symbol"].upper() for k in stock_keywords)]
        print(f"可能的股票/ETF代币: {stock_tokens[:20]}")
        # 保存USDT永续列表
        with open("binance_perpetual_symbols.json", "w") as f:
            json.dump([s["symbol"] for s in perpetual_usdt], f)
        print(f"已保存 {len(perpetual_usdt)} 个USDT永续合约到 binance_perpetual_symbols.json")
        return perpetual_usdt
    else:
        print(f"错误: {r.text[:500]}")
        return []

def test_ticker_24hr():
    """获取所有交易对24h行情"""
    print("\n" + "=" * 60)
    print("测试: /fapi/v1/ticker/24hr")
    r = requests.get(f"{BASE_URL}/fapi/v1/ticker/24hr", timeout=15)
    print(f"HTTP {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"返回交易对数: {len(data)}")
        if len(data) > 0:
            print(f"第一条字段: {list(data[0].keys())}")
            print(f"第一条样例: symbol={data[0]['symbol']}, change={data[0]['priceChangePercent']}%, vol={data[0]['quoteVolume']}")
        return data
    else:
        print(f"错误: {r.text[:500]}")
        return []

if __name__ == "__main__":
    try:
        symbols = test_exchange_info()
        tickers = test_ticker_24hr()

        # 合并：只保留USDT永续合约，按24h涨幅排序
        if symbols and tickers:
            usdt_symbols = set(s["symbol"] for s in symbols)
            usdt_tickers = [t for t in tickers if t["symbol"] in usdt_symbols]

            # 过滤股票/ETF
            stock_keywords = ["TSLA", "AAPL", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "STOCK", "INDEX", "ETF", "SP500", "SPX", "QQQ", "SPY", "XAU", "GOLD", "SILVER", "OIL"]
            crypto_tickers = [t for t in usdt_tickers if not any(k in t["symbol"].upper() for k in stock_keywords)]

            sorted_tickers = sorted(crypto_tickers, key=lambda x: float(x["priceChangePercent"]), reverse=True)
            print("\n" + "=" * 60)
            print(f"币安USDT永续合约 24h涨幅 Top 15（已过滤股票/ETF）")
            print(f"总加密货币合约数: {len(crypto_tickers)}")
            for i, t in enumerate(sorted_tickers[:15], 1):
                print(f"{i:2d}. {t['symbol']:15s}  24h: {float(t['priceChangePercent']):>7.2f}%  量: {float(t['quoteVolume'])/1e8:>8.1f}亿  价格: {t['lastPrice']}")

            # 保存
            with open("binance_top_gainers.json", "w") as f:
                json.dump(sorted_tickers[:50], f, indent=2)
            print("\n已保存 Top50 到 binance_top_gainers.json")

    except Exception as e:
        print(f"异常: {e}")
        import traceback
        traceback.print_exc()
