"""
FIFOQueueService - FIFO 队列记忆服务

使用场景:
- 对话历史（保留最近 N 轮对话）
- 实时日志记录
- 滑动窗口缓存

设计:
- 索引: FIFO队列索引（固定容量）
- 特点: 自动淘汰最老的数据
- 简单高效，无需向量计算
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    from ...memory_collection import UnifiedCollection

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("fifo_queue")
class FIFOQueueService(BaseMemoryService):
    """
    FIFO 队列记忆服务

    特性:
    - 固定容量，先进先出（FIFO）
    - 插入时自动淘汰最老的数据
    - 按时间顺序返回最近的数据

    配置参数:
        max_size: 队列最大容量（默认 10）

    使用示例:
        >>> service = FIFOQueueService(collection, {"max_size": 20})
        >>> service.insert("对话内容1")
        >>> service.insert("对话内容2")
        >>> results = service.retrieve("", top_k=5)  # 返回最近5条
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化 FIFO 队列服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - max_size: 队列最大容量（默认 10）
        """
        # 设置默认配置
        default_config = {"max_size": 100}
        merged_config = {**default_config, **(config or {})}
        super().__init__(collection, merged_config)

    def _setup_indexes(self) -> None:
        """
        配置 FIFO 队列索引

        创建一个固定容量的 FIFO 队列索引，
        当队列满时自动淘汰最旧的数据。
        """
        max_size = self.config.get("max_size", 10)

        self.collection.add_index(
            name="fifo_queue",
            index_type="fifo",
            config={"max_size": max_size},
        )

        self.logger.info(f"Created FIFO queue index with max_size={max_size}")

    def insert(
        self,
        entry: str,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict | None = None,
    ) -> str:
        """
        插入数据到 FIFO 队列（统一旧Service接口）

        Args:
            entry: 对话文本字符串（旧接口参数名）
            vector: embedding 向量（可选，neuromem暂不使用）
            metadata: 元数据字典（可选）
            insert_mode: 插入模式 ("active" | "passive"，neuromem暂不区分）
            insert_params: 主动插入参数（可选，neuromem暂不使用）

        Returns:
            data_id: 生成的数据 ID

        Note:
            - 如果队列已满，最旧的数据会被自动淘汰
            - 数据 ID 基于内容生成（SHA256）
        """
        # 插入数据，指定加入 fifo_queue 索引
        data_id = self.collection.insert(text=entry, metadata=metadata, index_names=["fifo_queue"])

        self.logger.debug(f"Inserted {data_id[:8]}... to FIFO queue")
        return data_id

    def retrieve(
        self,
        query: str | None = None,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 5,
        hints: dict[str, Any] | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索最近的数据

        Args:
            query: 查询文本（FIFO队列不使用，可传None）
            vector: 查询向量（FIFO队列不使用）
            metadata: 元数据过滤条件（可选）
            top_k: 返回的数据条数（默认5）
            hints: 检索策略提示（可选，暂不使用）
            threshold: 相似度阈值（可选，FIFO队列不使用）
            **kwargs: 保留参数

        Returns:
            结果列表: [{"id": "...", "text": "...", "metadata": {...}, "score": 1.0}, ...]
                按时间倒序（最新的在前）

        Note:
            - FIFO队列按插入时间排序
            - score固定为1.0（无相似度计算）
            - vector/threshold参数被忽略
        """
        # 从 FIFO 队列索引查询（返回 data_id 列表）
        data_ids = self.collection.query_by_index(index_name="fifo_queue", query=None, top_k=top_k)

        # 获取完整数据
        results = []
        for data_id in data_ids:
            item = self.collection.get(data_id)
            if item:
                results.append(
                    {
                        "id": data_id,
                        "text": item["text"],
                        "metadata": item.get("metadata", {}),
                        "score": 1.0,  # FIFO 无相似度概念
                    }
                )

        # 应用元数据过滤（如果提供）
        filters = kwargs.get("filters")
        if filters:
            results = self._filter_by_metadata(results, filters)

        self.logger.debug(f"Retrieved {len(results)} items from FIFO queue")
        return results

    def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取最近的 N 条数据（便捷方法）

        Args:
            limit: 返回的数据条数

        Returns:
            结果列表（按时间倒序）

        Example:
            >>> recent_conversations = service.get_recent(5)
        """
        return self.retrieve(query="", top_k=limit)

    def clear(self) -> int:
        """
        清空队列（保留索引结构）

        Returns:
            清空的数据条数

        Warning:
            此操作不可逆
        """
        # 获取所有数据 ID
        all_ids = self.collection.query_by_index(index_name="fifo_queue", query=None, top_k=10000)

        # 逐个删除
        count = 0
        for data_id in all_ids:
            if self.delete(data_id):
                count += 1

        self.logger.info(f"Cleared {count} items from FIFO queue")
        return count
