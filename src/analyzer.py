"""
行情分析器
==========
组装采集数据 → 构建Prompt → 调用千问生成分析报告 → 向量化报告
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm_client import QwenClient, LLMError
from prompts import SYSTEM_PROMPT, build_user_prompt


class MarketAnalyzer:
    """行情分析器"""

    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-turbo"):
        self.llm = QwenClient(api_key=api_key, model=model)

    def analyze(
        self,
        observation: Dict[str, Any],
        retrieved_history: str = "",
    ) -> Dict[str, Any]:
        """
        对一轮观测数据生成分析报告
        observation: collector.collect() 的返回结果
        retrieved_history: RAG检索到的历史记录文本
        返回：{"report": str, "embedding": List[float], "symbol": str}
        """
        winner = observation.get("winner")
        if not winner:
            raise ValueError("观测数据中没有winner（涨幅第一名）")

        symbol = winner["symbol"]
        market_data = winner.get("market_data", {})
        lsr_data = winner.get("lsr", {})
        observe_time = observation.get("observe_time", datetime.now().isoformat())

        print(f"[Analyzer] 正在分析 {symbol}...")

        # 1. 构建用户Prompt
        user_prompt = build_user_prompt(
            market_data=market_data,
            lsr_data=lsr_data,
            observe_time=observe_time,
            retrieved_history=retrieved_history,
        )

        # 2. 调用千问生成报告
        print(f"  调用千问 {self.llm.model} 生成报告...")
        report = self.llm.chat(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=2000,
        )
        print(f"  报告生成完成，长度: {len(report)} 字符")

        # 3. 向量化报告（用于RAG长期记忆）
        print(f"  向量化报告 (text-embedding-v1)...")
        embedding = self.llm.embed(report)
        print(f"  向量维度: {len(embedding)}")

        return {
            "symbol": symbol,
            "observe_time": observe_time,
            "report": report,
            "embedding": embedding,
            "market_data": market_data,
            "lsr_data": lsr_data,
        }

    def analyze_from_file(self, filepath: str, retrieved_history: str = "") -> Dict[str, Any]:
        """从本地JSON文件加载观测数据并分析"""
        with open(filepath, "r", encoding="utf-8") as f:
            observation = json.load(f)
        return self.analyze(observation, retrieved_history)


# ============================================================
# 命令行入口：python analyzer.py <observation.json>
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyzer.py <observation.json>")
        print("示例: python analyzer.py ../data/observation_20261003_124132.json")
        sys.exit(1)

    filepath = sys.argv[1]
    api_key = os.getenv("DASHSCOPE_API_KEY", "")

    if not api_key:
        print("错误: 请设置环境变量 DASHSCOPE_API_KEY")
        print("  export DASHSCOPE_API_KEY=sk-xxx")
        sys.exit(1)

    analyzer = MarketAnalyzer(api_key=api_key)

    try:
        result = analyzer.analyze_from_file(filepath)

        # 保存报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"../data/report_{result['symbol']}_{timestamp}.txt"
        report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), report_file)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"标的: {result['symbol']}\n")
            f.write(f"观测时间: {result['observe_time']}\n")
            f.write("=" * 60 + "\n\n")
            f.write(result["report"])

        print(f"\n报告已保存到: {report_path}")
        print("\n" + "=" * 60)
        print(result["report"])
        print("=" * 60)

    except LLMError as e:
        print(f"LLM错误: {e}")
    except Exception as e:
        print(f"分析失败: {e}")
        import traceback
        traceback.print_exc()
