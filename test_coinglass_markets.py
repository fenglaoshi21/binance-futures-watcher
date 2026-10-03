"""
测试 coins-markets 接口返回结构
看是否包含成交量、OI等更丰富数据
"""
import requests
import json
from datetime import datetime

API_KEY = "myapi_sk_59d1be182bb41204b0607f9e42e661b4"
BASE_URL = "https://api.alphanode.work"

headers = {"x-key": API_KEY, "accept": "application/json"}
path = "/open-api-v4.coinglass.com/api/futures/coins-markets"

print(f"[{datetime.now().strftime('%H:%M:%S')}] 调用: {path}")
try:
    r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)
    print(f"HTTP Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        with open("api_response_coins_markets.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已保存到 api_response_coins_markets.json")
        print(f"顶层keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if isinstance(data, dict) and 'data' in data:
            items = data['data']
            print(f"data长度: {len(items)}")
            if len(items) > 0:
                print(f"第一条 keys: {list(items[0].keys())}")
                print(f"第一条样例:")
                print(json.dumps(items[0], ensure_ascii=False, indent=2)[:2000])
    else:
        print(f"响应: {r.text[:1000]}")
except Exception as e:
    print(f"异常: {e}")
