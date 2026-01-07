"""
大模型客户端工具

支持 OpenAI 兼容的 API 接口，用于生成聊天回复。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class LLMClient:
    """大模型客户端

    支持 OpenAI 兼容的 API 格式，用于生成聊天回复。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ):
        """初始化 LLM 客户端

        Args:
            base_url: API 基础 URL
            api_key: API 密钥
            model_name: 模型名称
            max_tokens: 最大生成 token 数
            temperature: 生成温度
            timeout: 请求超时时间
        """
        if requests is None:
            raise ImportError("requests 库未安装，请运行: pip install requests")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        # 构造完整的 API 端点
        self.chat_url = f"{self.base_url}/v1/chat/completions"

        logger.info(f"LLM Client initialized: {self.model_name} at {self.base_url}")

    def generate_response(
        self,
        user_input: str,
        context: str = "",
        system_prompt: str = "你是一个有用的AI助手。",
    ) -> str:
        """生成聊天回复

        Args:
            user_input: 用户输入
            context: 对话上下文
            system_prompt: 系统提示词

        Returns:
            生成的回复文本

        Raises:
            Exception: API 调用失败
        """
        try:
            # 构造消息列表
            messages = [{"role": "system", "content": system_prompt}]

            # 添加上下文（如果有）
            if context and context.strip():
                messages.append(
                    {"role": "system", "content": f"以下是之前的对话历史作为参考：\n{context}"}
                )

            # 添加用户输入
            messages.append({"role": "user", "content": user_input})

            # 构造请求数据
            data = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": False,
            }

            # 构造请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            # 发送请求
            start_time = time.time()
            response = requests.post(
                self.chat_url,
                json=data,
                headers=headers,
                timeout=self.timeout,
            )

            # 检查响应状态
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 提取生成的文本
            if "choices" in result and len(result["choices"]) > 0:
                generated_text = result["choices"][0]["message"]["content"]

                # 记录性能信息
                duration = time.time() - start_time
                logger.debug(f"LLM response generated in {duration:.2f}s")

                return generated_text.strip()
            raise ValueError(f"Invalid API response format: {result}")

        except requests.exceptions.Timeout as e:
            raise Exception(f"LLM API 请求超时 ({self.timeout}s)") from e
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"无法连接到 LLM API: {self.base_url}") from e
        except requests.exceptions.HTTPError as e:
            raise Exception(
                f"LLM API 请求失败: {e.response.status_code} - {e.response.text}"
            ) from e
        except json.JSONDecodeError as e:
            raise Exception("LLM API 返回了无效的 JSON 响应") from e
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise Exception(f"LLM 生成失败: {str(e)}") from e

    def generate_simple_response(self, user_input: str) -> str:
        """生成简单回复（无上下文）

        Args:
            user_input: 用户输入

        Returns:
            生成的回复文本
        """
        return self.generate_response(user_input, context="")

    @classmethod
    def create_from_config(cls, config: dict[str, Any]) -> LLMClient:
        """从配置字典创建 LLM 客户端

        Args:
            config: 配置字典，包含以下键：
                - base_url: API 基础 URL
                - api_key: API 密钥
                - model_name: 模型名称
                - max_tokens: 最大生成 token 数（可选）
                - temperature: 生成温度（可选）
                - timeout: 请求超时时间（可选）

        Returns:
            LLM 客户端实例
        """
        required_keys = ["base_url", "api_key", "model_name"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config key: {key}")

        return cls(
            base_url=config["base_url"],
            api_key=config["api_key"],
            model_name=config["model_name"],
            max_tokens=config.get("max_tokens", 256),
            temperature=config.get("temperature", 0.7),
            timeout=config.get("timeout", 30.0),
        )


class MockLLMClient(LLMClient):
    """Mock LLM 客户端，用于测试

    不发送真实的 API 请求，返回预设的回复。
    """

    def __init__(self, **kwargs):
        """初始化 Mock 客户端"""
        # 使用虚拟参数初始化父类
        super().__init__(
            base_url="http://mock", api_key="mock-key", model_name="mock-model", **kwargs
        )

    def generate_response(
        self,
        user_input: str,
        context: str = "",
        system_prompt: str = "你是一个有用的AI助手。",
    ) -> str:
        """生成 Mock 回复"""
        user_lower = user_input.lower()

        if "你好" in user_lower or "hello" in user_lower:
            return "你好！我是基于 NeuroMem STM 的 AI 助手，很高兴与你聊天！"
        if "记忆" in user_lower or "memory" in user_lower:
            return "我使用短期记忆(STM)来记住我们的对话历史，这样可以提供更连贯的对话体验。"
        if "天气" in user_lower or "weather" in user_lower:
            return "抱歉，我暂时无法获取实时天气信息，但我会记住你询问了天气相关的问题。"
        if "帮助" in user_lower or "help" in user_lower:
            return (
                "我可以帮你进行对话，并记住我们聊天的内容。你可以：\n"
                "• 与我自由对话\n"
                "• 询问我们的对话历史\n"
                "• 让我基于上下文进行回复"
            )
        # 基于上下文生成回复
        if context and "暂无" not in context:
            return f"基于我们之前的对话，我注意到你提到了「{user_input}」。这是一个很有趣的话题！"
        return f"我理解你说的「{user_input}」。让我们继续聊下去吧！"
