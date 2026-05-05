"""
LLM API 客户端
负责与小米 Mimo LLM API 通信，处理对话请求和回复
"""

import json
import time
import logging
import requests
from typing import Optional

from config import (
    API_KEY, API_ENDPOINT, MODEL_NAME,
    MAX_TOKENS, TEMPERATURE, SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM API 客户端"""

    def __init__(self):
        self.api_key = API_KEY
        self.endpoint = API_ENDPOINT.rstrip('/')
        self.model = MODEL_NAME
        self.max_tokens = MAX_TOKENS
        self.temperature = TEMPERATURE
        self.system_prompt = SYSTEM_PROMPT
        self.conversation_history: list[dict] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self._session: Optional[requests.Session] = None

    @property
    def session(self) -> requests.Session:
        """懒加载 HTTP 会话"""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
        return self._session

    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def clear_history(self):
        """清除对话历史"""
        self.conversation_history.clear()

    def get_context_messages(self) -> list[dict]:
        """获取带 system prompt 的上下文消息"""
        return [
            {"role": "system", "content": self.system_prompt}
        ] + self.conversation_history[-30:]  # 限制上下文长度

    def chat(self, user_message: str) -> tuple[str, dict]:
        """
        发送聊天请求
        
        Returns:
            (回复文本, Token使用统计)
        """
        # 添加用户消息
        self.add_message("user", user_message)

        # 构建请求数据
        payload = {
            "model": self.model,
            "messages": self.get_context_messages(),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        start_time = time.time()
        try:
            response = self.session.post(
                f"{self.endpoint}/chat/completions",
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            # 解析回复
            assistant_message = data["choices"][0]["message"]["content"]
            
            # 统计Token
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            # 累加统计
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens

            # 添加助手回复到历史
            self.add_message("assistant", assistant_message)

            token_stats = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "latency_ms": int((time.time() - start_time) * 1000),
                "cumulative_input": self.total_input_tokens,
                "cumulative_output": self.total_output_tokens,
            }

            logger.info(f"API调用完成: {token_stats}")
            return assistant_message, token_stats

        except requests.exceptions.Timeout:
            error_msg = "请求超时了...网络可能不太好(｡･ω･｡)"
            logger.error("API请求超时")
            # 移除失败的用户消息
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            return error_msg, {"error": "timeout"}

        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else -1
            error_msg = f"哎呀，出错了({status_code})..."
            logger.error(f"API请求HTTP错误: {status_code} - {e}")
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            return error_msg, {"error": f"http_{status_code}"}

        except Exception as e:
            error_msg = "出了点问题...稍后再试试吧(｡･ω･｡)"
            logger.error(f"API请求异常: {e}", exc_info=True)
            if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                self.conversation_history.pop()
            return error_msg, {"error": str(e)}

    def detect_emotion(self, text: str) -> str:
        """
        根据回复文本检测情绪类型
        
        Returns:
            emotion_type: 'positive', 'surprised', 'sad', 'angry', 'singing', 'neutral'
        """
        text_lower = text.lower()

        # 愤怒关键词
        angry_words = ["生气", "哼", "讨厌", "烦", "气死", "可恶", "太过分"]
        for w in angry_words:
            if w in text:
                return "angry"

        # 惊讶/困惑关键词
        surprise_words = ["诶", "咦", "哇", "天呐", "不会吧", "真的吗", "啊？", "oao"]
        for w in surprise_words:
            if w in text_lower or w in text.lower():
                return "surprised"

        # 消极/委屈/抱歉关键词
        sad_words = ["对不起", "抱歉", "难过", "伤心", "qaq", "呜呜", "不好意思", "失礼"]
        for w in sad_words:
            if w in text_lower or w in text.lower():
                return "sad"

        # 唱歌/表演关键词
        sing_words = ["唱歌", "表演", "唱一首", "音乐", "哼歌", "麦克风", "mic"]
        for w in sing_words:
            if w in text:
                return "singing"

        # 积极情绪关键词
        positive_words = ["开心", "哈哈", "嘻嘻", "(｡･ω･｡)", "棒", "好耶", "太好了", "聪明"]
        for w in positive_words:
            if w in text:
                return "positive"

        return "neutral"
