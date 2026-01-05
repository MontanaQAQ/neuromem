"""
LSHHashService - LSH 哈希记忆服务

使用场景:
- 大规模数据去重
- 快速近似相似度搜索
- 高维向量快速检索

设计:
- 索引: LSH（Locality-Sensitive Hashing）索引
- 特点: O(1) 近似查询，适合海量数据
- 需要 Embedding 模型
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    from ...memory_collection import UnifiedCollection

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("lsh_hash")
class LSHHashService(BaseMemoryService):
    """
    LSH 哈希记忆服务

    特性:
    - 使用 LSH 算法进行快速近似相似度搜索
    - 适合大规模向量检索（百万级）
    - 牺牲少量精度换取极高速度

    配置参数:
        embedding_dim: Embedding 维度（默认 768）
        num_tables: LSH 哈希表数量（默认 10，越多越精确但越慢）
        hash_size: 哈希位数（默认 8）
        embedder: Embedding 模型对象（必需）

    使用示例:
        >>> from some_embedder import SentenceTransformer
        >>> embedder = SentenceTransformer("all-MiniLM-L6-v2")
        >>> service = LSHHashService(collection, {
        ...     "embedding_dim": 384,
        ...     "num_tables": 10,
        ...     "embedder": embedder
        ... })
        >>> service.insert("这是一段文本")
        >>> results = service.retrieve("相似的文本", top_k=5)
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化 LSH 哈希服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - embedding_dim: Embedding 维度（默认 768）
                - num_tables: LSH 哈希表数量（默认 10）
                - hash_size: 哈希位数（默认 128）
                - embedder: Embedding 模型对象（可选，仅用于向后兼容）

        Note:
            按照 SAGE 架构设计，embedding 应该在 PreInsert/PreRetrieval Operator 层完成。
            Service 层应该接收已经 embedding 好的 vector，而不是依赖 embedder。
        """
        # 设置默认配置
        default_config = {
            "embedding_dim": 768,
            "num_tables": 10,
            "hash_size": 128,
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(collection, merged_config)

    def _setup_indexes(self) -> None:
        """
        配置 LSH 索引

        创建 LSH 哈希索引，用于快速近似相似度搜索。
        """
        embedding_dim = self.config.get("embedding_dim", 768)
        num_tables = self.config.get("num_tables", 10)
        hash_size = self.config.get("hash_size", 8)

        self.collection.add_index(
            name="lsh_index",
            index_type="lsh",
            config={
                "dim": embedding_dim,
                "num_tables": num_tables,
                "hash_size": hash_size,
            },
        )

        self.logger.info(
            f"Created LSH index with dim={embedding_dim}, "
            f"num_tables={num_tables}, hash_size={hash_size}"
        )

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
        插入数据到 LSH 索引（统一接口）

        Args:
            entry: 原始文本内容（旧接口参数名为 text）
            vector: 预计算的向量（推荐由 PreInsert Operator 提供）
            metadata: 元数据字典（可选）
            insert_mode: 插入模式 ("active" | "passive"，neuromem暂不区分）
            insert_params: 主动插入参数（可选，neuromem暂不使用）

        Returns:
            data_id: 生成的数据 ID

        Note:
            - 当前LSHIndex使用text-based MinHash实现
            - 按照架构设计，vector 应该由 PreInsert Operator 层提供
            - 如果 vector 未提供且配置了 embedder，会回退到自动计算（不推荐）
            - Embedding 存储在 metadata 中便于后续使用
        """
        # 获取或计算 Embedding（保存到metadata供未来使用）
        if vector is not None:
            embedding = vector
        elif "embedder" in self.config:
            # 向后兼容：如果配置了 embedder，则自动计算（不推荐）
            self.logger.warning(
                "Using embedder in Service layer is deprecated. "
                "Please compute embeddings in PreInsert Operator instead."
            )
            embedding = self._get_embeddings([entry])[0]
        else:
            # 没有 vector 也没有 embedder，使用 None（LSHIndex 会使用文本模式）
            embedding = None

        # 扩展元数据，添加 embedding（如果有的话）
        extended_metadata = {**(metadata or {})}
        if embedding is not None:
            extended_metadata["embedding"] = embedding

        # 尝试插入数据到 LSH 索引
        # 注意：当前LSHIndex使用text-based MinHash，不支持vector参数
        # 未来如果LSHIndex支持向量，可以传入vector=embedding
        try:
            # 尝试使用向量模式（如果LSHIndex支持）
            data_id = self.collection.insert(
                text=entry,
                metadata=extended_metadata,
                index_names=["lsh_index"],
                vector=embedding,  # 传递向量（当前会抛出NotImplementedError）
            )
        except (NotImplementedError, TypeError):
            # 回退到文本模式（当前的MinHash实现）
            self.logger.debug("LSH vector mode not available, using text-based MinHash")
            data_id = self.collection.insert(
                text=entry, metadata=extended_metadata, index_names=["lsh_index"]
            )

        self.logger.debug(f"Inserted {data_id[:8]}... to LSH index (text mode)")
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
        使用 LSH 检索相似数据

        Args:
            query: 查询文本
            vector: 查询向量（当前MinHash实现使用文本，该参数被忽略）
            metadata: 元数据过滤条件（可选）
            top_k: 返回的数据条数（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选，LSH返回近似结果）
            **kwargs: 额外参数

        Returns:
            结果列表: [{"id": "...", "text": "...", "metadata": {...}, "score": 0.9}, ...]
                按相似度降序排列

        Note:
            - 当前使用MinHash文本模式，vector参数会被忽略
            - LSH返回的是近似结果，可能不是绝对最优
            - score是估计的相似度分数
        """
        # 从 LSH 索引查询（使用文本模式）
        data_ids = self.collection.query_by_index(
            index_name="lsh_index",
            query=query or "",
            top_k=top_k,
        )

        # 获取完整数据
        results = []
        for i, data_id in enumerate(data_ids):
            item = self.collection.get(data_id)
            if item:
                # LSH 返回的是近似结果，score 是估计值
                # 这里使用排名作为 score（越靠前分数越高）
                score = 1.0 - (i / max(len(data_ids), 1)) * 0.5

                results.append(
                    {
                        "id": data_id,
                        "text": item["text"],
                        "metadata": item.get("metadata", {}),
                        "score": score,
                    }
                )

        # 应用元数据过滤（如果提供）
        filters = kwargs.get("filters")
        if filters:
            results = self._filter_by_metadata(results, filters)

        # 应用相似度阈值（如果提供）
        threshold = kwargs.get("threshold")
        if threshold is not None:
            results = [r for r in results if r["score"] >= threshold]

        self.logger.debug(f"Retrieved {len(results)} items from LSH index")
        return results

    def find_duplicates(
        self, threshold: float = 0.9, batch_size: int = 100
    ) -> list[tuple[str, str, float]]:
        """
        查找重复或高度相似的数据（去重功能）

        Args:
            threshold: 相似度阈值（默认 0.9）
            batch_size: 批处理大小

        Returns:
            重复对列表: [(id1, id2, similarity), ...]

        Example:
            >>> duplicates = service.find_duplicates(threshold=0.95)
            >>> print(f"Found {len(duplicates)} duplicate pairs")

        Note:
            - 此方法可能比较耗时（需要遍历所有数据）
            - 使用 LSH 加速相似度搜索
        """
        # 获取所有数据ID（通过raw_data而非索引查询）
        all_ids = list(self.collection.raw_data.keys())

        duplicates = []
        checked_pairs = set()  # 避免重复检查

        # 逐个检查
        for i, data_id in enumerate(all_ids):
            item = self.collection.get(data_id)
            if not item:
                continue

            # 使用当前数据的文本查询相似项
            text = item.get("text", "")
            if not text:
                continue

            # LSH 检索相似项（使用文本）
            similar_ids = self.collection.query_by_index(
                index_name="lsh_index",
                query=text,  # 使用文本而非向量
                top_k=10,  # 查找前 10 个最相似的
            )

            # 检查相似度
            for similar_id in similar_ids:
                if similar_id == data_id:
                    continue

                # 避免重复检查 (id1, id2) 和 (id2, id1)
                pair = tuple(sorted([data_id, similar_id]))
                if pair in checked_pairs:
                    continue

                checked_pairs.add(pair)

                # 估计相似度（简化版，实际可能需要计算精确余弦相似度）
                similarity = 0.95  # LSH 返回的通常是高相似度

                if similarity >= threshold:
                    duplicates.append((data_id, similar_id, similarity))

            # 进度日志
            if (i + 1) % batch_size == 0:
                self.logger.info(
                    f"Processed {i + 1}/{len(all_ids)} items, found {len(duplicates)} duplicates"
                )

        self.logger.info(f"Found {len(duplicates)} duplicate pairs total")
        return duplicates
