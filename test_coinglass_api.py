"""
Coinglass 中转站 API 测试脚本
==============================
测试目标：确认 coins-price-change 接口返回结构，判断是否能一次拿到涨幅榜+足够数据
频率限制：1次/分钟，本脚本只调用1次
"""
import requests
import json
import time
from datetime import datetime

API_KEY = "myapi_sk_59d1be182bb41204b0607f9e42e661b4"
BASE_URL = "https://api.alphanode.work"

headers = {
    "x-key": API_KEY,
    "accept": "application/json"
}

# 目标接口：所有合约币种的24h价格变动（涨幅榜数据源）
path = "/open-api-v4.coinglass.com/api/futures/coins-price-change"

print(f"[{datetime.now().strftime('%H:%M:%S')}] 调用: {path}")
print(f"URL: {BASE_URL}{path}")
print("-" * 60)

try:
    r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)
    print(f"HTTP Status: {r.status_code}")
    print(f"响应头: {dict(r.headers)}")
    print("-" * 60)

    if r.status_code == 200:
        data = r.json()
        # 保存完整返回
        out_file = "api_response_coins_price_change.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"完整数据已保存到: {out_file}")
        print(f"数据类型: {type(data).__name__}")

        # 分析结构
        if isinstance(data, dict):
            print(f"顶层keys: {list(data.keys())[:20]}")
            # 找数据列表
            for k, v in data.items():
                if isinstance(v, list) and len(v) > 0:
                    print(f"\n列表字段 '{k}' 长度: {len(v)}")
                    print(f"第一条数据 keys: {list(v[0].keys()) if isinstance(v[0], dict) else type(v[0])}")
                    print(f"第一条数据样例:")
                    print(json.dumps(v[0], ensure_ascii=False, indent=2)[:1500])
                    break
        elif isinstance(data, list):
            print(f"列表长度: {len(data)}")
            if len(data) > 0:
                print(f"第一条 keys: {list(data[0].keys()) if isinstance(data[0], dict) else type(data[0])}")
                print(f"第一条样例:")
                print(json.dumps(data[0], ensure_ascii=False, indent=2)[:1500])
    else:
        print(f"非200响应，内容: {r.text[:1000]}")

except Exception as e:
    print(f"请求异常: {e}")
