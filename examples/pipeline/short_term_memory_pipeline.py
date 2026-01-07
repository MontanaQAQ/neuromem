"""STM Pipeline 模块

专门处理记忆检索、LLM生成、记忆存储的Pipeline逻辑
"""

from __future__ import annotations

from typing import Any

from openai import OpenAI
from sage.common.core import BatchFunction, MapFunction, SinkFunction
from sage.kernel.api.local_environment import LocalEnvironment

from sage.neuromem.services import NeuromemServiceFactory

# ========== 配置参数 ==========

SERVICES_TYPE = "partitional.fifo_queue"
FIFO_MAX_SIZE = 5
RETRIEVAL_TOP_K = 3  # 减少检索数量，避免过多历史影响当前回复

LLM_API_KEY = "iloveshuhao"
LLM_BASE_URL = "http://172.17.0.1:1040/v1"
LLM_MODEL = "pangu_embedded_1b"


# ========== Pipeline 算子定义 ==========


class DataSource(BatchFunction):
    """数据源 - 处理外部输入的数据"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.data_queue = []

    def set_data(self, data):
        """设置要处理的数据"""
        self.data_queue = [data] if data else []

    def execute(self):
        """返回队列中的数据"""
        if self.data_queue:
            return self.data_queue.pop(0)
        return None


class STMProcessor(MapFunction):
    """STM 处理器 - 检索→生成→存储"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.service_name = SERVICES_TYPE.split(".")[-1]
        self.llm_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """处理数据"""
        turn = data["turn"]
        user_input = data["user_input"]

        # 1. 检索历史记忆
        retrieved = self.call_service(
            self.service_name, method="retrieve", query=user_input, top_k=RETRIEVAL_TOP_K
        )
        retrieval_count = len(retrieved) if retrieved else 0

        # 2. 构建 LLM 上下文
        messages = []
        if retrieved:
            for item in retrieved:
                entry_text = item.get("entry", "")
                metadata = item.get("metadata", {})
                role = metadata.get("role", "user")
                messages.append({"role": role, "content": entry_text})

        messages.append({"role": "user", "content": user_input})

        # 3. 调用 LLM 生成回复
        try:
            response = self.llm_client.chat.completions.create(
                model=LLM_MODEL, messages=messages, max_tokens=256, temperature=0.7
            )
            assistant_reply = response.choices[0].message.content
        except Exception as e:
            assistant_reply = f"[LLM 错误: {e}]"

        # 4. 存储用户输入和助手回复
        self.call_service(
            self.service_name,
            method="insert",
            entry=user_input,
            metadata={"turn": turn, "role": "user"},
        )

        self.call_service(
            self.service_name,
            method="insert",
            entry=assistant_reply,
            metadata={"turn": turn, "role": "assistant"},
        )

        # 返回结果
        return {
            "turn": turn,
            "user_input": user_input,
            "assistant_reply": assistant_reply,
            "retrieval_count": retrieval_count,
        }


