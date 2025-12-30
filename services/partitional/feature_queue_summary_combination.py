"""
FeatureQueueSummaryCombinationService - 特征+队列+摘要组合服务

设计要点:
1. 三个索引组合: Feature (BM25) + FIFOQueue + Summary (摘要FIFO)
2. 自动摘要生成和特征提取
3. FIFO队列提供时序信息，Summary提供压缩信息

使用场景:
- 对话摘要管理
- 需要压缩历史信息
- 快速检索关键信息

配置示例:
    config = {
        "fifo_max_size": 100,
        "summary_max_size": 20,
        "summary_min_length": 10,  # 最小文本长度才生成摘要
        "enable_feature_extraction": True,
        "enable_summary_generation": True,
        "combination_strategy": "weighted",
        "weights": {
            "feature_index": 0.4,
            "fifo_index": 0.3,
            "summary_index": 0.3,
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


@MemoryServiceRegistry.register("feature_queue_summary_combination")
class FeatureQueueSummaryCombinationService(BaseMemoryService):
    """
    特征 + FIFO队列 + 摘要组合服务

    Attributes:
        collection: UnifiedCollection 实例
        config: Service 配置
        fifo_max_size: FIFO队列最大大小
        summary_max_size: 摘要队列大小
        summary_min_length: 生成摘要的最小文本长度
        enable_feature_extraction: 是否启用特征提取
        enable_summary_generation: 是否启用摘要生成
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
                - summary_max_size: 摘要队列大小 (默认 20)
                - summary_min_length: 最小摘要长度 (默认 10)
                - enable_feature_extraction: 启用特征提取 (默认 True)
                - enable_summary_generation: 启用摘要生成 (默认 True)
                - combination_strategy: 组合策略 (默认 weighted)
                - weights: 各索引权重字典
        """
        # 配置参数 - 必须在 super().__init__() 之前设置
        config = config or {}
        self.fifo_max_size = config.get("fifo_max_size", 100)
        self.summary_max_size = config.get("summary_max_size", 20)
        self.summary_min_length = config.get("summary_min_length", 10)
        self.enable_feature_extraction = config.get("enable_feature_extraction", True)
        self.enable_summary_generation = config.get("enable_summary_generation", True)
        self.combination_strategy = config.get("combination_strategy", "weighted")
        self.weights = config.get(
            "weights",
            {
                "feature_index": 0.4,
                "fifo_index": 0.3,
                "summary_index": 0.3,
            },
        )

        super().__init__(collection, config)

        self.logger.info(
            f"FeatureQueueSummaryCombinationService initialized: "
            f"fifo_max_size={self.fifo_max_size}, "
            f"summary_max_size={self.summary_max_size}, "
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

        # 3. Summary FIFO索引
        self.collection.add_index(
            name="summary_index", index_type="fifo", config={"max_size": self.summary_max_size}
        )

        self.logger.info("Indexes configured: feature_index, fifo_index, summary_index")

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
        插入数据到三个索引（统一接口）

        Args:
            entry: 文本内容
            vector: 向量（可选，未使用）
            metadata: 元数据（可选）
            insert_mode: 插入模式（未使用）
            insert_params: 插入参数（未使用）

        Returns:
            str: 数据ID
        """
        metadata = metadata or {}

        # 兼容旧接口：如果直接传 text 参数
        text = entry

        # 特征提取
        if self.enable_feature_extraction:
            features = self._extract_features(text)
            metadata["features"] = features

        # 摘要生成
        summary_text = text
        if self.enable_summary_generation and len(text) >= self.summary_min_length:
            summary_text = self._generate_summary(text)
            metadata["summary"] = summary_text

        # 插入到 Feature 和 FIFO 索引
        data_id = self.collection.insert(
            text=text, metadata=metadata, index_names=["feature_index", "fifo_index"]
        )

        # 如果有摘要，插入到 Summary 索引
        if self.enable_summary_generation and len(text) >= self.summary_min_length:
            self.collection.insert(
                text=summary_text,
                metadata={**metadata, "original_id": data_id, "is_summary": True},
                index_names=["summary_index"],
            )

        self.logger.debug(
            f"Inserted data_id={data_id}, text_len={len(text)}, "
            f"has_summary={len(text) >= self.summary_min_length}"
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
                - include_summaries: 是否包含摘要结果

        Returns:
            list[dict]: 检索结果列表
        """
        strategy = kwargs.get("strategy") or self.combination_strategy
        include_summaries = kwargs.get("include_summaries", False)

        if strategy == "weighted":
            return self._retrieve_weighted(query, top_k, include_summaries, **kwargs)
        elif strategy == "voting":
            return self._retrieve_voting(query, top_k, include_summaries, **kwargs)
        elif strategy == "cascade":
            return self._retrieve_cascade(query, top_k, include_summaries, **kwargs)
        elif strategy == "recent":
            return self._retrieve_recent(query, top_k, **kwargs)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _retrieve_weighted(
        self, query: str, top_k: int, include_summaries: bool = False, **kwargs
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

        # Summary检索
        summary_results = self.collection.retrieve(
            index_name="summary_index", query=query, top_k=top_k * 2
        )

        # 加权融合
        fused_results = self._weighted_fusion(
            {
                "feature_index": feature_results,
                "fifo_index": fifo_results,
                "summary_index": summary_results,
            },
            self.weights,
            top_k,
        )

        # 过滤摘要项 (除非明确要求)
        if not include_summaries:
            fused_results = [
                r for r in fused_results if not r.get("metadata", {}).get("is_summary", False)
            ]

        return fused_results[:top_k]

    def _retrieve_voting(
        self, query: str, top_k: int, include_summaries: bool = False, **kwargs
    ) -> list[dict]:
        """投票融合检索"""
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k * 2
        )

        fifo_results = self.collection.retrieve(
            index_name="fifo_index", query=query, top_k=top_k * 2
        )

        summary_results = self.collection.retrieve(
            index_name="summary_index", query=query, top_k=top_k * 2
        )

        # 投票计数
        votes: dict[str, int] = {}
        item_map: dict[str, dict] = {}

        for result in feature_results + fifo_results + summary_results:
            item_id = result.get("id", result.get("data_id"))
            votes[item_id] = votes.get(item_id, 0) + 1
            item_map[item_id] = result

        # 按投票数排序
        sorted_ids = sorted(votes.keys(), key=lambda x: votes[x], reverse=True)
        voting_results = [item_map[id_] for id_ in sorted_ids]

        # 过滤摘要项
        if not include_summaries:
            voting_results = [
                r for r in voting_results if not r.get("metadata", {}).get("is_summary", False)
            ]

        return voting_results[:top_k]

    def _retrieve_cascade(
        self, query: str, top_k: int, include_summaries: bool = False, **kwargs
    ) -> list[dict]:
        """级联检索 - 先Summary，再Feature，最后FIFO"""
        # 1. 先从Summary检索
        summary_results = self.collection.retrieve(
            index_name="summary_index", query=query, top_k=top_k
        )

        if not include_summaries:
            # 获取原始ID对应的完整文档
            original_ids = [
                r.get("metadata", {}).get("original_id")
                for r in summary_results
                if r.get("metadata", {}).get("original_id")
            ]
            cascade_results = [
                self.collection.get(oid) for oid in original_ids if self.collection.get(oid)
            ]
        else:
            cascade_results = summary_results

        if len(cascade_results) >= top_k:
            return cascade_results[:top_k]

        # 2. 补充Feature检索
        feature_results = self.collection.retrieve(
            index_name="feature_index", query=query, top_k=top_k
        )

        combined = self._merge_results(cascade_results, feature_results, top_k)
        if len(combined) >= top_k:
            return combined[:top_k]

        # 3. 补充FIFO检索
        fifo_results = self.collection.retrieve(index_name="fifo_index", query=query, top_k=top_k)

        return self._merge_results(combined, fifo_results, top_k)[:top_k]

    def _retrieve_recent(self, query: str, top_k: int, **kwargs) -> list[dict]:
        """优先返回最近的数据"""
        fifo_results = self.collection.retrieve(index_name="fifo_index", query=query, top_k=top_k)
        return fifo_results[:top_k]

    def get_recent_items(self, count: int = 10) -> list[dict]:
        """获取最近的N个项目"""
        results = self.collection.retrieve(index_name="fifo_index", query="", top_k=count)
        return results

    def get_summaries(self, count: int = 10) -> list[dict]:
        """获取最近的摘要"""
        results = self.collection.retrieve(index_name="summary_index", query="", top_k=count)
        return results

    # ========== 工具方法 ==========

    def _extract_features(self, text: str) -> dict[str, Any]:
        """提取文本特征"""
        return {
            "word_count": len(text.split()) if text.strip() else 0,
            "char_count": len(text),
        }

    def _generate_summary(self, text: str) -> str:
        """生成文本摘要 (简单实现: 截取前50字符)"""
        max_summary_length = 50
        if len(text) <= max_summary_length:
            return text
        return text[:max_summary_length] + "..."

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
