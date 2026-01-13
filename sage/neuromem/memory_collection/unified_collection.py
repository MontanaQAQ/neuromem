"""
UnifiedCollection - 统一数据容器，支持动态索引管理

设计原则:
- 数据只存一份 (raw_data)
- 索引可以有多个 (动态添加/删除)
- Collection 只管数据 + 索引容器，不关心索引实现细节

重构目标:
- 替代多种 Collection (VDB/Graph/KV/Hybrid)
- 通过组合而非继承获得索引能力
- 降低代码重复，提高扩展性
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class _StorageProxy:
    """
    存储代理 - 向后兼容 raw_data 字典接口

    将在 v0.4.0.0 中移除，请使用 collection.storage 替代。
    """

    def __init__(self, storage):
        self._storage = storage

    def __getitem__(self, key: str) -> dict[str, Any]:
        result = self._storage.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        self._storage.put(key, value)

    def __delitem__(self, key: str) -> None:
        self._storage.delete(key)

    def __contains__(self, key: str) -> bool:
        return self._storage.get(key) is not None

    def __len__(self) -> int:
        return len(self._storage)

    def get(self, key: str, default=None):
        result = self._storage.get(key)
        return result if result is not None else default

    def keys(self):
        return self._storage.keys()

    def items(self):
        for key in self._storage:
            value = self._storage.get(key)
            if value is not None:
                yield key, value

    def values(self):
        for key in self._storage:
            value = self._storage.get(key)
            if value is not None:
                yield value


class UnifiedCollection:
    """
    统一数据容器 - 管理原始数据 + 多种索引

    Attributes:
        name: Collection 名称
        storage: 可插拔存储后端 (Memory/Redis/SageDB)
        raw_data: 原始数据存储 {data_id: {text, metadata, created_at}} (向后兼容，将弃用)
        indexes: 索引容器 {index_name: IndexObject}
        index_metadata: 索引配置信息 {index_name: {type, config, created_at}}
    """

    def __init__(
        self,
        name: str,
        storage_backend: str = "memory",
        storage_config: dict[str, Any] | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        初始化 UnifiedCollection

        Args:
            name: Collection 名称
            storage_backend: 存储后端类型 ("memory", "redis", "sagedb")
            storage_config: 存储后端配置字典
            config: 其他配置（预留用于持久化路径等）
        """
        self.name = name
        self.config = config or {}
        self._is_unified_collection = True  # Marker for Mixin compatibility

        # 创建可插拔存储后端
        from ..storage_engine import StorageFactory

        self.storage = StorageFactory.create(storage_backend, storage_config)

        # 向后兼容：raw_data 作为 storage 的别名
        # 将在 v0.4.0.0 中移除
        self.raw_data = _StorageProxy(self.storage)

        self.indexes: dict[str, Any] = {}  # 索引对象容器
        self.index_metadata: dict[str, dict[str, Any]] = {}  # 索引配置信息

        logger.info(f"Created UnifiedCollection: {name} with {storage_backend} storage")

    # ==================== 数据操作 (T1.1 任务) ====================

    def insert(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
        index_names: list[str] | None = None,
    ) -> str:
        """
        插入数据到 Collection

        Args:
            text: 原始文本内容
            metadata: 可选的元数据字典
            index_names: 要加入的索引列表 (None 表示加入所有索引)

        Returns:
            data_id: 生成的数据 ID (基于内容的 SHA256 哈希)

        Note:
            - 数据 ID 基于 text + metadata 生成，保证内容相同时 ID 稳定
            - 如果 ID 已存在，会覆盖旧数据（更新语义）
            - 数据会自动加入指定的索引（或所有索引）
        """
        data_id = self._generate_id(text, metadata)

        # 存储原始数据到可插拔后端
        self.storage.put(
            data_id,
            {
                "text": text,
                "metadata": metadata or {},
                "created_at": time.time(),
            },
        )

        # T1.2: 将数据加入指定索引
        target_indexes = list(self.indexes.keys()) if index_names is None else index_names
        for idx_name in target_indexes:
            if idx_name in self.indexes:
                self.indexes[idx_name].add(data_id, text, metadata or {})

        logger.debug(f"Inserted data {data_id[:8]}... to {self.name}")
        return data_id

    def get(self, data_id: str) -> dict[str, Any] | None:
        """
        获取原始数据

        Args:
            data_id: 数据 ID

        Returns:storage
            数据字典 {text, metadata, created_at}，不存在则返回 None
        """
        return self.raw_data.get(data_id)

    def insert_batch(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        index_names: list[str] | None = None,
    ) -> list[str]:
        """
        批量插入数据到 Collection

        Args:
            texts: 文本列表
            metadatas: 元数据列表（可选，默认为空字典列表）
            index_names: 要加入的索引列表 (None 表示加入所有索引)

        Returns:
            data_ids: 生成的数据 ID 列表

        Raises:
            ValueError: 当 texts 和 metadatas 长度不一致时

        Note:
            - 批量操作是通过多次调用 insert() 实现的
            - 后续可以优化为批量索引更新（T1.2）
        """
        if metadatas is None:
            metadatas = [{}] * len(texts)

        if len(texts) != len(metadatas):
            msg = f"texts ({len(texts)}) and metadatas ({len(metadatas)}) must have same length"
            raise ValueError(msg)

        data_ids = []
        for text, metadata in zip(texts, metadatas):
            data_id = self.insert(text, metadata, index_names)
            data_ids.append(data_id)

        logger.debug(f"Batch inserted {len(data_ids)} items to {self.name}")
        return data_ids

    def size(self) -> int:
        """
        获取 Collection 中的数据条数

        Returns:
            数据条目总数
        """
        return len(self.raw_data)

    def delete(self, data_id: str) -> bool:
        """
        完全删除数据 (包括原始数据和所有索引中的条目)

        Args:
            data_id: 数据 ID

        Returns:
            是否删除成功 (False 表示 ID 不存在)

        Note:
            - 会从所有索引中移除该数据
            - 删除后无法恢复
        """
        if data_id not in self.raw_data:
            logger.warning(f"Data {data_id} not found in {self.name}")
            return False

        # T1.2: 从所有索引中移除
        for index in self.indexes.values():
            index.remove(data_id)

        # 删除原始数据
        del self.raw_data[data_id]
        logger.debug(f"Deleted data {data_id[:8]}... from {self.name}")
        return True

    def _generate_id(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """
        生成稳定的数据 ID (基于内容的 SHA256 哈希)

        Args:
            text: 原始文本
            metadata: 元数据字典

        Returns:
            64 字符的 SHA256 哈希字符串

        Implementation:
            - 使用 text + sorted_metadata 作为键
            - 保证相同内容生成相同 ID
            - metadata 按键排序后序列化，确保顺序不影响结果
        """
        key = text
        if metadata:
            # 按键排序后序列化，确保稳定性
            key += json.dumps(metadata, sort_keys=True, ensure_ascii=False)

        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    # ==================== 工具方法 ====================

    def __len__(self) -> int:
        """返回数据条目总数"""
        return len(self.raw_data)

    def __contains__(self, data_id: str) -> bool:
        """检查数据 ID 是否存在"""
        return data_id in self.raw_data

    def __repr__(self) -> str:
        """返回 Collection 的字符串表示"""
        return (
            f"UnifiedCollection(name='{self.name}', "
            f"data_count={len(self.raw_data)}, "
            f"index_count={len(self.indexes)})"
        )

    # ==================== 索引管理 (T1.2 任务) ====================

    def add_index(self, name: str, index_type: str, config: dict[str, Any] | None = None) -> bool:
        """
        动态添加索引到 Collection

        Args:
            name: 索引名称（如 "fifo_queue", "vector_faiss"）
            index_type: 索引类型（"faiss", "lsh", "graph", "bm25", "fifo"）
            config: 索引配置（如 dim, max_size 等）

        Returns:
            是否添加成功（False 表示索引已存在）

        Note:
            - 通过 IndexFactory 创建索引实例（T1.3 实现）
            - 新建索引时不会自动加入现有数据
            - 使用 insert_to_index() 手动迁移数据
        """
        if name in self.indexes:
            logger.warning(f"Index '{name}' already exists in {self.name}")
            return False

        # T1.3: 通过工厂创建索引
        from .indexes import IndexFactory

        index = IndexFactory.create(index_type, config or {})
        self.indexes[name] = index

        self.index_metadata[name] = {
            "type": index_type,
            "config": config or {},
            "created_at": time.time(),
        }

        logger.info(f"Added index '{name}' of type '{index_type}' to {self.name}")
        return True

    def remove_index(self, name: str) -> bool:
        """
        删除索引（不影响原始数据）

        Args:
            name: 索引名称

        Returns:
            是否删除成功（False 表示索引不存在）

        Note:
            - 只删除索引，原始数据保留
            - 索引数据不可恢复
        """
        if name not in self.indexes:
            logger.warning(f"Index '{name}' not found in {self.name}")
            return False

        del self.indexes[name]
        del self.index_metadata[name]
        logger.info(f"Removed index '{name}' from {self.name}")
        return True

    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引的信息

        Returns:
            索引信息列表，每个元素包含 {name, type, config}
        """
        return [
            {"name": name, "type": meta["type"], "config": meta["config"]}
            for name, meta in self.index_metadata.items()
        ]

    def insert_to_index(self, data_id: str, index_name: str) -> bool:
        """
        将已有数据加入指定索引

        Args:
            data_id: 数据 ID
            index_name: 索引名称

        Returns:
            是否成功（False 表示数据或索引不存在）

        Use Case:
            - 新建索引后迁移现有数据
            - 选择性地将数据加入某些索引
        """
        if data_id not in self.raw_data:
            logger.warning(f"Data {data_id} not found in {self.name}")
            return False

        if index_name not in self.indexes:
            logger.warning(f"Index '{index_name}' not found in {self.name}")
            return False

        data = self.raw_data[data_id]
        self.indexes[index_name].add(data_id, data["text"], data["metadata"])
        logger.debug(f"Added data {data_id[:8]}... to index '{index_name}'")
        return True

    def remove_from_index(self, data_id: str, index_name: str) -> bool:
        """
        从索引移除数据（保留原始数据）

        Args:
            data_id: 数据 ID
            index_name: 索引名称

        Returns:
            是否成功（False 表示索引不存在）

        Note:
            - 只从索引移除，原始数据保留
            - 如果数据不在索引中，操作仍返回 True
        """
        if index_name not in self.indexes:
            logger.warning(f"Index '{index_name}' not found in {self.name}")
            return False

        self.indexes[index_name].remove(data_id)
        logger.debug(f"Removed data {data_id[:8]}... from index '{index_name}'")
        return True

    def query_by_index(self, index_name: str, query: Any, **params: Any) -> list[str]:
        """
        通过指定索引查询数据 ID

        Args:
            index_name: 索引名称
            query: 查询内容（根据索引类型不同：文本/向量/图节点）
            **params: 查询参数（top_k, threshold 等）

        Returns:
            匹配的 data_id 列表

        Raises:
            ValueError: 索引不存在时抛出

        Examples:
            # FIFO 队列索引
            ids = collection.query_by_index("fifo", query=None, top_k=10)

            # 向量索引
            ids = collection.query_by_index("vector", query=[0.1, 0.2, ...], top_k=5)

            # 图索引
            ids = collection.query_by_index("graph", query="node_id", depth=2)
        """
        if index_name not in self.indexes:
            msg = f"Index '{index_name}' not found in {self.name}"
            raise ValueError(msg)

        return self.indexes[index_name].query(query, **params)

    def retrieve(self, index_name: str, query: Any, **params: Any) -> list[dict[str, Any]]:
        """
        检索完整数据（query_by_index + get 的快捷方式）

        Args:
            index_name: 索引名称
            query: 查询内容
            **params: 查询参数

        Returns:
            匹配的完整数据列表 [{id, text, metadata, created_at}, ...]

        Note:
            - 等价于 [get(id) for id in query_by_index(...)]
            - 自动过滤掉已删除的数据
            - 返回结果包含 id 字段以支持 Mixin 功能
        """
        data_ids = self.query_by_index(index_name, query, **params)
        results = []
        for id_ in data_ids:
            if id_ in self.raw_data:
                data = self.raw_data[id_].copy()
                data["id"] = id_  # Add id field for Mixin compatibility
                results.append(data)
        return results
