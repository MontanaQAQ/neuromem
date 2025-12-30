"""
FeatureQueueVectorstoreCombinationService - 特征+队列+向量组合服务

设计要点:
1. 三个索引组合: Feature (BM25) + FIFOQueue + Vectorstore (FAISS)
2. 平衡关键词检索、时序信息和语义相似度
3. 支持多种融合策略

使用场景:
- 混合检索 + 时序管理
- FAQ系统
- 文档检索 + 时间窗口

配置示例:
    config = {
        "vector_dim": 768,
        "fifo_max_size": 100,
        "combination_strategy": "weighted",
        "weights": {
            "feature_index": 0.3,
            "fifo_index": 0.3,
            "vector_index": 0.4,
        },
        "fusion_method": "rrf",  # rrf/linear
        "rrf_k": 60,
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


@MemoryServiceRegistry.register("feature_queue_vectorstore_combination")
class FeatureQueueVectorstoreCombinationService(BaseMemoryService):
    """
    特征 + FIFO队列 + 向量库组合服务

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置
        vector_dim: 向量维度
        fifo_max_size: FIFO队列最大大小
        combination_strategy: 组合策略
        weights: 各索引权重
        fusion_method: RRF或Linear融合
        rrf_k: RRF常数
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化组合服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - vector_dim: 向量维度 (默认 768)
                - fifo_max_size: FIFO队列大小 (默认 100)
                - combination_strategy: 组合策略 (默认 weighted)
                - weights: 各索引权重字典
                - fusion_method: rrf/linear (默认 rrf)
                - rrf_k: RRF参数 (默认 60)
        """
        # 配置参数 - 必须在 super().__init__() 之前设置
        config = config or {}
        self.vector_dim = config.get("vector_dim", 768)
        self.fifo_max_size = config.get("fifo_max_size", 100)
        self.combination_strategy = config.get("combination_strategy", "weighted")
        self.weights = config.get(
            "weights",
            {
                "feature_index": 0.3,
                "fifo_index": 0.3,
                "vector_index": 0.4,
            },
        )
        self.fusion_method = config.get("fusion_method", "rrf")
        self.rrf_k = config.get("rrf_k", 60)

        super().__init__(collection, config)

        self.logger.info(
            f"FeatureQueueVectorstoreCombinationService initialized: "
            f"vector_dim={self.vector_dim}, "
            f"fifo_max_size={self.fifo_max_size}, "
            f"combination_strategy={self.combination_strategy}, "
            f"fusion_method={self.fusion_method}"
        )

    def _setup_indexes(self):
        """配置所需索引"""
        # 1. Feature索引 (BM25)
        self.collection.add_index(name="feature_index", index_type="bm25", config={})

        # 2. FIFO Queue索引
        self.collection.add_index(
            name="fifo_index", index_type="fifo", config={"max_size": self.fifo_max_size}
        )

        # 3. Vector索引 (FAISS)
        self.collection.add_index(
            name="vector_index", index_type="faiss", config={"dim": self.vector_dim}
        )

        self.logger.info("Indexes configured: feature_index, fifo_index, vector_index")

    def insert(
        self,
        entry: str,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "default",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """
        插入数据到三个索引（统一接口）

        Args:
            entry: 文本内容
            vector: 查询向量（可选，如果未提供则自动生成）
            metadata: 元数据（可选）
            insert_mode: 插入模式（默认 "default"）
            insert_params: 插入参数（可选）

        Returns:
            str: 数据ID
        """
        metadata = metadata or {}

        # 向量必须由调用者提供
        if vector is None:
            raise ValueError(
                "Vector is required for insert operation. Embedding should be done by caller."
            )

        metadata["vector"] = vector

        # 插入到所有索引
        data_id = self.collection.insert(
            text=entry,
            metadata=metadata,
            index_names=["feature_index", "fifo_index", "vector_index"],
        )

        self.logger.debug(f"Inserted data_id={data_id}, text_len={len(entry)}")
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
        检索数据 - 支持多种策略

        Args:
            query: 查询文本
            vector: 查询向量（即query_vector，用于向量检索）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 其他参数
                - strategy: 组合策略(weighted/voting/rrf/linear/recent)

        Returns:
            list[dict]: 检索结果列表
        """
        strategy = kwargs.get("strategy") or self.combination_strategy
        query_vector = vector  # 兼容旧参数名

        if strategy == "weighted":
            return self._retrieve_weighted(query or "", top_k, query_vector, **kwargs)
        elif strategy == "voting":
            return self._retrieve_voting(query or "", top_k, query_vector, **kwargs)
        elif strategy == "rrf":
            return self._retrieve_rrf(query or "", top_k, query_vector, **kwargs)
        elif strategy == "linear":
            return self._retrieve_linear(query or "", top_k, query_vector, **kwargs)
        elif strategy == "recent":
            return self._retrieve_recent(query or "", top_k, **kwargs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _retrieve_weighted(
        self, query: str, top_k: int, query_vector: list[float] | None = None, **kwargs
    ) -> list[dict]:
        """加权融合检索"""
        # Feature检索
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        # FIFO检索
        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        # Vector检索
        if query_vector is None:
            raise ValueError(
                "Query vector is required for vector retrieval. Embedding should be done by caller."
            )

        vector_results = self.collection.retrieve(
            index_name="vector_index", query=query_vector, top_k=top_k * 2
        )

        # 加权融合
        return self._weighted_fusion(
            {
                "feature_index": feature_results,
                "fifo_index": fifo_results,
                "vector_index": vector_results,
            },
            self.weights,
            top_k,
        )

    def _retrieve_voting(
        self, query: str, top_k: int, query_vector: list[float] | None = None, **kwargs
    ) -> list[dict]:
        """投票融合检索"""
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        if query_vector is None:
            raise ValueError(
                "Query vector is required for vector retrieval. Embedding should be done by caller."
            )

        vector_results = self.collection.retrieve(
            index_name="vector_index", query=query_vector, top_k=top_k * 2
        )

        # 投票计数
        votes: dict[str, int] = {}
        item_map: dict[str, dict] = {}

        for result in feature_results + fifo_results + vector_results:
            item_id = result.get("id", result.get("data_id"))
            votes[item_id] = votes.get(item_id, 0) + 1
            item_map[item_id] = result

        # 按投票数排序
        sorted_ids = sorted(votes.keys(), key=lambda x: votes[x], reverse=True)
        return [item_map[id_] for id_ in sorted_ids[:top_k]]

    def _retrieve_rrf(
        self, query: str, top_k: int, query_vector: list[float] | None = None, **kwargs
    ) -> list[dict]:
        """RRF (Reciprocal Rank Fusion) 融合检索"""
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        if query_vector is None:
            raise ValueError(
                "Query vector is required for vector retrieval. Embedding should be done by caller."
            )

        vector_results = self.collection.retrieve(
            index_name="vector_index", query=query_vector, top_k=top_k * 2
        )

        # RRF 融合
        return self._rrf_fusion([feature_results, fifo_results, vector_results], self.rrf_k, top_k)

    def _retrieve_linear(
        self,
        query: str,
        top_k: int,
        query_vector: list[float] | None = None,
        alpha: float = 0.5,
        **kwargs,
    ) -> list[dict]:
        """线性融合检索 (feature + vector, 忽略fifo的时序信息)"""
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        if query_vector is None:
            raise ValueError(
                "Query vector is required for vector retrieval. Embedding should be done by caller."
            )

        vector_results = self.collection.retrieve(
            index_name="vector_index", query=query_vector, top_k=top_k * 2
        )

        # 线性融合
        return self._linear_fusion(feature_results, vector_results, alpha, top_k)

    def _retrieve_recent(self, query: str, top_k: int, **kwargs) -> list[dict]:
        """优先返回最近的数据"""
        fifo_results = self.collection.retrieve(index_name="fifo_index", query=query, top_k=top_k)
        return fifo_results[:top_k]

    def get_recent_items(self, count: int = 10) -> list[dict]:
        """获取最近的N个项目"""
        results = self.collection.retrieve(index_name="fifo_index", query="", top_k=count)
        return results

    # ========== 工具方法 ==========

    def _weighted_fusion(
        self, result_sets: dict[str, list[dict]], weights: dict[str, float], top_k: int
    ) -> list[dict]:
        """加权融合多个结果集"""
        scores: dict[str, float] = {}
        item_map: dict[str, dict] = {}

        for index_name, results in result_sets.items():
            weight = weights.get(index_name, 0.0)

            for i, result in enumerate(results):
                item_id = result.get("id", result.get("data_id"))
                # 位置得分: 1 / (rank + 1)
                position_score = 1.0 / (i + 1)
                scores[item_id] = scores.get(item_id, 0.0) + weight * position_score
                item_map[item_id] = result

        # 按得分排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [{**item_map[id_], "fused_score": scores[id_]} for id_ in sorted_ids[:top_k]]

    def _rrf_fusion(self, result_lists: list[list[dict]], k: int, top_k: int) -> list[dict]:
        """RRF融合"""
        scores: dict[str, float] = {}
        item_map: dict[str, dict] = {}

        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                item_id = result.get("id", result.get("data_id"))
                rrf_score = 1.0 / (k + rank)
                scores[item_id] = scores.get(item_id, 0.0) + rrf_score
                item_map[item_id] = result

        # 按得分排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [{**item_map[id_], "rrf_score": scores[id_]} for id_ in sorted_ids[:top_k]]

    def _linear_fusion(
        self, feature_results: list[dict], vector_results: list[dict], alpha: float, top_k: int
    ) -> list[dict]:
        """线性融合 feature 和 vector 结果"""
        scores: dict[str, float] = {}
        item_map: dict[str, dict] = {}

        # Feature 得分 (归一化)
        feature_scores = self._normalize_scores(feature_results)
        for item_id, score in feature_scores.items():
            scores[item_id] = scores.get(item_id, 0.0) + alpha * score
            item_map[item_id] = next(
                r for r in feature_results if r.get("id", r.get("data_id")) == item_id
            )

        # Vector 得分 (归一化)
        vector_scores = self._normalize_scores(vector_results)
        for item_id, score in vector_scores.items():
            scores[item_id] = scores.get(item_id, 0.0) + (1 - alpha) * score
            if item_id not in item_map:
                item_map[item_id] = next(
                    r for r in vector_results if r.get("id", r.get("data_id")) == item_id
                )

        # 按得分排序
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [{**item_map[id_], "linear_score": scores[id_]} for id_ in sorted_ids[:top_k]]

    def _normalize_scores(self, results: list[dict]) -> dict[str, float]:
        """归一化得分到 [0, 1]"""
        scores = {}

        for i, result in enumerate(results):
            item_id = result.get("id", result.get("data_id"))
            # 使用排名得分
            scores[item_id] = 1.0 / (i + 1)

        if not scores:
            return scores

        # Min-Max 归一化
        max_score = max(scores.values())
        min_score = min(scores.values())

        if max_score == min_score:
            return dict.fromkeys(scores.keys(), 1.0)

        normalized = {}
        for item_id, score in scores.items():
            normalized[item_id] = (score - min_score) / (max_score - min_score)

        return normalized
