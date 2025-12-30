"""
FeatureSummaryVectorStoreCombinationService - 特征+摘要+向量组合服务

设计要点:
1. 三个索引组合: Vector (FAISS) + Feature (BM25) + Summary (FIFO)
2. 支持多种融合策略: weighted, voting, cascade
3. 自动特征提取和摘要生成

使用场景:
- 复杂查询场景
- 多维度检索
- 需要特征提取和摘要的应用

配置示例:
    config = {
        "vector_dim": 768,
        "summary_max_size": 50,
        "combination_strategy": "weighted",
        "weights": {
            "vector_index": 0.5,
            "feature_index": 0.3,
            "summary_index": 0.2,
        },
        "enable_feature_extraction": True,
        "enable_summary_generation": True,
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


@MemoryServiceRegistry.register("feature_summary_vectorstore_combination")
class FeatureSummaryVectorStoreCombinationService(BaseMemoryService):
    """
    特征 + 摘要 + 向量组合服务

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置
        vector_dim: 向量维度
        summary_max_size: 摘要队列最大大小
        combination_strategy: 组合策略 (weighted/voting/cascade)
        weights: 各索引权重
        enable_feature_extraction: 是否启用特征提取
        enable_summary_generation: 是否启用摘要生成
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化组合服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - vector_dim: 向量维度 (默认 768)
                - summary_max_size: 摘要队列大小 (默认 50)
                - combination_strategy: weighted/voting/cascade (默认 weighted)
                - weights: 各索引权重字典 (默认均等)
                - enable_feature_extraction: 是否提取特征 (默认 True)
                - enable_summary_generation: 是否生成摘要 (默认 True)
        """
        # 提取配置参数
        self.vector_dim = config.get("vector_dim", 768) if config else 768
        self.summary_max_size = config.get("summary_max_size", 50) if config else 50
        self.combination_strategy = (
            config.get("combination_strategy", "weighted") if config else "weighted"
        )
        self.weights = (
            config.get(
                "weights",
                {"vector_index": 0.5, "feature_index": 0.3, "summary_index": 0.2},
            )
            if config
            else {"vector_index": 0.5, "feature_index": 0.3, "summary_index": 0.2}
        )
        self.enable_feature_extraction = (
            config.get("enable_feature_extraction", True) if config else True
        )
        self.enable_summary_generation = (
            config.get("enable_summary_generation", True) if config else True
        )

        # 调用父类初始化（会触发 _setup_indexes）
        super().__init__(collection, config)

    def _setup_indexes(self) -> None:
        """
        配置三个索引：向量、特征、摘要

        Note:
            - 使用 add_index 而不是直接访问 IndexFactory
            - Collection 会自动管理索引生命周期
        """
        # 1. 向量索引 (FAISS) - 语义检索
        self.collection.add_index(
            name="vector_index",
            index_type="faiss",
            config={
                "dim": self.vector_dim,
                "metric": "cosine",
                "index_type": "Flat",  # 简单场景使用Flat，大数据量可用IVF
            },
        )

        # 2. 特征索引 (BM25) - 关键词检索
        self.collection.add_index(
            name="feature_index",
            index_type="bm25",
            config={
                "backend": "numba",
                "language": "auto",
            },
        )

        # 3. 摘要索引 (FIFO) - 最近摘要
        self.collection.add_index(
            name="summary_index",
            index_type="fifo",
            config={
                "max_size": self.summary_max_size,
            },
        )

        self.logger.info(
            f"Set up 3 indexes: vector ({self.vector_dim}D), "
            f"feature (BM25), summary (FIFO {self.summary_max_size})"
        )

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
        插入数据（统一接口），自动提取特征和生成摘要

        Args:
            entry: 原始文本
            vector: 向量（必需，由调用者提供）
            metadata: 元数据
            insert_mode: 插入模式（默认 "default"）
            insert_params: 插入参数（可选）
                - skip_feature_extraction: 跳过特征提取 (默认 False)
                - skip_summary_generation: 跳过摘要生成 (默认 False)

        Returns:
            data_id: 数据 ID
        """
        metadata = metadata or {}
        insert_params = insert_params or {}

        # 向量必须由调用者提供
        if vector is None:
            raise ValueError(
                "Vector is required for insert operation. Embedding should be done by caller."
            )

        metadata["vector"] = vector

        # 1. 特征提取（如果启用）
        if self.enable_feature_extraction and not insert_params.get("skip_feature_extraction"):
            features = self._extract_features(entry)
            metadata["features"] = features

        # 2. 摘要生成（如果启用）
        if self.enable_summary_generation and not insert_params.get("skip_summary_generation"):
            summary = self._generate_summary(entry)
            metadata["summary"] = summary

        # 3. 插入到 Collection（会自动添加到所有索引）
        data_id = self.collection.insert(text=entry, metadata=metadata)

        self.logger.debug(
            f"Inserted data '{data_id}' with features={bool(metadata.get('features'))} "
            f"summary={bool(metadata.get('summary'))}"
        )

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
        检索数据，使用多索引融合策略

        Args:
            query: 查询文本
            vector: 查询向量（可选）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数量（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 额外参数
                - strategy: 覆盖默认融合策略(可选)
                - filters: 额外过滤条件(可选)

        Returns:
            结果列表 [{"id": "...", "text": "...", "metadata": {...}, "score": 0.9}, ...]
        """
        strategy = kwargs.get("strategy", self.combination_strategy)

        # 根据策略选择融合方法
        if strategy == "weighted":
            return self._retrieve_weighted(query or "", top_k, **kwargs)
        elif strategy == "voting":
            return self._retrieve_voting(query or "", top_k, **kwargs)
        elif strategy == "cascade":
            return self._retrieve_cascade(query or "", top_k, **kwargs)
        else:
            msg = f"Unknown combination strategy: {strategy}"
            raise ValueError(msg)

    def _retrieve_weighted(self, query: str, top_k: int, **kwargs: Any) -> list[dict[str, Any]]:
        """
        加权融合策略 - 对各索引结果加权求和

        Returns:
            融合后的结果列表
        """
        # 1. 向量索引检索
        vector_ids = self.collection.query_by_index(
            index_name="vector_index",
            query=kwargs.get("query_vector", query),
            top_k=top_k * 2,
        )
        vector_results = self._ids_to_results(vector_ids)

        # 2. 特征索引检索
        feature_ids = self.collection.query_by_index(
            index_name="feature_index", query=query, top_k=top_k * 2
        )
        feature_results = self._ids_to_results(feature_ids)

        # 3. 摘要索引检索（返回最近的摘要）
        summary_ids = self.collection.query_by_index(
            index_name="summary_index", query=None, top_k=top_k
        )
        summary_results = self._ids_to_results(summary_ids)

        # 4. 加权融合
        fused_results = self._weighted_fusion(
            {
                "vector_index": vector_results,
                "feature_index": feature_results,
                "summary_index": summary_results,
            },
            self.weights,
        )

        # 5. 返回 top_k
        return fused_results[:top_k]

    def _retrieve_voting(self, query: str, top_k: int, **kwargs: Any) -> list[dict[str, Any]]:
        """
        投票策略 - 统计各索引返回频次

        Returns:
            投票排序后的结果列表
        """
        # 从三个索引获取候选
        vector_ids = self.collection.query_by_index(
            index_name="vector_index", query=kwargs.get("query_vector", query), top_k=top_k * 2
        )
        vector_results = self._ids_to_results(vector_ids)

        feature_ids = self.collection.query_by_index(
            index_name="feature_index", query=query, top_k=top_k * 2
        )
        feature_results = self._ids_to_results(feature_ids)

        summary_ids = self.collection.query_by_index(
            index_name="summary_index", query=None, top_k=top_k
        )
        summary_results = self._ids_to_results(summary_ids)

        # 统计投票
        vote_count: dict[str, int] = {}
        all_results: dict[str, dict[str, Any]] = {}

        for result in vector_results + feature_results + summary_results:
            data_id = result["id"]
            vote_count[data_id] = vote_count.get(data_id, 0) + 1
            if data_id not in all_results:
                all_results[data_id] = result

        # 按投票数排序
        sorted_ids = sorted(vote_count.keys(), key=lambda x: vote_count[x], reverse=True)

        # 构造结果
        voted_results = []
        for data_id in sorted_ids[:top_k]:
            result = all_results[data_id]
            result["vote_count"] = vote_count[data_id]
            voted_results.append(result)

        return voted_results

    def _retrieve_cascade(self, query: str, top_k: int, **kwargs: Any) -> list[dict[str, Any]]:
        """
        级联策略 - 依次使用索引过滤

        流程: 向量索引 → 特征索引重排 → 摘要索引过滤

        Returns:
            级联过滤后的结果列表
        """
        # 1. 向量索引初筛
        candidate_ids = self.collection.query_by_index(
            index_name="vector_index", query=kwargs.get("query_vector", query), top_k=top_k * 3
        )
        candidates = self._ids_to_results(candidate_ids)

        # 2. 特征索引重排（BM25 打分）
        feature_ids_list = self.collection.query_by_index(
            index_name="feature_index", query=query, top_k=len(candidate_ids)
        )
        feature_results = self._ids_to_results(feature_ids_list)
        feature_ids = {r["id"]: r.get("score", 0.0) for r in feature_results}

        # 重新打分
        for candidate in candidates:
            candidate["feature_score"] = feature_ids.get(candidate["id"], 0.0)

        # 按特征分数重排
        candidates.sort(key=lambda x: x.get("feature_score", 0.0), reverse=True)

        # 3. 摘要索引过滤（只保留在摘要中的）
        summary_ids_list = self.collection.query_by_index(
            index_name="summary_index", query=None, top_k=self.summary_max_size
        )
        summary_ids = set(summary_ids_list)

        # 优先返回在摘要中的结果
        final_results = [c for c in candidates if c["id"] in summary_ids]
        final_results.extend([c for c in candidates if c["id"] not in summary_ids])

        return final_results[:top_k]

    def _weighted_fusion(
        self, results_by_index: dict[str, list[dict[str, Any]]], weights: dict[str, float]
    ) -> list[dict[str, Any]]:
        """
        加权融合多个索引的结果

        Args:
            results_by_index: {index_name: results}
            weights: {index_name: weight}

        Returns:
            融合后的结果列表
        """
        # 收集所有 data_id
        all_ids: set[str] = set()
        for results in results_by_index.values():
            for result in results:
                all_ids.add(result["id"])

        # 计算加权分数
        weighted_scores: dict[str, float] = dict.fromkeys(all_ids, 0.0)
        all_data: dict[str, dict[str, Any]] = {}

        for index_name, results in results_by_index.items():
            weight = weights.get(index_name, 0.0)
            for result in results:
                data_id = result["id"]
                score = result.get("score", 1.0)  # 默认分数 1.0
                weighted_scores[data_id] += score * weight
                if data_id not in all_data:
                    all_data[data_id] = result

        # 按加权分数排序
        sorted_ids = sorted(weighted_scores.keys(), key=lambda x: weighted_scores[x], reverse=True)

        # 构造结果
        fused_results = []
        for data_id in sorted_ids:
            result = all_data[data_id]
            result["weighted_score"] = weighted_scores[data_id]
            fused_results.append(result)

        return fused_results

    def _extract_features(self, text: str) -> dict[str, Any]:
        """
        提取文本特征（简化版）

        Args:
            text: 原始文本

        Returns:
            特征字典
        """
        # TODO: 实现更复杂的特征提取（如 TF-IDF、关键词、实体等）
        # 这里提供简单的统计特征
        words = text.split()
        return {
            "word_count": len(words),
            "char_count": len(text),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0,
        }

    def _generate_summary(self, text: str) -> str:
        """
        生成文本摘要（简化版）

        Args:
            text: 原始文本

        Returns:
            摘要文本
        """
        # TODO: 使用 LLM 或摘要模型生成摘要
        # 这里提供简单的截断策略
        max_length = 100
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."

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
