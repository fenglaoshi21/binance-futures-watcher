"""
测试 vip2.coinglass.site API（第二个API）
1. 查账户权限（不消耗额度）
2. 测 coins-markets
3. 测 LSR 信号（聪明钱+大户）
"""
import requests
import json
from datetime import datetime

API_KEY = "cg_84079e88fece703fca404b89e5743050b682c642cd733be7"
BASE_URL = "https://vip2.coinglass.site"

headers = {
    "X-API-Key": API_KEY,
    "Accept-Encoding": "gzip",
    "accept": "application/json"
}

def call(path, params=None, label=""):
    url = f"{BASE_URL}{path}"
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {label}")
    print(f"GET {url}")
    if params:
        print(f"params: {params}")
    try:
        r = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"HTTP {r.status_code}")
        # 打印频率限制头
        for h in ['X-Rate-Limit-Limit-User', 'X-Rate-Limit-Used-User',
                   'X-Rate-Limit-Remaining-User', 'Retry-After', 'X-API-Key-Expires-At']:
            if h in r.headers:
                print(f"  {h}: {r.headers[h]}")
        if r.status_code == 200:
            data = r.json()
            # 保存
            safe_name = label.replace(" ", "_").replace("/", "_")
            with open(f"api_response_vip2_{safe_name}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"已保存到 api_response_vip2_{safe_name}.json")
            # 打印结构
            if isinstance(data, dict):
                print(f"顶层keys: {list(data.keys())[:15]}")
                if 'data' in data and isinstance(data['data'], list):
                    print(f"data列表长度: {len(data['data'])}")
                    if len(data['data']) > 0:
                        print(f"第一条keys: {list(data['data'][0].keys())[:20]}")
                elif 'data' in data and isinstance(data['data'], dict):
                    print(f"data keys: {list(data['data'].keys())[:20]}")
                # 打印前1500字符
                print(f"内容预览: {json.dumps(data, ensure_ascii=False)[:1500]}")
            else:
                print(f"内容预览: {str(data)[:1500]}")
        else:
            print(f"响应: {r.text[:800]}")
        return r
    except Exception as e:
        print(f"异常: {e}")
        return None

# 1. 查账户（不消耗额度）
call("/api/gateway/account", label="account")

# 2. 测 coins-markets（只取10条，减少数据量）
call("/api/futures/coins-markets", params={"per_page": 10}, label="coins_markets")

# 3. 测 LSR 聪明钱信号 - BTC
call("/api/lsr/signal/BTC", params={"mode": "trader"}, label="lsr_signal_BTC_trader")

# 4. 测 LSR 大户信号 - BTC
call("/api/lsr/signal/BTC", params={"mode": "whale"}, label="lsr_signal_BTC_whale")
