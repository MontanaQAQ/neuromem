"""
BaseMemoryService - MemoryService 抽象基类

设计要点:
1. 持有 UnifiedCollection 引用 (组合，不继承)
2. 定义统一的业务接口 (insert, retrieve)
3. 提供公共工具方法 (_get_embeddings, _summarize, etc.)

核心方法:
- _setup_indexes(): 配置所需索引 (抽象方法，子类实现)
- insert(): 插入数据 + Service 特定逻辑 (抽象方法)
- retrieve(): 检索数据 + Service 特定逻辑 (抽象方法)
- delete(), get(): 通用数据操作 (具体实现)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..memory_collection import UnifiedCollection

logger = logging.getLogger(__name__)


class BaseMemoryService(ABC):
    """
    MemoryService 抽象基类 - 所有 13 个 Service 的父类

    设计原则:
    - Service = Collection + 业务逻辑
    - 持有 UnifiedCollection 引用 (不继承)
    - 定义统一的抽象接口
    - 提供公共工具方法

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置字典
        logger: 日志记录器
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化 MemoryService

        Args:
            collection: UnifiedCollection 实例 (由 MemoryManager 提供)
            config: Service 配置字典
                - top_k: 默认检索数量
                - embedder: Embedding 模型 (可选)
                - summarizer: 摘要模型 (可选)
                - threshold: 相似度阈值 (可选)
                - ... Service 特定配置

        Note:
            - __init__ 中会自动调用 _setup_indexes()
            - 子类只需实现 _setup_indexes() 来配置索引
        """
        self.collection = collection
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Service 特定初始化 (子类实现)
        self._setup_indexes()

        self.logger.info(
            f"Initialized {self.__class__.__name__} for collection '{collection.name}'"
        )

    # ========== 抽象方法 (子类必须实现) ==========

    @abstractmethod
    def _setup_indexes(self) -> None:
        """
        配置 Service 所需的索引

        在 __init__ 中自动调用。子类应在此方法中调用
        self.collection.add_index() 来创建索引。

        Example:
            def _setup_indexes(self):
                self.collection.add_index("vector", "faiss", {"dim": 768})
                self.collection.add_index("queue", "fifo", {"max_size": 10})

        Note:
            - 不要直接在 __init__ 中创建索引
            - 使用此方法保持代码结构一致
        """

    @abstractmethod
    def insert(self, text: str, metadata: dict[str, Any] | None = None, **kwargs: Any) -> str:
        """
        插入数据 (Service 特定逻辑)

        Args:
            text: 原始文本内容
            metadata: 元数据字典
            **kwargs: Service 特定参数
                - vector: 预计算的向量 (可选)
                - segment_id: 分段 ID (可选)
                - edges: 图边列表 (可选)

        Returns:
            data_id: 生成的数据 ID

        Note:
            - 子类应实现 Service 特定的插入逻辑
            - 例如：特征提取、自动分段、图关系构建等
        """

    @abstractmethod
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
        检索数据 (Service 特定逻辑)

        Args:
            query: 查询文本（可选）
            vector: 查询向量（可选，用于向量检索）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数量（默认5）
            hints: 检索策略提示（可选，由PreRetrieval生成）
            threshold: 相似度阈值（可选，过滤低于阈值的结果）
            **kwargs: Service 特定参数
                - filters: 额外过滤条件
                - segment_id: 指定分段（层次化服务）
                - fusion_strategy: 多索引融合策略

        Returns:
            结果列表: [{"id": "...", "text": "...", "metadata": {...}, "score": 0.9}, ...]

        Note:
            - 统一接口，兼容旧服务签名（vector, metadata, hints, threshold显式参数）
            - 子类应实现 Service 特定的检索逻辑
            - 例如：多索引融合、重排序、过滤等
        """

    # ========== 公共方法 (所有 Service 共享) ==========

    def delete(self, entry_id: str) -> bool:
        """
        删除数据 (通用实现)

        Args:
            entry_id: 数据 ID（兼容 data_id）

        Returns:
            是否成功删除

        Note:
            - 会从 Collection 中删除原始数据
            - 所有索引中的对应项也会被删除
        """
        result = self.collection.delete(entry_id)
        if result:
            self.logger.debug(f"Deleted data {entry_id[:8]}...")
        else:
            self.logger.warning(f"Failed to delete data {entry_id[:8]}...")
        return result

    def get(self, data_id: str) -> dict[str, Any] | None:
        """
        获取原始数据 (通用实现)

        Args:
            data_id: 数据 ID

        Returns:
            数据字典: {"text": "...", "metadata": {...}, "created_at": 123456} 或 None
        """
        return self.collection.get(data_id)

    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出当前 Service 使用的索引

        Returns:
            索引列表: [{"name": "vector", "type": "faiss", "config": {...}}, ...]
        """
        return self.collection.list_indexes()

    # ========== 工具方法 (子类可选使用) ==========

    def _get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        批量获取 Embedding (公共工具)

        Args:
            texts: 文本列表

        Returns:
            向量列表: [[0.1, 0.2, ...], ...]

        Raises:
            ValueError: 如果 embedder 未配置

        Note:
            - 需要在 config 中提供 embedder 对象
            - embedder 应有 embed(texts: List[str]) -> List[List[float]] 方法
        """
        embedder = self.config.get("embedder")
        if not embedder:
            raise ValueError(
                f"{self.__class__.__name__} requires 'embedder' in config for embedding"
            )
        return embedder.embed(texts)

    def _summarize(self, texts: list[str]) -> str:
        """
        总结文本 (公共工具)

        Args:
            texts: 文本列表

        Returns:
            摘要文本

        Note:
            - 需要在 config 中提供 summarizer 对象
            - 如果未配置，返回前 100 个 token 的拼接 (fallback)
        """
        summarizer = self.config.get("summarizer")
        if not summarizer:
            # Fallback: 简单拼接前 100 个 token
            combined = " ".join(texts)
            tokens = combined.split()[:100]
            return " ".join(tokens)
        return summarizer.summarize(texts)

    def _filter_by_metadata(
        self, results: list[dict[str, Any]], filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        元数据过滤 (公共工具)

        Args:
            results: 检索结果列表
            filters: 过滤条件字典 {"key": "value", ...}

        Returns:
            过滤后的结果列表

        Example:
            results = [
                {"id": "1", "metadata": {"type": "doc", "lang": "en"}},
                {"id": "2", "metadata": {"type": "code", "lang": "python"}},
            ]
            filtered = self._filter_by_metadata(results, {"type": "doc"})
            # 返回: [{"id": "1", ...}]
        """
        if not filters:
            return results

        filtered = []
        for item in results:
            metadata = item.get("metadata", {})
            # 检查所有过滤条件是否匹配
            if all(metadata.get(k) == v for k, v in filters.items()):
                filtered.append(item)

        self.logger.debug(f"Filtered {len(results)} -> {len(filtered)} results")
        return filtered

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"{self.__class__.__name__}("
            f"collection='{self.collection.name}', "
            f"indexes={len(self.collection.indexes)})"
        )
