"""
主流程 Pipeline
===============
完整一轮观测的端到端流程：
1. 采集：调用 Coinglass coins-markets + LSR，过滤后取涨幅第一
2. RAG检索：将当前行情摘要向量化，检索相似历史记录
3. LLM分析：组装Prompt，调用千问生成分析报告
4. 存储：写入 Supabase（行情+报告+向量）

用法：
  python pipeline.py                  # 完整一轮（需配置所有API）
  python pipeline.py --skip-db        # 只采集+分析，不写数据库
  python pipeline.py --skip-llm       # 只采集，不分析
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# 加载 .env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector import MarketCollector
from analyzer import MarketAnalyzer
from rag import RAGManager
from supabase_client import SupabaseDB
from llm_client import QwenClient


class ObservationPipeline:
    """观测主流程"""

    def __init__(
        self,
        vip2_api_key: Optional[str] = None,
        dashscope_api_key: Optional[str] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        use_db: bool = True,
    ):
        # 采集器（双数据源：币安涨幅榜 + Coinglass专业数据 + LSR）
        binance_proxy = os.getenv("BINANCE_PROXY")
        self.collector = MarketCollector(vip2_api_key=vip2_api_key, binance_proxy=binance_proxy)

        # LLM 客户端
        llm_model = os.getenv("QWEN_MODEL", "qwen-turbo")
        self.llm = QwenClient(api_key=dashscope_api_key, model=llm_model)
        self.analyzer = MarketAnalyzer(api_key=dashscope_api_key, model=llm_model)

        # 数据库
        self.use_db = use_db
        self.db = None
        self.rag = None

        if use_db and supabase_url and supabase_key:
            try:
                self.db = SupabaseDB(url=supabase_url, service_key=supabase_key)
                self.rag = RAGManager(llm_client=self.llm, db=self.db)
                print("[Pipeline] 数据库连接成功，RAG已启用")
            except Exception as e:
                print(f"[Pipeline] 数据库连接失败: {e}，将跳过数据库操作")
                self.use_db = False
        elif use_db:
            print("[Pipeline] 未配置 Supabase 凭证，将跳过数据库操作")
            self.use_db = False

    def run(self, top_n: int = 1, period: str = "24h") -> Dict[str, Any]:
        """
        执行完整一轮观测
        """
        start_time = datetime.now(timezone.utc)
        print(f"\n{'='*60}")
        print(f"[Pipeline] 开始观测 - {start_time.isoformat()}")
        print(f"{'='*60}")

        # ===== Step 1: 采集 =====
        print("\n[Step 1/4] 采集行情数据...")
        observation = self.collector.collect(top_n=top_n, period=period)

        if not observation.get("winner"):
            print("[Pipeline] 未找到涨幅第一名，终止")
            return {"error": "no_winner", "observation": observation}

        winner = observation["winner"]
        symbol = winner["symbol"]
        market_data = winner.get("market_data", {})
        lsr_data = winner.get("lsr", {})

        # ===== Step 2: RAG 检索相似历史 =====
        print(f"\n[Step 2/4] RAG检索相似历史记录...")
        retrieved_history = ""
        if self.use_db and self.rag:
            # 用当前行情摘要作为查询
            query_text = (
                f"{symbol} 24h涨幅{market_data.get('price_change_percent_24h')}% "
                f"资金费率{market_data.get('avg_funding_rate_by_oi')} "
                f"OI{market_data.get('open_interest_usd', 0)/1e8:.1f}亿 "
                f"爆仓{market_data.get('liquidation_usd_24h', 0)/1e6:.1f}M"
            )
            retrieved_history = self.rag.retrieve_and_format(query_text, top_k=3)
            print(f"  检索完成，历史记录长度: {len(retrieved_history)} 字符")
        else:
            retrieved_history = "数据库未配置，本次无历史记录参考。"
            print("  跳过RAG（数据库未配置）")

        # ===== Step 3: LLM 分析 =====
        print(f"\n[Step 3/4] 千问生成分析报告...")
        try:
            analysis_result = self.analyzer.analyze(
                observation=observation,
                retrieved_history=retrieved_history,
            )
            report = analysis_result["report"]
            embedding = analysis_result["embedding"]
            print(f"  报告生成完成: {len(report)} 字符, 向量维度: {len(embedding)}")
        except Exception as e:
            print(f"  LLM分析失败: {e}")
            report = f"LLM分析失败: {e}"
            embedding = []

        # ===== Step 4: 存储 =====
        print(f"\n[Step 4/4] 存储观测记录...")
        obs_id = None
        if self.use_db and self.db and embedding:
            try:
                saved = self.db.save_full_observation(
                    symbol=symbol,
                    market_data=market_data,
                    lsr_data=lsr_data,
                    report=report,
                    embedding=embedding,
                    observe_time=observation.get("observe_time"),
                )
                obs_id = saved["id"]
                print(f"  已写入数据库: id={obs_id}")
            except Exception as e:
                print(f"  数据库写入失败: {e}")
        else:
            print("  跳过数据库存储")

        # ===== 完成 =====
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        print(f"\n{'='*60}")
        print(f"[Pipeline] 观测完成 - 耗时 {elapsed:.1f}s")
        print(f"  标的: {symbol}")
        print(f"  24h涨幅: {market_data.get('price_change_percent_24h')}%")
        print(f"  数据库ID: {obs_id or '未存储'}")
        print(f"{'='*60}")

        # 打印报告摘要
        if report:
            print("\n" + report[:500] + ("..." if len(report) > 500 else ""))

        return {
            "symbol": symbol,
            "observe_time": observation.get("observe_time"),
            "market_data": market_data,
            "lsr_data": lsr_data,
            "report": report,
            "embedding_dim": len(embedding),
            "db_id": obs_id,
            "elapsed_seconds": elapsed,
        }


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="币安合约涨幅榜观测Pipeline")
    parser.add_argument("--skip-db", action="store_true", help="跳过数据库操作")
    parser.add_argument("--skip-llm", action="store_true", help="只采集，不分析")
    parser.add_argument("--top-n", type=int, default=1, help="取涨幅前N名")
    parser.add_argument("--period", type=str, default="24h", help="涨幅周期")
    args = parser.parse_args()

    # 从环境变量读取
    vip2_key = os.getenv("VIP2_API_KEY", "")
    dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    if not vip2_key:
        print("错误: 请设置 VIP2_API_KEY")
        sys.exit(1)

    if not args.skip_llm and not dashscope_key:
        print("错误: 请设置 DASHSCOPE_API_KEY（或使用 --skip-llm）")
        sys.exit(1)

    use_db = not args.skip_db and bool(sb_url and sb_key)

    pipeline = ObservationPipeline(
        vip2_api_key=vip2_key,
        dashscope_api_key=dashscope_key,
        supabase_url=sb_url,
        supabase_key=sb_key,
        use_db=use_db,
    )

    if args.skip_llm:
        # 只采集
        result = pipeline.collector.collect_and_save(
            output_dir=os.path.join(os.path.dirname(__file__), "..", "data"),
            top_n=args.top_n,
            period=args.period,
        )
    else:
        result = pipeline.run(top_n=args.top_n, period=args.period)

    # 保存完整结果到本地
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data",
        f"pipeline_result_{timestamp}.json"
    )
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完整结果已保存到: {outfile}")
