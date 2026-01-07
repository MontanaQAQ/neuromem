"""基于 STM 的短期记忆 Pipeline

为 sage_chat 提供记忆管理功能，只暴露 send() 和 get() 两个接口
"""

from __future__ import annotations

import queue
import threading

from sage.common.core import BatchFunction, MapFunction, SinkFunction
from sage.common.utils.logging.custom_logger import CustomLogger
from sage.kernel.api.local_environment import LocalEnvironment

# ============================================================================
# Source 算子
# ============================================================================


class ChatSource(BatchFunction):
    """聊天数据源 - 从内部队列读取用户消息"""

    def __init__(self, input_queue: queue.Queue, stop_event: threading.Event):
        """初始化

        Args:
            input_queue: 输入消息队列（由 STMPipeline 传入）
            stop_event: 停止信号（由 STMPipeline 传入）
        """
        super().__init__()
        self.input_queue = input_queue
        self.stop_event = stop_event

    def execute(self):
        """从队列获取消息

        Returns:
            dict: 消息数据 {"user_input": str, "turn": int, "timestamp": float}
            None: 停止信号
        """
        if self.stop_event.is_set():
            return None

        try:
            # 阻塞等待消息（不设置超时，一直等待）
            message = self.input_queue.get()
            if message is None:  # 停止信号
                return None
            return message
        except Exception:
            return None


# ============================================================================
# Map 算子
# ============================================================================


class ChatProcess(MapFunction):
    """聊天处理算子 - 负责记忆插入、检索和回复生成"""

    def __init__(self, service_name: str, config: dict = None):
        """初始化

        Args:
            service_name: 记忆服务名称（由 STMPipeline 传入）
            config: 配置参数
        """
        super().__init__()
        self.service_name = service_name
        self.config = config or {}

        # 从配置中读取参数
        self.max_history = self.config.get("max_history", 5)
        self.use_llm = self.config.get("use_llm", False)

        # LLM 配置（如果启用）
        if self.use_llm:
            self.api_key = self.config.get("api_key", "dummy-key")
            self.base_url = self.config.get("base_url", "http://localhost:8000/v1")
            self.model_name = self.config.get("model_name", "gpt-3.5-turbo")
            self.max_tokens = self.config.get("max_tokens", 256)
            self.temperature = self.config.get("temperature", 0.7)

    def execute(self, data: dict) -> dict:
        """处理用户消息

        流程：
        1. 从记忆中检索相关历史对话
        2. 构建上下文并调用 LLM 生成回复（或使用模拟回复）
        3. 将用户消息和助手回复插入记忆系统

        Args:
            data: 来自 ChatSource 的消息
                {
                    "user_input": str,
                    "turn": int,
                    "timestamp": float
                }

        Returns:
            dict: 处理结果
                {
                    "user_input": str,
                    "turn": int,
                    "assistant_reply": str,
                    "retrieval_count": int,
                    "retrieval_results": list
                }
        """
        try:
            user_input = data["user_input"]
            turn = data["turn"]

            # 步骤1：记忆检索
            retrieval_results = self._retrieve_memory(user_input)
            retrieval_count = len(retrieval_results)

            # 步骤2：生成回复
            assistant_reply = self._generate_reply(user_input, retrieval_results)

            # 步骤3：记忆插入（用户消息 + 助手回复）
            self._insert_memory(user_input, assistant_reply, turn)

            return {
                "user_input": user_input,
                "turn": turn,
                "assistant_reply": assistant_reply,
                "retrieval_count": retrieval_count,
                "retrieval_results": retrieval_results,
            }
        except Exception as e:
            # 返回错误结果而不是抛出异常，确保 pipeline 能继续运行
            return {
                "user_input": data.get("user_input", ""),
                "turn": data.get("turn", 0),
                "assistant_reply": f"[错误] {str(e)}",
                "retrieval_count": 0,
                "retrieval_results": [],
            }

    def _retrieve_memory(self, query: str) -> list[dict]:
        """从记忆服务中检索相关对话

        Args:
            query: 查询文本（用户输入）

        Returns:
            list[dict]: 检索结果列表
        """
        try:
            # 调用记忆服务的 retrieve 方法
            results = self.call_service(
                self.service_name,
                method="retrieve",
                query=query,
                top_k=self.max_history,
                timeout=5.0,
            )
            return results if results else []
        except Exception as e:
            print(f"⚠️ 记忆检索失败: {e}")
            return []

    def _generate_reply(self, user_input: str, history: list[dict]) -> str:
        """生成助手回复

        Args:
            user_input: 用户输入
            history: 检索到的历史对话

        Returns:
            str: 助手回复
        """
        if not self.use_llm:
            # 模拟回复模式
            return f"[模拟回复] 收到: {user_input}"

        # LLM 回复模式
        try:
            # 构建 messages（使用标准格式）
            messages = [
                {
                    "role": "system",
                    "content": "你是一个善解人意的聊天助手。请根据历史对话上下文，自然地回应用户的问题。回答要简洁、贴心，不要生硬地列条目。",
                }
            ]

            # 添加历史对话（从 text 字段解析出角色和内容）
            for item in history:
                text = item.get("text", "")
                # 解析格式：[第N轮] 用户: xxx 或 [第N轮] 助手: xxx
                if "用户:" in text:
                    content = text.split("用户:", 1)[1].strip()
                    messages.append({"role": "user", "content": content})
                elif "助手:" in text:
                    content = text.split("助手:", 1)[1].strip()
                    messages.append({"role": "assistant", "content": content})

            # 添加当前用户输入
            messages.append({"role": "user", "content": user_input})

            # 调用 LLM
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ LLM 调用失败: {e}")
            return f"[模拟回复] 收到: {user_input}"

    def _insert_memory(self, user_input: str, assistant_reply: str, turn: int):
        """插入记忆（用户消息 + 助手回复）

        Args:
            user_input: 用户输入
            assistant_reply: 助手回复
            turn: 对话轮次
        """
        import time

        timestamp = time.time()

        try:
            # 插入用户消息
            self.call_service(
                self.service_name,
                method="insert",
                entry=f"[第{turn}轮] 用户: {user_input}",
                metadata={"turn": turn, "role": "user", "timestamp": timestamp},
                timeout=5.0,
            )

            # 插入助手回复
            self.call_service(
                self.service_name,
                method="insert",
                entry=f"[第{turn}轮] 助手: {assistant_reply}",
                metadata={"turn": turn, "role": "assistant", "timestamp": timestamp},
                timeout=5.0,
            )
        except Exception as e:
            print(f"⚠️ 记忆插入失败: {e}")


