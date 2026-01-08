# file: sage.middleware.services.neuromem./memory_collection/base_collection.py
# python -m sage.core.sage.middleware.services.neuromem.memory_collection.base_collection
"""
NeuroMem Collection 基类定义。

设计原则：
- Collection 持有数据（text_storage + metadata_storage）
- Collection 可以在数据上建立多种类型的索引（VDB、KV、Graph）
- 每种 Collection 类型支持不同的 IndexType
- Service : Collection = 1 : 1
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np

from ..storage_engine.metadata_storage import MetadataStorage
from ..storage_engine.text_storage import TextStorage

if TYPE_CHECKING:
    pass


class IndexType(Enum):
    """
    索引类型枚举。

    VDB: 向量索引（FAISS 等）
    KV: 文本/KV 索引（BM25、FIFO、排序等）
    GRAPH: 图索引（邻接表、知识图谱等）
    """

    VDB = "vdb"
    KV = "kv"
    GRAPH = "graph"


class BaseMemoryCollection(ABC):
    """
    NeuroMem Collection 基类。

    设计原则：
    - Collection 持有数据（text + metadata）
    - Collection 可以在数据上建立多个索引
    - 每种 Collection 类型可支持不同的 IndexType

    子类必须实现所有抽象方法，并声明 supported_index_types。
    """

    # 子类声明支持的索引类型
    supported_index_types: ClassVar[set[IndexType]] = set()

    def __init__(self, config: dict[str, Any]):
        """
        统一使用 dict 配置初始化。

        Args:
            config: 配置字典，必须包含 "name" 字段
        """
        import warnings

        warnings.warn(
            "BaseMemoryCollection is deprecated and will be removed in v0.3.0.0. "
            "Use UnifiedCollection instead. See docs/dev-note/MIGRATION_GUIDE.md",
            DeprecationWarning,
            stacklevel=2,
        )
        self.name = config["name"]
        self.text_storage = TextStorage()
        self.metadata_storage = MetadataStorage()

    def _get_stable_id(self, raw_text: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Generate stable ID from raw text and optional metadata using SHA256.
        使用 SHA256 生成稳定的文本 ID。

        Args:
            raw_text: 原始文本内容
            metadata: 可选的元数据（用于区分相同文本不同元数据的情况）

        Returns:
            稳定的 ID 字符串
        """
        import json

        key = raw_text
        if metadata:
            key += json.dumps(metadata, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def filter_ids(
        self,
        ids: list[str],
        metadata_filter_func: Callable[[dict[str, Any]], bool] | None = None,
        **metadata_conditions: Any,
    ) -> list[str]:
        """
        Filter given IDs based on metadata filter function or exact match conditions.
        基于元数据过滤函数或条件筛选给定ID列表中的条目。

        Args:
            ids: 要过滤的 ID 列表
            metadata_filter_func: 元数据过滤函数，接收 metadata dict，返回 bool
            **metadata_conditions: 精确匹配条件

        Returns:
            匹配的 ID 列表
        """
        matched_ids = []

        for item_id in ids:
            metadata = self.metadata_storage.get(item_id)

            if metadata_filter_func:
                if metadata_filter_func(metadata):
                    matched_ids.append(item_id)
            else:
                if all(metadata.get(k) == v for k, v in metadata_conditions.items()):
                    matched_ids.append(item_id)

        return matched_ids

    def get_all_ids(self) -> list[str]:
        """
        Get all stored item IDs.
        获取所有存储的条目ID。
        """
        return self.text_storage.get_all_ids()

    def add_metadata_field(self, field_name: str) -> None:
        """
        Register a metadata field.
        注册一个元数据字段。
        """
        self.metadata_storage.add_field(field_name)

    def get_text(self, item_id: str) -> str | None:
        """
        Get text content by ID.
        根据 ID 获取文本内容。
        """
        return self.text_storage.get(item_id)

    def get_metadata(self, item_id: str) -> dict[str, Any] | None:
        """
        Get metadata by ID.
        根据 ID 获取元数据。
        """
        return self.metadata_storage.get(item_id)

    def has_item(self, item_id: str) -> bool:
        """
        Check if an item exists.
        检查条目是否存在。
        """
        return self.text_storage.has(item_id)

    # ==================== 抽象方法：索引管理 ====================

    @abstractmethod
    def create_index(
        self,
        config: dict[str, Any],
        index_type: IndexType | None = None,
    ) -> bool:
        """
        创建索引。

        Args:
            config: 索引配置，必须包含 "name" 字段
            index_type: 索引类型（基础 Collection 可忽略，HybridCollection 必需）

        Returns:
            是否创建成功
        """
        ...

    @abstractmethod
    def delete_index(self, index_name: str) -> bool:
        """
        删除索引。

        Args:
            index_name: 索引名称

        Returns:
            是否删除成功
        """
        ...

    @abstractmethod
    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引。

        Returns:
            索引信息列表: [{"name": ..., "type": IndexType, "config": {...}}, ...]
        """
        ...

    # ==================== 抽象方法：数据操作 ====================

    @abstractmethod
    def insert(
        self,
        content: str,
        index_names: list[str] | str | None = None,
        vector: np.ndarray | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        插入数据。

        Args:
            content: 文本内容
            index_names: 目标索引名列表或单个索引名（None 表示只存数据不建索引）
            vector: 向量（VDB 索引需要）
            metadata: 元数据

        Returns:
            stable_id
        """
        ...

    @abstractmethod
    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        将已有数据加入索引（用于跨索引迁移）。

        Args:
            item_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（VDB 索引需要，可以现场计算）

        Returns:
            成功/失败
        """
        ...

    @abstractmethod
    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从索引移除（数据保留）。

        用于 MemoryOS 场景：从 FIFO 索引移除，加入 Segment 索引。

        Args:
            item_id: 数据 ID
            index_name: 索引名称

        Returns:
            成功/失败
        """
        ...

    @abstractmethod
    def retrieve(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        with_metadata: bool = False,
        metadata_filter: Callable[[dict[str, Any]], bool] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索数据。

        Args:
            query: 查询（文本或向量）
            index_name: 使用的索引
            top_k: 返回数量
            with_metadata: 是否返回 metadata
            metadata_filter: 元数据过滤函数

        Returns:
            检索结果列表: [{"id": ..., "text": ..., "metadata": ..., "score": ...}, ...]
        """
        ...

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """
        完全删除（数据 + 所有索引）。

        Args:
            item_id: 条目 ID

        Returns:
            是否删除成功
        """
        ...

    @abstractmethod
    def update(
        self,
        item_id: str,
        new_content: str | None = None,
        new_vector: np.ndarray | None = None,
        new_metadata: dict[str, Any] | None = None,
        index_name: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        更新条目。

        Args:
            item_id: 条目 ID
            new_content: 新文本内容
            new_vector: 新向量
            new_metadata: 新元数据
            index_name: 索引名称

        Returns:
            是否更新成功
        """
        ...

    # ==================== 抽象方法：持久化 ====================

    @abstractmethod
    def store(self, path: str | None = None) -> dict[str, Any]:
        """
        持久化到磁盘。

        Args:
            path: 存储路径（None 使用默认路径）

        Returns:
            存储元信息
        """
        ...

    @classmethod
    @abstractmethod
    def load(cls, name: str, path: str | None = None) -> BaseMemoryCollection:
        """
        从磁盘加载。

        Args:
            name: Collection 名称
            path: 加载路径（None 使用默认路径）

        Returns:
            加载的 Collection 实例
        """
        ...

    # ==================== 抽象方法：统计信息 ====================

    @abstractmethod
    def get_storage_stats(self) -> dict[str, int]:
        """
        获取存储空间统计。

        返回所有存储组件（text_storage, metadata_storage, index）的条目数和大小。

        Returns:
            统计信息字典:
            {
                "total_entries": 总条目数,
                "text_storage_entries": 文本存储条目数,
                "metadata_storage_entries": 元数据存储条目数,
                "index_entries": 索引条目数（对于 VDB/Graph 等）,
                "total_size_bytes": 总大小（字节）
            }
        """
        ...

    # ==================== 基础方法：清理 ====================

    def clear(self) -> None:
        """
        Clear all stored text and metadata.
        清空所有存储的文本和元数据。
        """
        self.text_storage.clear()
        self.metadata_storage.clear()
