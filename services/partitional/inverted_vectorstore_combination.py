"""
InvertedVectorStoreCombinationService - 倒排+向量组合服务

设计要点:
1. 两个索引组合: Inverted (BM25) + Vector (FAISS)
2. 支持 RRF (Reciprocal Rank Fusion) 融合
3. 平衡精确匹配和语义检索

使用场景:
- 混合检索场景
- 需要精确匹配 + 语义相似
- FAQ 系统、文档检索

配置示例:
    config = {
        "vector_dim": 768,
        "fusion_strategy": "rrf",  # rrf or linear
        "rrf_k": 60,
        "linear_alpha": 0.5,  # BM25 weight (1-alpha for vector)
    }
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    from ...memory_collection import UnifiedCollection

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("inverted_vectorstore_combination")
class InvertedVectorStoreCombinationService(BaseMemoryService):
    """
    倒排 + 向量组合服务

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置
        vector_dim: 向量维度
        fusion_strategy: 融合策略 (rrf/linear)
        rrf_k: RRF 常数参数
        linear_alpha: 线性融合中 BM25 权重
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化组合服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - vector_dim: 向量维度 (默认 768)
                - fusion_strategy: rrf/linear (默认 rrf)
                - rrf_k: RRF 参数 (默认 60)
                - linear_alpha: BM25 权重 (默认 0.5)
        """
        # 提取配置参数
        self.vector_dim = config.get("vector_dim", 768) if config else 768
        self.fusion_strategy = config.get("fusion_strategy", "rrf") if config else "rrf"
        self.rrf_k = config.get("rrf_k", 60) if config else 60
        self.linear_alpha = config.get("linear_alpha", 0.5) if config else 0.5

        # 调用父类初始化（会触发 _setup_indexes）
        super().__init__(collection, config)

    def _setup_indexes(self) -> None:
        """
        配置两个索引：倒排索引和向量索引

        Note:
            - BM25 用于精确关键词匹配
            - FAISS 用于语义相似检索
        """
        # 1. 倒排索引 (BM25) - 关键词检索
        self.collection.add_index(
            name="inverted_index",
            index_type="bm25",
            config={
                "backend": "numba",
                "language": "auto",
            },
        )

        # 2. 向量索引 (FAISS) - 语义检索
        self.collection.add_index(
            name="vector_index",
            index_type="faiss",
            config={
                "dim": self.vector_dim,
                "metric": "cosine",
                "index_type": "Flat",
            },
        )

        self.logger.info(f"Set up 2 indexes: inverted (BM25) + vector ({self.vector_dim}D FAISS)")

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
        插入数据到两个索引

        Args:
            entry: 原始文本
            vector: 预计算的向量 (可选)
            metadata: 元数据
            insert_mode: 插入模式 (passive/active等，暂未使用)
            insert_params: 插入参数 (暂未使用)

        Returns:
            data_id: 数据 ID
        """
        # 确保metadata不为None
        if metadata is None:
            metadata = {}

        # 如果有vector，添加到metadata
        if vector is not None:
            metadata["vector"] = vector

        # 插入到 Collection（会自动添加到所有索引）
        data_id = self.collection.insert(text=entry, metadata=metadata)

        self.logger.debug(f"Inserted data '{data_id}' to inverted + vector indexes")

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
        检索数据，使用倒排 + 向量融合

        Args:
            query: 查询文本
            vector: 查询向量（可选）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数量（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 额外参数
                - strategy: 覆盖默认融合策略(rrf/linear)
                - filters: 额外过滤条件(可选)

        Returns:
            结果列表 [{"id": "...", "text": "...", "metadata": {...}, "score": 0.9}, ...]
        """
        strategy = kwargs.get("strategy", self.fusion_strategy)
        query_vector = vector  # 兼容参数名

        # 1. BM25 检索
        inverted_ids = self.collection.query_by_index(
            index_name="inverted_index", query=query or "", top_k=top_k * 2
        )
        inverted_results = self._ids_to_results(inverted_ids)

        # 2. 向量检索 - 使用 vector 参数或 query 作为备选
        # 优先级: kwargs["query_vector"] > vector 参数 > query 文本
        vector_query = kwargs.get("query_vector") or query_vector or query
        if vector_query is None:
            # 如果没有向量查询，仅使用 BM25 结果
            return inverted_results[:top_k]

        vector_ids = self.collection.query_by_index(
            index_name="vector_index",
            query=vector_query,
            top_k=top_k * 2,
        )
        vector_results = self._ids_to_results(vector_ids)

        # 3. 融合
        if strategy == "rrf":
            fused_results = self._rrf_fusion(inverted_results, vector_results, self.rrf_k)
        elif strategy == "linear":
            fused_results = self._linear_fusion(inverted_results, vector_results, self.linear_alpha)
        else:
            msg = f"Unknown fusion strategy: {strategy}"
            raise ValueError(msg)

        return fused_results[:top_k]

    def _rrf_fusion(
        self,
        inverted_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]],
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """
        RRF (Reciprocal Rank Fusion) 融合策略

        公式: RRF(d) = Σ 1/(k + rank_i(d))

        Args:
            inverted_results: BM25 检索结果
            vector_results: 向量检索结果
            k: RRF 常数参数 (默认 60)

        Returns:
            融合后的结果列表
        """
        # 构建排名字典
        inverted_ranks = {r["id"]: idx + 1 for idx, r in enumerate(inverted_results)}
        vector_ranks = {r["id"]: idx + 1 for idx, r in enumerate(vector_results)}

        # 收集所有 data_id
        all_ids = set(inverted_ranks.keys()) | set(vector_ranks.keys())

        # 计算 RRF 分数
        rrf_scores: dict[str, float] = {}
        all_data: dict[str, dict[str, Any]] = {}

        for data_id in all_ids:
            rrf_score = 0.0
            if data_id in inverted_ranks:
                rrf_score += 1.0 / (k + inverted_ranks[data_id])
            if data_id in vector_ranks:
                rrf_score += 1.0 / (k + vector_ranks[data_id])

            rrf_scores[data_id] = rrf_score

            # 保存数据对象（优先使用 inverted_results）
            for result in inverted_results:
                if result["id"] == data_id:
                    all_data[data_id] = result
                    break
            else:
                for result in vector_results:
                    if result["id"] == data_id:
                        all_data[data_id] = result
                        break

        # 按 RRF 分数排序
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # 构造结果
        fused_results = []
        for data_id in sorted_ids:
            result = all_data[data_id]
            result["rrf_score"] = rrf_scores[data_id]
            result["inverted_rank"] = inverted_ranks.get(data_id)
            result["vector_rank"] = vector_ranks.get(data_id)
            fused_results.append(result)

        self.logger.debug(
            f"RRF fusion: {len(inverted_results)} inverted + {len(vector_results)} vector "
            f"→ {len(fused_results)} fused (k={k})"
        )

        return fused_results

    def _linear_fusion(
        self,
        inverted_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]],
        alpha: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        线性融合策略

        公式: score(d) = α * score_inverted(d) + (1-α) * score_vector(d)

        Args:
            inverted_results: BM25 检索结果
            vector_results: 向量检索结果
            alpha: BM25 权重 (0-1)

        Returns:
            融合后的结果列表
        """
        # 归一化分数到 [0, 1]
        inverted_scores = self._normalize_scores(
            {r["id"]: r.get("score", 1.0) for r in inverted_results}
        )
        vector_scores = self._normalize_scores(
            {r["id"]: r.get("score", 1.0) for r in vector_results}
        )

        # 收集所有 data_id
        all_ids = set(inverted_scores.keys()) | set(vector_scores.keys())

        # 计算线性融合分数
        linear_scores: dict[str, float] = {}
        all_data: dict[str, dict[str, Any]] = {}

        for data_id in all_ids:
            inverted_score = inverted_scores.get(data_id, 0.0)
            vector_score = vector_scores.get(data_id, 0.0)
            linear_score = alpha * inverted_score + (1 - alpha) * vector_score

            linear_scores[data_id] = linear_score

            # 保存数据对象
            for result in inverted_results:
                if result["id"] == data_id:
                    all_data[data_id] = result
                    break
            else:
                for result in vector_results:
                    if result["id"] == data_id:
                        all_data[data_id] = result
                        break

        # 按线性分数排序
        sorted_ids = sorted(linear_scores.keys(), key=lambda x: linear_scores[x], reverse=True)

        # 构造结果
        fused_results = []
        for data_id in sorted_ids:
            result = all_data[data_id]
            result["linear_score"] = linear_scores[data_id]
            result["inverted_score"] = inverted_scores.get(data_id, 0.0)
            result["vector_score"] = vector_scores.get(data_id, 0.0)
            fused_results.append(result)

        self.logger.debug(
            f"Linear fusion: {len(inverted_results)} inverted + {len(vector_results)} vector "
            f"→ {len(fused_results)} fused (alpha={alpha})"
        )

        return fused_results

    def _normalize_scores(self, scores: dict[str, float]) -> dict[str, float]:
        """
        归一化分数到 [0, 1]

        Args:
            scores: {data_id: score}

        Returns:
            归一化后的分数字典
        """
        if not scores:
            return {}

        values = list(scores.values())
        min_score = min(values)
        max_score = max(values)

        # 避免除零
        if max_score == min_score:
            return dict.fromkeys(scores, 1.0)

        # Min-Max 归一化
        normalized = {
            data_id: (score - min_score) / (max_score - min_score)
            for data_id, score in scores.items()
        }

        return normalized

    def _ids_to_results(self, data_ids: list[str]) -> list[dict[str, Any]]:
        """
        将data_id列表转换为完整的结果字典列表

        Args:
            data_ids: data_id列表

        Returns:
            结果列表 [{id, text, metadata, score}, ...]
        """
        results = []
        for idx, data_id in enumerate(data_ids):
            if data_id in self.collection.raw_data:
                data = self.collection.raw_data[data_id]
                results.append(
                    {
                        "id": data_id,
                        "text": data["text"],
                        "metadata": data["metadata"],
                        "score": 1.0 / (idx + 1),  # 简单的排名分数
                    }
                )
        return results
