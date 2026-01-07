"""
记忆存储组件

负责将用户输入和 LLM 回复存储到 STM 服务中。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStorage:
    """记忆存储器

    将对话内容存储到 STM 服务中，维护对话历史。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化记忆存储器"""
        self.config = config or {}

        # 存储配置
        self.store_user_messages = self.config.get("store_user_messages", True)
        self.store_assistant_messages = self.config.get("store_assistant_messages", True)

        logger.info("Memory storage initialized")

    def store_message(
        self,
        role: str,
        content: str,
        timestamp: str,
        call_service,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """存储单条消息到 STM

        Args:
            role: 角色 ("user" 或 "assistant")
            content: 消息内容
            timestamp: 时间戳
            call_service: 服务调用函数
            metadata: 额外的元数据

        Returns:
            存储的数据 ID，失败则返回 None
        """
        try:
            # 构造消息文本（包含时间和角色）
            formatted_message = f"[{timestamp}] {role}: {content}"

            # 构造元数据
            message_metadata = {
                "role": role,
                "timestamp": timestamp,
                "content": content,
                **(metadata or {}),
            }

            # 调用 STM 服务存储消息
            data_id = call_service(
                service_name="stm_service",
                method="insert",
                entry=formatted_message,
                metadata=message_metadata,
            )

            logger.debug(f"Stored message: {role} - {content[:50]}...")
            return data_id

        except Exception as e:
            logger.error(f"Failed to store message: {e}")
            return None

    def __call__(self, data: dict[str, Any], call_service) -> dict[str, Any]:
        """Pipeline 调用接口

        Args:
            data: 输入数据，包含用户输入和 LLM 回复
            call_service: 服务调用函数

        Returns:
            添加了存储信息的数据字典
        """
        # 如果用户选择退出，直接返回
        if data.get("exit", False):
            return data

        user_input = data.get("user_input", "")
        llm_response = data.get("llm_response", "")
        timestamp = data.get("timestamp", "")

        stored_ids = []

        # 存储用户消息
        if self.store_user_messages and user_input:
            user_id = self.store_message(
                role="user",
                content=user_input,
                timestamp=timestamp,
                call_service=call_service,
                metadata={"type": "user_input"},
            )
            if user_id:
                stored_ids.append(user_id)

        # 存储助手回复
        if self.store_assistant_messages and llm_response:
            assistant_id = self.store_message(
                role="assistant",
                content=llm_response,
                timestamp=timestamp,
                call_service=call_service,
                metadata={"type": "llm_response"},
            )
            if assistant_id:
                stored_ids.append(assistant_id)

        # 添加存储信息到数据中
        data["stored_ids"] = stored_ids
        data["storage_success"] = len(stored_ids) > 0

        logger.debug(f"Stored {len(stored_ids)} messages to STM")

        return data
