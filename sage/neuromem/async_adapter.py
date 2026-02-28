"""AsyncMemoryAdapter — neuromem 异步包装层

将 MemoryManager / UnifiedCollection 的同步操作包装为 asyncio 友好的调用，
适用于 asyncio 主循环（如 VidaAgent）中非阻塞地操作记忆。

设计原则：
- 不修改任何同步接口（零破坏性变更）
- 使用 ``asyncio.get_event_loop().run_in_executor`` 将阻塞调用转移到线程池
- 模块级共享 ThreadPoolExecutor，避免重复创建销毁线程池的开销

典型用法：
    >>> from sage.neuromem import AsyncMemoryAdapter, MemoryManager, UnifiedCollection
    >>> manager = MemoryManager()
    >>> collection = manager.create_collection("my_data")
    >>> adapter = AsyncMemoryAdapter(collection)
    >>> # 在 async 函数中：
    >>> data_id = await adapter.insert("Hello, world!", {"source": "agent"})
    >>> results = await adapter.retrieve("default_index", "Hello")
    >>> await adapter.persist(manager, "my_data")
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .memory_manager import MemoryManager
    from .memory_collection import UnifiedCollection

# 模块级共享线程池（max_workers 可通过环境变量调整，默认 4）
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="neuromem")


class AsyncMemoryAdapter:
    """将 neuromem 同步操作包装为 asyncio 友好的调用。

    使用 ``run_in_executor`` 将阻塞的 UnifiedCollection 操作转移到线程池，
    使 asyncio 事件循环在等待期间可以执行其他协程。

    属性：
        collection: 被包装的 UnifiedCollection 实例

    示例：
        >>> adapter = AsyncMemoryAdapter(collection)
        >>> data_id = await adapter.insert("text content", {"key": "value"})
        >>> results = await adapter.retrieve("my_index", "query text", top_k=5)
        >>> await adapter.persist(manager, "collection_name")
    """

    def __init__(self, collection: UnifiedCollection) -> None:
        """初始化 AsyncMemoryAdapter。

        Args:
            collection: 要包装的 UnifiedCollection 实例。
        """
        self.collection = collection

    async def insert(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        index_names: list[str] | None = None,
    ) -> str:
        """异步插入数据到 Collection。

        在线程池中调用 ``UnifiedCollection.insert()``，不阻塞事件循环。

        Args:
            text: 原始文本内容。
            metadata: 可选的元数据字典。
            index_names: 要加入的索引列表（``None`` 表示加入所有索引）。

        Returns:
            data_id: 生成的数据 ID（基于内容的 SHA256 哈希）。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.collection.insert(text, metadata, index_names),
        )

    async def insert_batch(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        index_names: list[str] | None = None,
    ) -> list[str]:
        """异步批量插入数据到 Collection。

        在线程池中调用 ``UnifiedCollection.insert_batch()``，不阻塞事件循环。

        Args:
            texts: 文本列表。
            metadatas: 元数据列表（可选）。
            index_names: 要加入的索引列表（``None`` 表示加入所有索引）。

        Returns:
            data_ids: 生成的数据 ID 列表。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.collection.insert_batch(texts, metadatas, index_names),
        )

    async def retrieve(
        self,
        index_name: str,
        query: Any,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """异步检索完整数据。

        在线程池中调用 ``UnifiedCollection.retrieve()``，不阻塞事件循环。

        Args:
            index_name: 索引名称。
            query: 查询内容（文本、向量等，取决于索引类型）。
            **params: 传递给底层索引的额外查询参数（如 ``top_k``）。

        Returns:
            匹配的完整数据列表，每项格式为
            ``{id, text, metadata, created_at}``。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: self.collection.retrieve(index_name, query, **params),
        )

    async def persist(self, manager: MemoryManager, name: str) -> bool:
        """异步持久化 Collection 到磁盘。

        在线程池中调用 ``MemoryManager.persist()``，不阻塞事件循环。

        Args:
            manager: 拥有该 Collection 的 MemoryManager 实例。
            name: Collection 名称。

        Returns:
            是否持久化成功。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            lambda: manager.persist(name),
        )

    @staticmethod
    def get_executor() -> ThreadPoolExecutor:
        """返回模块级共享线程池实例（用于测试或自定义调优）。

        Returns:
            全局共享的 ThreadPoolExecutor 实例。
        """
        return _executor
