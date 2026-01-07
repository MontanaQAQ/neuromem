"""
记忆检索组件

负责从 STM 服务中检索相关的对话历史，作为生成回复的上下文。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryRetriever:
    """记忆检索器

    从 STM 服务检索对话历史，提供给 LLM 作为上下文。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化记忆检索器"""
        self.config = config or {}

        # 检索配置
        self.top_k = self.config.get("retrieval_top_k", 5)
        self.include_metadata = self.config.get("include_metadata", True)

        # STM 服务将在运行时通过 call_service 获取
        logger.info(f"Memory retriever initialized with top_k={self.top_k}")

    def retrieve_context(self, user_input: str, call_service) -> list[dict[str, Any]]:
        """检索对话上下文

        Args:
            user_input: 用户输入
            call_service: 服务调用函数

        Returns:
            检索到的对话历史
        """
        try:
            # 调用 STM 服务检索相关对话
            context = call_service(
                service_name="stm_service", method="retrieve", query=user_input, top_k=self.top_k
            )

            logger.debug(f"Retrieved {len(context)} context items from STM")
            return context

        except Exception as e:
            logger.error(f"Failed to retrieve memory context: {e}")
            return []

    def format_context(self, context: list[dict[str, Any]]) -> str:
        """格式化上下文为文本

        Args:
            context: 检索到的对话上下文

        Returns:
            格式化后的上下文字符串
        """
        if not context:
            return ""

        context_lines = []
        # FIFO 返回的是按时间倒序（最新在前），我们需要正序显示
        for item in reversed(context):
            text = item.get("text", "")
            if text:
                context_lines.append(text)

        return "\\n".join(context_lines)

    def __call__(self, data: dict[str, Any], call_service) -> dict[str, Any]:
        """Pipeline 调用接口

        Args:
            data: 输入数据，包含 user_input
            call_service: 服务调用函数

        Returns:
            添加了 context 信息的数据字典
        """
        # 如果用户选择退出，直接返回
        if data.get("exit", False):
            return data

        user_input = data.get("user_input", "")
        if not user_input:
            data["context"] = ""
            data["formatted_context"] = ""
            return data

        # 检索对话上下文
        context = self.retrieve_context(user_input, call_service)
        formatted_context = self.format_context(context)

        # 添加到数据中
        data["context"] = context
        data["formatted_context"] = formatted_context

        logger.debug(f"Context retrieved for: {user_input[:50]}...")

        return data
