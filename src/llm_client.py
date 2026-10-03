"""
通义千问 LLM 客户端
==================
使用 OpenAI 兼容接口，无需安装 dashscope SDK。
- 文本生成：qwen-turbo / qwen-plus / qwen-max
- 文本嵌入：text-embedding-v1（1536维，匹配pgvector）
"""
import os
import requests
from typing import List, Optional


class QwenClient:
    """通义千问 API 客户端（OpenAI 兼容模式）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-turbo",
        embedding_model: str = "text-embedding-v1",
        timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """
        文本生成
        返回模型输出的文本内容
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            r = self.session.post(url, json=payload, timeout=self.timeout)
            if r.status_code != 200:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:500]}")
            data = r.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            raise LLMError("LLM请求超时")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"LLM请求异常: {e}")
        except (KeyError, IndexError) as e:
            raise LLMError(f"LLM响应解析失败: {e}, raw={r.text[:500] if 'r' in dir() else 'N/A'}")

    def embed(self, text: str) -> List[float]:
        """
        文本嵌入（向量化）
        返回1536维向量列表
        """
        url = f"{self.base_url}/embeddings"
        payload = {
            "model": self.embedding_model,
            "input": text,
        }

        try:
            r = self.session.post(url, json=payload, timeout=self.timeout)
            if r.status_code != 200:
                raise LLMError(f"Embedding HTTP {r.status_code}: {r.text[:500]}")
            data = r.json()
            return data["data"][0]["embedding"]
        except requests.exceptions.Timeout:
            raise LLMError("Embedding请求超时")
        except requests.exceptions.RequestException as e:
            raise LLMError(f"Embedding请求异常: {e}")
        except (KeyError, IndexError) as e:
            raise LLMError(f"Embedding响应解析失败: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量文本嵌入"""
        return [self.embed(t) for t in texts]


class LLMError(Exception):
    """LLM调用错误"""
    pass
