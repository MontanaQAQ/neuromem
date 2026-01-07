"""
聊天输出组件

负责显示聊天回复和管理聊天界面。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ChatOutput:
    """聊天输出处理器

    负责显示 LLM 回复和聊天状态信息。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化聊天输出处理器"""
        self.config = config or {}

        # 输出配置
        self.bot_prompt = self.config.get("bot_prompt", "助手: ")
        self.show_timestamps = self.config.get("show_timestamps", False)
        self.show_memory_status = self.config.get("show_memory_status", False)

        logger.info("Chat output initialized")

    def display_response(self, response: str, timestamp: str = "") -> None:
        """显示助手回复

        Args:
            response: 回复内容
            timestamp: 时间戳（可选）
        """
        if self.show_timestamps and timestamp:
            print(f"{self.bot_prompt}[{timestamp}] {response}")
        else:
            print(f"{self.bot_prompt}{response}")

    def display_memory_status(self, call_service, stm_max_size: int = 10) -> None:
        """显示记忆状态

        Args:
            call_service: 服务调用函数
            stm_max_size: STM 最大容量
        """
        try:
            # 获取最近的记忆
            recent_memory = call_service(
                service_name="stm_service", method="get_recent", limit=stm_max_size
            )

            memory_count = len(recent_memory)

            print("\\n--- 记忆状态 ---")
            print(f"当前记忆条数: {memory_count}/{stm_max_size}")

            if memory_count > 0:
                print("最近的对话:")
                # 显示最近3条对话
                for i, item in enumerate(reversed(recent_memory[-3:]), 1):
                    text = item.get("text", "")
                    print(f"  {i}. {text}")

            print("--- 记忆状态 ---\\n")

        except Exception as e:
            logger.error(f"Failed to display memory status: {e}")
            print(f"\\n无法获取记忆状态: {e}\\n")

    def display_welcome(self) -> None:
        """显示欢迎信息"""
        welcome_message = self.config.get(
            "welcome_message",
            "🤖 欢迎使用 NeuroMem STM 聊天机器人！\\n"
            "基于短期记忆系统，我会记住我们的对话内容。\\n"
            "输入 'exit' 退出聊天，输入 '状态' 查看记忆状态。\\n",
        )
        print(welcome_message)

    def display_goodbye(self) -> None:
        """显示告别信息"""
        goodbye_message = self.config.get(
            "goodbye_message", "👋 再见！感谢使用 NeuroMem STM 聊天机器人。"
        )
        print(goodbye_message)

    def display_error(self, error_message: str) -> None:
        """显示错误信息

        Args:
            error_message: 错误信息
        """
        print(f"❌ 错误: {error_message}")

    def __call__(self, data: dict[str, Any], call_service=None) -> dict[str, Any]:
        """Pipeline 调用接口

        Args:
            data: 输入数据，包含 LLM 回复等信息
            call_service: 服务调用函数（可选，用于显示状态）

        Returns:
            处理后的数据字典
        """
        # 如果用户选择退出
        if data.get("exit", False):
            self.display_goodbye()
            return data

        # 显示 LLM 回复
        llm_response = data.get("llm_response", "")
        timestamp = data.get("response_timestamp", "")

        if llm_response:
            self.display_response(llm_response, timestamp)

        # 检查是否需要显示记忆状态
        user_input = data.get("user_input", "").lower()
        if ("状态" in user_input or "status" in user_input) and call_service:
            stm_max_size = self.config.get("stm_max_size", 10)
            self.display_memory_status(call_service, stm_max_size)

        # 检查存储状态
        if not data.get("storage_success", True):
            logger.warning("Some messages failed to store in STM")

        return data