class ResultCollector(SinkFunction):
    """结果收集器"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.results = []

    def execute(self, data: dict[str, Any]) -> None:
        """收集结果"""
        self.results.append(data)


# ========== STM Pipeline 类 ==========


class STMPipeline:
    """STM Pipeline 封装类 - 简化版本"""

    def __init__(self):
        self.service = None
        self.llm_client = None
        self._setup()

    def _setup(self):
        """初始化服务"""
        # 创建环境（仅用于服务注册）
        env = LocalEnvironment("stm_pipeline")

        # 创建配置
        config = {
            "services": {"services_type": SERVICES_TYPE, "fifo_queue": {"max_size": FIFO_MAX_SIZE}}
        }

        # 创建并注册 STM 服务
        factory = NeuromemServiceFactory.create(SERVICES_TYPE, config)
        service_name = SERVICES_TYPE.split(".")[-1]
        env.register_service_factory(service_name, factory)

        # 直接创建服务实例
        self.service = factory.service_class()
        self.service.setup()

        # 初始化 LLM 客户端
        self.llm_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    def process(self, user_input: str, turn: int) -> dict[str, Any]:
        """处理单轮对话 - 直接调用服务，不用Pipeline

        Args:
            user_input: 用户输入
            turn: 对话轮次

        Returns:
            处理结果字典
        """
        try:
            # 1. 检索历史记忆
            retrieved = self.service.retrieve(query=user_input, top_k=RETRIEVAL_TOP_K)
            retrieval_count = len(retrieved) if retrieved else 0

            # DEBUG: 打印检索到的原始数据
            print("\n" + "🔍" * 40)
            print(f"DEBUG - 检索到 {retrieval_count} 条记录:")
            if retrieved:
                for i, item in enumerate(retrieved):
                    print(f"\n--- 记录 {i + 1} ---")
                    print(f"完整数据: {item}")
                    print(f"类型: {type(item)}")
                    if isinstance(item, dict):
                        print(f"  entry: {item.get('entry', 'NOT FOUND')}")
                        print(f"  metadata: {item.get('metadata', 'NOT FOUND')}")
            print("🔍" * 40 + "\n")

            # 2. 构建 LLM 上下文
            messages = []

            # 添加系统提示，强调身份记忆和上下文理解
            messages.append(
                {
                    "role": "system",
                    "content": """你是一个智能AI助手。请仔细阅读对话历史，记住用户的身份信息和之前的对话内容。

重要规则：
1. 如果用户告诉你他们的名字，请记住并在后续对话中使用
2. 当用户问"我是谁？"或类似问题时，应该回答用户的身份，而不是你自己的身份
3. 保持对话的连续性和一致性
4. 不要重复介绍自己，除非用户明确询问你的身份
5. 专注于回答用户的问题，而不是介绍自己

请根据上下文智能回应。""",
                }
            )

            # 按时间顺序添加历史对话（从早到晚）
            if retrieved:
                # 按turn排序，确保对话顺序正确
                sorted_retrieved = sorted(
                    retrieved, key=lambda x: x.get("metadata", {}).get("turn", 0)
                )
                for item in sorted_retrieved:
                    entry_text = item.get("text", "")  # 修复：使用'text'而不是'entry'
                    metadata = item.get("metadata", {})
                    role = metadata.get("role", "user")
                    print(
                        f"DEBUG - 处理记录: role={role}, entry={entry_text[:50] if entry_text else 'EMPTY'}"
                    )
                    if role in ["user", "assistant"] and entry_text.strip():
                        messages.append({"role": role, "content": entry_text})
                        print("  ✓ 已添加到messages")

            messages.append({"role": "user", "content": user_input})

            # DEBUG: 打印发送给LLM的完整消息
            print("\n" + "=" * 80)
            print("🔍 DEBUG: 发送给LLM的消息:")
            print("=" * 80)
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                print(f"\n[消息 {i + 1}] Role: {role}")
                print(
                    f"Content: {content[:200]}..." if len(content) > 200 else f"Content: {content}"
                )
            print("=" * 80 + "\n")

            # 3. 调用 LLM 生成回复
            try:
                response = self.llm_client.chat.completions.create(
                    model=LLM_MODEL, messages=messages, max_tokens=200, temperature=0.3
                )
                assistant_reply = response.choices[0].message.content
            except Exception as e:
                assistant_reply = f"[LLM 错误: {e}]"

            # 4. 存储用户输入和助手回复
            self.service.insert(
                entry=user_input,
                metadata={"turn": turn, "role": "user"},
            )

            self.service.insert(
                entry=assistant_reply,
                metadata={"turn": turn, "role": "assistant"},
            )

            # 返回结果
            return {
                "turn": turn,
                "user_input": user_input,
                "assistant_reply": assistant_reply,
                "retrieval_count": retrieval_count,
            }

        except Exception as e:
            return {
                "turn": turn,
                "user_input": user_input,
                "assistant_reply": f"[处理失败: {e}]",
                "retrieval_count": 0,
            }
