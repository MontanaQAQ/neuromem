"""
基于 SAGE Pipeline 的 STM 聊天机器人

使用 NeuroMem STM 服务和大模型 API，实现记忆增强的聊天机器人。
支持对话历史记忆、上下文检索和智能回复生成。

使用方法：
    python examples/stm_chat_pipeline.py

输入 'exit' 退出聊天。
"""

from __future__ import annotations

import os
import sys

# 使用本地路径导入 - 确保使用项目内的sage包
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 移除可能冲突的外部sage路径
sage_paths = [
    p for p in sys.path if "sage-middleware" in p or "sage-common" in p or "sage-kernel" in p
]
for p in sage_paths:
    if p in sys.path:
        sys.path.remove(p)

from typing import Any  # noqa: E402

from sage.neuromem.chat import (  # noqa: E402
    ChatInput,
    ChatOutput,
    LLMGenerator,
    MemoryRetriever,
    MemoryStorage,
)
from sage.neuromem.services import NeuromemServiceFactory  # noqa: E402

# ========== 配置参数 ==========

# 聊天配置
CHAT_CONFIG = {
    "user_prompt": "🧠 用户: ",
    "bot_prompt": "🤖 助手: ",
    "welcome_message": (
        "🤖 欢迎使用 NeuroMem STM 聊天机器人！\\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        "✨ 基于短期记忆系统，我会记住我们的对话内容\\n"
        "🔧 输入 'exit' 退出聊天\\n"
        "📊 输入 '状态' 查看记忆状态\\n"
        "💡 输入 '帮助' 查看使用说明\\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
    ),
    "goodbye_message": "👋 再见！感谢使用 NeuroMem STM 聊天机器人。",
    "exit_commands": ["exit", "quit", "bye", "退出", "再见"],
    "show_timestamps": False,
    "show_memory_status": False,
}

# STM 服务配置
STM_CONFIG = {
    "services_type": "partitional.fifo_queue",
    "fifo_queue": {
        "max_size": 20,  # 保留最近 20 条对话
    },
}

# 记忆检索配置
RETRIEVAL_CONFIG = {
    "retrieval_top_k": 8,  # 检索最近 8 条对话作为上下文
    "include_metadata": True,
}

# LLM 配置
LLM_CONFIG = {
    # 使用 Mock 模式进行测试（不需要真实的 API）
    "use_mock_llm": True,
    # 真实 LLM 配置（取消注释并填入真实配置来使用）
    # "use_mock_llm": False,
    # "api_key": "your-api-key-here",
    # "base_url": "https://api.openai.com",
    # "model_name": "gpt-3.5-turbo",
    # "max_tokens": 256,
    # "temperature": 0.7,
    # "timeout": 30.0,
    "system_prompt": (
        "你是一个智能的AI助手，基于NeuroMem短期记忆系统。"
        "请根据用户输入和之前的对话历史，提供有用、准确、友好的回复。"
        "保持回复简洁明了，展现出你能记住对话历史的能力。"
    ),
}

# 记忆存储配置
STORAGE_CONFIG = {
    "store_user_messages": True,
    "store_assistant_messages": True,
}

# 输出配置
OUTPUT_CONFIG = {
    **CHAT_CONFIG,
    "stm_max_size": STM_CONFIG["fifo_queue"]["max_size"],
}


class STMChatPipeline:
    """基于 Pipeline 的 STM 聊天机器人"""

    def __init__(self):
        """初始化聊天 Pipeline"""
        # 创建 Pipeline 组件
        self.chat_input = ChatInput(CHAT_CONFIG)
        self.memory_retriever = MemoryRetriever(RETRIEVAL_CONFIG)
        self.llm_generator = LLMGenerator(LLM_CONFIG)
        self.memory_storage = MemoryStorage(STORAGE_CONFIG)
        self.chat_output = ChatOutput(OUTPUT_CONFIG)

        # 创建 STM 服务（简化版，不使用完整的 LocalEnvironment）
        self.stm_service = self._create_stm_service()

        print("🔧 STM 聊天机器人 Pipeline 初始化完成！")
        print(f"📝 STM 容量: {STM_CONFIG['fifo_queue']['max_size']} 条对话")
        print(f"🔍 上下文检索: {RETRIEVAL_CONFIG['retrieval_top_k']} 条")
        print(f"🤖 LLM 模式: {'Mock' if LLM_CONFIG['use_mock_llm'] else 'Real API'}")

    def _create_stm_service(self):
        """创建 STM 服务（简化版）"""
        try:
            # 使用 NeuromemServiceFactory 创建服务
            factory = NeuromemServiceFactory.create(
                STM_CONFIG["services_type"], {"fifo_queue": STM_CONFIG["fifo_queue"]}
            )

            # 创建服务实例
            service_instance = factory.service_class()
            service_instance.setup()

            return service_instance

        except Exception as e:
            print(f"❌ 创建 STM 服务失败: {e}")
            raise

    def call_service(self, service_name: str, method: str, **kwargs) -> Any:
        """服务调用接口

        Args:
            service_name: 服务名称（目前只支持 'stm_service'）
            method: 调用方法
            **kwargs: 方法参数

        Returns:
            服务调用结果
        """
        if service_name != "stm_service":
            raise ValueError(f"Unknown service: {service_name}")

        if not hasattr(self.stm_service, method):
            raise ValueError(f"STM service does not have method: {method}")

        service_method = getattr(self.stm_service, method)
        return service_method(**kwargs)

    def process_chat_turn(self) -> bool:
        """处理一轮聊天对话

        Returns:
            是否继续聊天（False 表示用户选择退出）
        """
        try:
            # Step 1: 获取用户输入
            data = {}
            data = self.chat_input(data)

            # 检查是否退出
            if data.get("exit", False):
                self.chat_output(data)
                return False

            # Step 2: 检索记忆上下文
            data = self.memory_retriever(data, self.call_service)

            # Step 3: 生成 LLM 回复
            data = self.llm_generator(data)

            # Step 4: 存储到记忆
            data = self.memory_storage(data, self.call_service)

            # Step 5: 输出回复
            data = self.chat_output(data, self.call_service)

            return True

        except KeyboardInterrupt:
            print("\\n👋 用户中断，退出聊天。")
            return False
        except Exception as e:
            print(f"❌ 处理聊天时发生错误: {e}")
            print("🔄 请重试或输入 'exit' 退出。")
            return True  # 继续聊天

    def run(self):
        """运行聊天循环"""
        # 显示欢迎信息
        self.chat_output.display_welcome()

        # 聊天循环
        while True:
            if not self.process_chat_turn():
                break

    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self.stm_service, "teardown"):
                self.stm_service.teardown()
        except Exception as e:
            print(f"⚠️  清理资源时出错: {e}")


def main():
    """主函数"""
    try:
        # 创建并运行聊天机器人
        chatbot = STMChatPipeline()
        chatbot.run()
        chatbot.cleanup()

    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