# ============================================================================
# Sink 算子
# ============================================================================


class ChatSink(SinkFunction):
    """聊天输出算子 - 将结果放入输出队列"""

    def __init__(self, output_queue: queue.Queue):
        """初始化

        Args:
            output_queue: 输出结果队列（由 STMPipeline 传入）
        """
        super().__init__()
        self.output_queue = output_queue

    def execute(self, data: dict) -> None:
        """将结果放入输出队列

        Args:
            data: 来自 ChatProcess 的处理结果
        """
        self.output_queue.put(data)


# ============================================================================
# Pipeline 封装类
# ============================================================================


class STMPipeline:
    """短期记忆 Pipeline

    对外只暴露 process() 方法
    """

    def __init__(self, config: dict = None):
        """初始化 Pipeline

        Args:
            config: 配置参数
                {
                    "service_type": "partitional.fifo_queue",  # 记忆服务类型
                    "max_size": 5,                             # FIFO队列大小
                    "max_history": 5,                          # 检索历史数量
                    "use_llm": False,                          # 是否使用LLM
                    "api_key": "xxx",                          # LLM API Key
                    "base_url": "xxx",                         # LLM Base URL
                    "model_name": "xxx",                       # LLM 模型名
                    ...
                }
        """
        from sage.neuromem.services import NeuromemServiceFactory

        self.config = config or {}

        # 默认配置
        self.service_type = self.config.get("service_type", "partitional.fifo_queue")
        self.service_name = self.service_type.split(".")[-1]  # "fifo_queue"

        # 内部队列
        self._input_queue = queue.Queue()
        self._output_queue = queue.Queue()
        self._stop_event = threading.Event()

        # 创建 SAGE 环境
        CustomLogger.disable_global_console_debug()
        self.env = LocalEnvironment("stm_chat_pipeline")

        # 注册记忆服务（使用 NeuromemServiceFactory）
        factory = NeuromemServiceFactory.create(self.service_type, self.config)
        self.env.register_service_factory(self.service_name, factory)

        # 构建 Pipeline
        (
            self.env.from_batch(ChatSource, self._input_queue, self._stop_event)
            .map(ChatProcess, self.service_name, self.config)
            .sink(ChatSink, self._output_queue)
        )

        # 启动 Pipeline（submit 后会自动执行）
        self.env.submit(autostop=False)
        print(f"✅ STM Pipeline 已启动 (服务: {self.service_name})")

    def process(self, user_input: str, turn: int) -> dict:
        """处理用户消息（同步接口）

        Args:
            user_input: 用户输入
            turn: 对话轮次

        Returns:
            dict: 处理结果
        """
        import time

        # 发送消息到 Pipeline
        message = {
            "user_input": user_input,
            "turn": turn,
            "timestamp": time.time(),
        }
        self._input_queue.put(message)

        # 获取处理结果（超时 30 秒，LLM 调用可能较慢）
        try:
            return self._output_queue.get(timeout=30.0)
        except queue.Empty:
            raise TimeoutError("Pipeline 处理超时（30秒）") from None

    def close(self):
        """关闭 Pipeline"""
        self._stop_event.set()
        self._input_queue.put(None)  # 发送停止信号
        print("🛑 STM Pipeline 已关闭")
