"""
RAG 长期记忆管理器
=================
封装向量嵌入、相似度检索、历史记录格式化。
每次分析前检索相似历史行情，提供给LLM做对比复盘。
"""
import os
import sys
from typing import List, Dict, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import QwenClient
from supabase_client import SupabaseDB


class RAGManager:
    """RAG 长期记忆管理器"""

    def __init__(
        self,
        llm_client: Optional[QwenClient] = None,
        db: Optional[SupabaseDB] = None,
        top_k: int = 3,
    ):
        self.llm = llm_client or QwenClient()
        self.db = db
        self.top_k = top_k

    def embed_text(self, text: str) -> List[float]:
        """将文本向量化"""
        return self.llm.embed(text)

    def search_similar(
        self,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据查询文本检索相似历史记录
        1. 将查询文本向量化
        2. 在 pgvector 中检索 top_k 条相似记录
        """
        if not self.db:
            return []

        k = top_k or self.top_k
        query_embedding = self.embed_text(query_text)
        results = self.db.search_similar(query_embedding, top_k=k)
        return results

    def format_history_for_prompt(
        self,
        similar_records: List[Dict[str, Any]],
    ) -> str:
        """
        将检索到的相似历史记录格式化为 LLM Prompt 可用的文本
        """
        if not similar_records:
            return "本次无匹配相似历史观测记录。"

        lines = []
        for i, record in enumerate(similar_records, 1):
            similarity = record.get("similarity", 0)
            report_text = record.get("report_text", "")
            market_id = record.get("market_id", "")
            create_time = record.get("create_time", "")

            lines.append(f"--- 相似历史记录 #{i} (相似度: {similarity:.4f}, ID: {market_id}, 时间: {create_time}) ---")
            # 只取报告前1000字符，避免Prompt过长
            lines.append(report_text[:1000])
            lines.append("")

        return "\n".join(lines)

    def retrieve_and_format(
        self,
        query_text: str,
        top_k: Optional[int] = None,
    ) -> str:
        """
        一站式：检索相似历史并格式化为Prompt文本
        """
        try:
            records = self.search_similar(query_text, top_k=top_k)
            return self.format_history_for_prompt(records)
        except Exception as e:
            print(f"[RAG] 检索失败: {e}")
            return f"本次RAG检索失败，无历史记录参考。错误: {str(e)[:100]}"

    def store_memory(
        self,
        market_id: int,
        report_text: str,
        embedding: Optional[List[float]] = None,
    ):
        """
        存储新的记忆（报告向量化后写入pgvector）
        """
        if not self.db:
            print("[RAG] 数据库未连接，跳过记忆存储")
            return

        if embedding is None:
            embedding = self.embed_text(report_text)

        self.db.insert_embedding(
            market_id=market_id,
            embedding=embedding,
            report_text=report_text,
        )
        print(f"[RAG] 已存储记忆: market_id={market_id}, 向量维度={len(embedding)}")
