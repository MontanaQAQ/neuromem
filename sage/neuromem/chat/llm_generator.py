"""
LLM 回复生成组件

负责调用大模型生成聊天回复。
"""

from __future__ import annotations

import logging
from typing import Any

from ..utils.llm_client import LLMClient, MockLLMClient

logger = logging.getLogger(__name__)


class LLMGenerator:
    """LLM 回复生成器

    使用大模型生成基于上下文的聊天回复。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化 LLM 生成器"""
        self.config = config or {}

        # LLM 配置
        self.system_prompt = self.config.get(
            "system_prompt",
            "你是一个智能的AI助手，基于NeuroMem短期记忆系统。请根据用户输入和对话历史，提供有用、准确、友好的回复。",
        )

        # 创建 LLM 客户端
        if self._is_mock_mode():
            self.llm_client = MockLLMClient()
            logger.info("Using MockLLMClient for testing")
        else:
            self.llm_client = LLMClient.create_from_config(self._get_llm_config())
            logger.info(f"LLM Generator initialized with model: {self.llm_client.model_name}")

    def _is_mock_mode(self) -> bool:
        """检查是否使用 Mock 模式"""
        return self.config.get("use_mock_llm", False)

    def _get_llm_config(self) -> dict[str, Any]:
        """获取 LLM 配置"""
        required_keys = ["api_key", "base_url", "model_name"]
        llm_config = {}

        # 从配置中提取 LLM 相关配置
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required LLM config: {key}")
            llm_config[key] = self.config[key]

        # 可选配置
        optional_keys = ["max_tokens", "temperature", "timeout"]
        for key in optional_keys:
            if key in self.config:
                llm_config[key] = self.config[key]

        return llm_config

    def generate_response(self, user_input: str, context: str = "") -> str:
        """生成聊天回复

        Args:
            user_input: 用户输入
            context: 对话上下文

        Returns:
            生成的回复文本
        """
        try:
            response = self.llm_client.generate_response(
                user_input=user_input, context=context, system_prompt=self.system_prompt
            )

            logger.debug(f"Generated response for: {user_input[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {e}")
            # 返回错误回复
            return f"抱歉，我遇到了一些技术问题，无法正常回复。错误信息：{str(e)[:100]}"

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Pipeline 调用接口

        Args:
            data: 输入数据，包含 user_input 和 formatted_context

        Returns:
            添加了 llm_response 的数据字典
        """
        # 如果用户选择退出，直接返回
        if data.get("exit", False):
            data["llm_response"] = ""
            return data

        user_input = data.get("user_input", "")
        context = data.get("formatted_context", "")

        if not user_input:
            data["llm_response"] = ""
            return data

        # 生成回复
        response = self.generate_response(user_input, context)

        # 添加到数据中
        data["llm_response"] = response
        data["response_role"] = "assistant"
        data["response_timestamp"] = data.get("timestamp")  # 使用相同时间戳

        return data
