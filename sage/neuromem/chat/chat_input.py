"""
聊天输入处理组件

负责获取用户输入并初始化聊天数据结构。
"""

from __future__ import annotations

import datetime
from typing import Any


class ChatInput:
    """聊天输入处理器

    处理用户输入，包装成标准的聊天数据格式。
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化聊天输入处理器"""
        self.config = config or {}

        # 聊天配置
        self.user_prompt = self.config.get("user_prompt", "用户: ")
        self.exit_commands = self.config.get("exit_commands", ["exit", "quit", "bye", "退出"])

    def get_user_input(self) -> str | None:
        """获取用户输入

        Returns:
            用户输入的文本，如果是退出命令则返回 None
        """
        try:
            user_input = input(self.user_prompt).strip()

            # 检查退出命令
            if user_input.lower() in self.exit_commands:
                return None

            return user_input if user_input else ""

        except (KeyboardInterrupt, EOFError):
            return None

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Pipeline 调用接口

        Args:
            data: 输入数据（通常为空或包含会话信息）

        Returns:
            包含用户输入的数据字典
        """
        # 获取用户输入
        user_input = self.get_user_input()

        if user_input is None:
            # 用户选择退出
            data["exit"] = True
            data["user_input"] = ""
        else:
            data["exit"] = False
            data["user_input"] = user_input
            data["timestamp"] = datetime.datetime.now(tz=datetime.timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            data["role"] = "user"

        return data
