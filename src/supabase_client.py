"""
Supabase 数据库客户端
====================
封装观测记录的读写、向量存储、RAG检索。
表结构见 sql/schema.sql
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None


class SupabaseDB:
    """Supabase 数据库操作封装"""

    def __init__(
        self,
        url: Optional[str] = None,
        service_key: Optional[str] = None,
    ):
        if create_client is None:
            raise ImportError("请先安装 supabase: pip install supabase")

        self.url = url or os.getenv("SUPABASE_URL", "")
        self.service_key = service_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

        if not self.url or not self.service_key:
            raise ValueError("需要 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY")

        self.client: Client = create_client(self.url, self.service_key)

    # ----------------------------------------------------------
    # 观测记录 (market_observation)
    # ----------------------------------------------------------

    def create_observation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建一条观测记录"""
        res = self.client.table("market_observation").insert(data).execute()
        return res.data[0] if res.data else None

    def update_observation(self, obs_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新观测记录"""
        res = self.client.table("market_observation").update(data).eq("id", obs_id).execute()
        return res.data[0] if res.data else None

    def get_observation(self, obs_id: int) -> Optional[Dict[str, Any]]:
        """获取单条观测记录"""
        res = self.client.table("market_observation").select("*").eq("id", obs_id).execute()
        return res.data[0] if res.data else None

    def get_latest_observation(self) -> Optional[Dict[str, Any]]:
        """获取最新一条已完成的观测记录"""
        res = (
            self.client.table("market_observation")
            .select("*")
            .eq("task_status", "completed")
            .order("observe_time", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    def list_observations(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取观测记录列表"""
        query = self.client.table("market_observation").select("*")
        if status:
            query = query.eq("task_status", status)
        res = (
            query.order("observe_time", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data

    def get_pending_observation(self) -> Optional[Dict[str, Any]]:
        """获取最早一条待处理的观测记录"""
        res = (
            self.client.table("market_observation")
            .select("*")
            .eq("task_status", "pending")
            .order("observe_time", desc=False)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    # ----------------------------------------------------------
    # 向量记忆 (observation_embedding)
    # ----------------------------------------------------------

    def insert_embedding(
        self,
        market_id: int,
        embedding: List[float],
        report_text: str,
    ) -> Dict[str, Any]:
        """插入一条向量记忆"""
        # pgvector 需要将向量转为字符串 '[0.1,0.2,...]'
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        res = (
            self.client.table("observation_embedding")
            .insert({
                "market_id": market_id,
                "embedding": embedding_str,
                "report_text": report_text,
            })
            .execute()
        )
        return res.data[0] if res.data else None

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        向量相似度检索（RAG）
        使用 pgvector 的余弦相似度，返回最相似的 top_k 条历史记录
        """
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # 使用 Supabase RPC 或直接 SQL 查询
        # 这里用 rpc 调用需要先在 Supabase 创建函数
        # 备用方案：用 postgrest 的 op 操作
        try:
            res = (
                self.client.rpc(
                    "match_observations",
                    {
                        "query_embedding": embedding_str,
                        "match_count": top_k,
                    },
                )
                .execute()
            )
            return res.data
        except Exception:
            # 如果 RPC 函数不存在，返回空列表
            # 需要在 Supabase SQL Editor 中创建 match_observations 函数
            return []

    # ----------------------------------------------------------
    # 完整一轮观测的写入
    # ----------------------------------------------------------

    def save_full_observation(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        lsr_data: Dict[str, Any],
        report: str,
        embedding: List[float],
        observe_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        保存完整一轮观测：
        1. 写入 market_observation（行情+报告）
        2. 写入 observation_embedding（向量）
        """
        if not observe_time:
            observe_time = datetime.now(timezone.utc).isoformat()

        # 1. 写入主表
        obs = self.create_observation({
            "observe_time": observe_time,
            "symbol": symbol,
            "change_24h": market_data.get("price_change_percent_24h"),
            "volume_24h": market_data.get("volume_change_usd_24h"),
            "open_interest": market_data.get("open_interest_usd"),
            "funding_rate": market_data.get("avg_funding_rate_by_oi"),
            "long_liq_24h": market_data.get("long_liquidation_usd_24h"),
            "short_liq_24h": market_data.get("short_liquidation_usd_24h"),
            "raw_data": {
                "market": market_data,
                "lsr": lsr_data,
            },
            "llm_report": report,
            "task_status": "completed",
        })

        if not obs:
            raise Exception("写入观测记录失败")

        # 2. 写入向量
        self.insert_embedding(
            market_id=obs["id"],
            embedding=embedding,
            report_text=report,
        )

        return obs
