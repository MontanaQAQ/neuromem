"""
FeatureQueueSegmentCombinationService - 特征+队列+分段组合服务

设计要点:
1. 三个索引组合: Feature (BM25) + FIFOQueue + Segment (时间分段)
2. 支持特征提取和时间/主题分段
3. FIFO队列提供时序信息，Segment提供上下文切分

使用场景:
- 对话历史管理
- 需要时间窗口检索
- 按主题/会话切分的场景

配置示例:
    config = {
        "fifo_max_size": 100,
        "segment_strategy": "time",  # time/keyword/topic
        "segment_threshold": 3600,  # 1小时
        "enable_feature_extraction": True,
        "combination_strategy": "weighted",
        "weights": {
            "feature_index": 0.4,
            "fifo_index": 0.3,
            "segment_index": 0.3,
        },
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


@MemoryServiceRegistry.register("feature_queue_segment_combination")
class FeatureQueueSegmentCombinationService(BaseMemoryService):
    """
    特征 + FIFO队列 + 分段组合服务

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置
        fifo_max_size: FIFO队列最大大小
        segment_strategy: 分段策略
        segment_threshold: 分段阈值
        enable_feature_extraction: 是否启用特征提取
        combination_strategy: 组合策略
        weights: 各索引权重
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化组合服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - fifo_max_size: FIFO队列大小 (默认 100)
                - segment_strategy: time/keyword/topic (默认 time)
                - segment_threshold: 分段阈值 (默认 3600秒)
                - enable_feature_extraction: 启用特征提取 (默认 True)
                - combination_strategy: 组合策略 (默认 weighted)
                - weights: 各索引权重字典
        """
        # 配置参数 - 必须在 super().__init__() 之前设置，因为 _setup_indexes() 会使用它们
        config = config or {}
        self.fifo_max_size = config.get("fifo_max_size", 100)
        self.segment_strategy = config.get("segment_strategy", "time")
        self.segment_threshold = config.get("segment_threshold", 3600)
        self.enable_feature_extraction = config.get("enable_feature_extraction", True)
        self.combination_strategy = config.get("combination_strategy", "weighted")
        self.weights = config.get(
            "weights",
            {
                "feature_index": 0.4,
                "fifo_index": 0.3,
                "segment_index": 0.3,
            },
        )

        super().__init__(collection, config)

        self.logger.info(
            f"FeatureQueueSegmentCombinationService initialized: "
            f"fifo_max_size={self.fifo_max_size}, "
            f"segment_strategy={self.segment_strategy}, "
            f"combination_strategy={self.combination_strategy}"
        )

    def _setup_indexes(self):
        """配置所需索引"""
        # 1. Feature索引 (BM25)
        self.collection.add_index(name="feature_index", index_type="bm25", config={})

        # 2. FIFO Queue索引
        self.collection.add_index(
            name="fifo_index", index_type="fifo", config={"max_size": self.fifo_max_size}
        )

        # 3. Segment索引
        segment_config = {
            "strategy": self.segment_strategy,
            "threshold": self.segment_threshold,
        }
        self.collection.add_index(name="segment_index", index_type="segment", config=segment_config)

        self.logger.info("Indexes configured: feature_index, fifo_index, segment_index")

    def insert(
        self,
        entry: str,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        *,
        insert_mode: str = "passive",
        insert_params: dict[str, Any] | None = None,
    ) -> str:
        """
        插入数据到三个索引（统一接口）

        Args:
            entry: 文本内容
            vector: 向量（从调用者传入）
            metadata: 元数据
            insert_mode: 插入模式（默认 "passive"）
            insert_params: 插入参数

        Returns:
            str: 数据ID
        """
        metadata = metadata or {}
        # 特征提取
        if self.enable_feature_extraction:
            features = self._extract_features(entry)
            metadata["features"] = features

        # 向量添加到 metadata（UnifiedCollection 需要）
        if vector is not None:
            metadata["vector"] = vector

        # 插入到 Collection (自动同步到所有索引)
        data_id = self.collection.insert(
            text=entry,
            metadata=metadata,
            index_names=["feature_index", "fifo_index", "segment_index"],
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
            vector: 查询向量（可选）
            metadata: 元数据过滤条件（可选）
            top_k: 返回结果数（默认5）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 其他参数
                - strategy: 组合策略(weighted/voting/cascade/recent)
                - segment_id: 指定分段ID(可选)

        Returns:
            list[dict]: 检索结果列表
        """
        strategy = kwargs.get("strategy") or self.combination_strategy
        segment_id = kwargs.get("segment_id")

        if strategy == "weighted":
            return self._retrieve_weighted(query or "", top_k, segment_id, **kwargs)
        elif strategy == "voting":
            return self._retrieve_voting(query or "", top_k, segment_id, **kwargs)
        elif strategy == "cascade":
            return self._retrieve_cascade(query or "", top_k, segment_id, **kwargs)
        elif strategy == "recent":
            return self._retrieve_recent(query or "", top_k, segment_id, **kwargs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _retrieve_weighted(
        self, query: str, top_k: int, segment_id: str | None = None, **kwargs
    ) -> list[dict]:
        """加权融合检索"""
        # Feature检索
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        # FIFO检索 (最近N个)
        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        # Segment检索
        segment_kwargs = {"segment_id": segment_id} if segment_id else {}
        segment_results = self.collection.retrieve(
            index_name="segment_index", query=query, top_k=top_k * 2, **segment_kwargs
        )

        # 加权融合
        return self._weighted_fusion(
            {
                "feature_index": feature_results,
                "fifo_index": fifo_results,
                "segment_index": segment_results,
            },
            self.weights,
            top_k,
        )

    def _retrieve_voting(
        self, query: str, top_k: int, segment_id: str | None = None, **kwargs
    ) -> list[dict]:
        """投票融合检索 - 出现在多个索引结果中的项目优先"""
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        segment_kwargs = {"segment_id": segment_id} if segment_id else {}
        segment_results = self.collection.retrieve(
            index_name="segment_index", query=query, top_k=top_k * 2, **segment_kwargs
        )

        # 投票计数
        votes: dict[str, int] = {}
        item_map: dict[str, dict] = {}

        for result in feature_results + fifo_results + segment_results:
            item_id = result.get("id", result.get("data_id"))
            votes[item_id] = votes.get(item_id, 0) + 1
            item_map[item_id] = result

        # 按投票数排序
        sorted_ids = sorted(votes.keys(), key=lambda x: votes[x], reverse=True)
        return [item_map[id_] for id_ in sorted_ids[:top_k]]

    def _retrieve_cascade(
        self, query: str, top_k: int, segment_id: str | None = None, **kwargs
    ) -> list[dict]:
        """级联检索 - 先Segment，再Feature，最后FIFO"""
        # 1. 先从Segment检索
        segment_kwargs = {"segment_id": segment_id} if segment_id else {}
        segment_results = self.collection.retrieve(
            index_name="segment_index", query=query, top_k=top_k, **segment_kwargs
        )

        if len(segment_results) >= top_k:
            return segment_results[:top_k]

        # 2. 补充Feature检索
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k
        )

        combined = self._merge_results(segment_results, feature_results, top_k)
        if len(combined) >= top_k:
            return combined[:top_k]

        # 3. 补充FIFO检索
        fifo_results = self.collection.retrieve(index_name="fifo_index", query=query, top_k=top_k)

        return self._merge_results(combined, fifo_results, top_k)[:top_k]

    def _retrieve_recent(
        self, query: str, top_k: int, segment_id: str | None = None, **kwargs
    ) -> list[dict]:
        """优先返回最近的数据"""
        fifo_results = self.collection.retrieve(index_name="fifo_index", query=query, top_k=top_k)
        return fifo_results[:top_k]

    def get_current_segment(self, top_k: int = 10) -> list[dict]:
        """获取当前分段的数据"""
        results = self.collection.retrieve(
            index_name="segment_index",
            query="",  # 空查询返回当前segment
            top_k=top_k,
        )
        return results

    def get_recent_items(self, count: int = 10) -> list[dict]:
        """获取最近的N个项目"""
        results = self.collection.retrieve(index_name="fifo_index", query="", top_k=count)
        return results

    # ========== 工具方法 ==========

    def _extract_features(self, text: str) -> dict[str, Any]:
        """提取文本特征"""
        return {
            "word_count": len(text.split()) if text.strip() else 0,
            "char_count": len(text),
        }

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

    def _merge_results(self, results1: list[dict], results2: list[dict], top_k: int) -> list[dict]:
        """合并去重两个结果集"""
        seen_ids = set()
        merged = []

        for result in results1 + results2:
            item_id = result.get("id", result.get("data_id"))
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                merged.append(result)
                if len(merged) >= top_k:
                    break

        return merged
