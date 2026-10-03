"""
Vercel Serverless 轻量触发接口
==============================
被 cron-job.org 每30分钟调用一次。
职责：仅在 market_observation 表插入一条 pending 任务，立即返回。
不做任何 API 调用、LLM 调用，确保在 Vercel Hobby 10s 超时内完成。
真正的采集+分析逻辑在 Supabase Edge Function 中执行。
"""

import os
import json
from http.server import BaseHTTPRequestHandler

# 延迟导入，避免冷启动时加载过重
_supabase_client = None


def get_supabase_client():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
        )
    return _supabase_client


def handler(event, context):
    """Vercel Python Serverless 入口"""
    try:
        client = get_supabase_client()
        # 插入一条待处理任务
        res = client.table("market_observation").insert({
            "task_status": "pending",
            "note": "auto-triggered by cron-job.org"
        }).execute()

        task_id = res.data[0]["id"] if res.data else None
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "code": 200,
                "msg": "任务已下发，等待 Edge Function 处理",
                "task_id": task_id
            })
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "code": 500,
                "msg": "触发失败",
                "error": str(e)
            })
        }
