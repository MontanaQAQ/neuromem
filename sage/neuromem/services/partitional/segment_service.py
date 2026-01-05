"""
SegmentService - 分段记忆服务

使用场景:
- 长对话历史管理（按时间/话题分段）
- 多轮对话上下文切换
- 会议/文档章节管理

设计:
- 索引: Segment 索引（时间窗口、话题聚类）
- 特点: 自动分段，支持多层级检索
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..base_service import BaseMemoryService
from ..registry import MemoryServiceRegistry

if TYPE_CHECKING:
    from ...memory_collection import UnifiedCollection

logger = logging.getLogger(__name__)


@MemoryServiceRegistry.register("segment")
class SegmentService(BaseMemoryService):
    """
    分段记忆服务

    特性:
    - 自动按时间窗口或话题切分数据
    - 支持按段检索（最近一段、指定段）
    - 适合长期对话、多轮交互场景

    配置参数:
        segment_strategy: 分段策略 ["time", "topic", "hybrid"]（默认 "time"）
        time_window: 时间窗口（秒，默认 3600 = 1小时）
        max_segment_size: 单段最大数据量（默认 100）
        topic_threshold: 话题相似度阈值（仅 topic/hybrid 模式，默认 0.7）
        embedder: Embedding 模型（topic/hybrid 模式需要）

    使用示例:
        >>> # 按时间分段
        >>> service = SegmentService(collection, {
        ...     "segment_strategy": "time",
        ...     "time_window": 1800  # 30分钟
        ... })
        >>> service.insert("消息1")
        >>> service.insert("消息2")
        >>> recent_segment = service.get_current_segment()

        >>> # 按话题分段
        >>> service = SegmentService(collection, {
        ...     "segment_strategy": "topic",
        ...     "topic_threshold": 0.8,
        ...     "embedder": embedder
        ... })
    """

    def __init__(self, collection: UnifiedCollection, config: dict[str, Any] | None = None):
        """
        初始化分段服务

        Args:
            collection: UnifiedCollection 实例
            config: 配置字典
                - segment_strategy: "time", "topic", "hybrid"
                - time_window: 时间窗口（秒）
                - max_segment_size: 单段最大数据量
                - topic_threshold: 话题相似度阈值
                - embedder: Embedding 模型（可选，topic 模式需要）
        """
        # 默认配置
        default_config = {
            "segment_strategy": "time",
            "time_window": 3600,  # 1小时
            "max_segment_size": 100,
            "topic_threshold": 0.7,
        }

        merged_config = {**default_config, **(config or {})}

        # 先初始化父类（这会初始化 logger）
        super().__init__(collection, merged_config)

        # 验证 embedder（如果是 topic 或 hybrid 模式）
        strategy = merged_config["segment_strategy"]
        if strategy in ["topic", "hybrid"]:
            # Topic和Hybrid策略目前会在SegmentIndex中自动回退到time
            # SegmentIndex会发出警告并处理回退逻辑
            self.logger.info(
                f"Strategy '{strategy}' is experimental and will fall back to 'time' mode. "
                "Embedder is optional in current implementation."
            )
            # embedder可选（虽然当前不使用，但保留以便未来扩展）
            if "embedder" not in merged_config:
                merged_config["embedder"] = None

        # 当前段 ID（用于跟踪最新段）
        self._current_segment_id: str | None = None

    def _setup_indexes(self) -> None:
        """
        配置 Segment 索引

        创建分段索引，支持时间、话题或混合分段策略。
        """
        strategy = self.config["segment_strategy"]
        time_window = self.config["time_window"]
        max_size = self.config["max_segment_size"]
        topic_threshold = self.config.get("topic_threshold", 0.7)
        vector_dim = self.config.get("vector_dim", 1024)  # 向量维度

        self.collection.add_index(
            name="segment_index",
            index_type="segment",
            config={
                "strategy": strategy,
                "time_window": time_window,
                "max_segment_size": max_size,
                "topic_threshold": topic_threshold,
                "vector_dim": vector_dim,  # 传递向量维度
            },
        )

        self.logger.info(
            f"Created Segment index with strategy={strategy}, "
            f"time_window={time_window}s, max_size={max_size}"
        )

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
        插入数据到分段索引（统一接口）

        Args:
            entry: 原始文本内容
            vector: 向量（从调用者传入）
            metadata: 元数据字典
            insert_mode: 插入模式（默认 "passive"）
            insert_params: 插入参数
                - timestamp: 自定义时间戳（默认当前时间）
                - force_new_segment: 强制创建新段（默认 False）

        Returns:
            data_id: 生成的数据 ID

        Note:
            - Vector 由调用者提供（不在服务内部计算）
            - 自动判断是否需要创建新段
        """
        # 确保 insert_params 不为 None
        insert_params = insert_params or {}
        metadata = metadata or {}

        # 扩展元数据
        extended_metadata = {
            **metadata,
            "timestamp": insert_params.get("timestamp", datetime.now().isoformat()),
        }

        # 向量添加到 metadata（UnifiedCollection 需要）
        if vector is not None:
            extended_metadata["vector"] = vector

        # 检查是否需要强制创建新段
        force_new = insert_params.get("force_new_segment", False)
        if force_new:
            # 将segment_start标记放到metadata中，SegmentIndex会通过kwargs读取
            extended_metadata["segment_start"] = True

        data_id = self.collection.insert(
            text=entry, metadata=extended_metadata, index_names=["segment_index"]
        )

        # 更新当前段 ID
        if self._current_segment_id is None:
            self._current_segment_id = data_id

        self.logger.debug(f"Inserted {data_id[:8]}... to segment index")
        return data_id

    def _should_create_new_segment(self, text: str, metadata: dict[str, Any]) -> bool:
        """
        判断是否需要创建新段

        Args:
            text: 当前文本
            metadata: 当前元数据

        Returns:
            是否需要创建新段
        """
        strategy = self.config["segment_strategy"]

        if strategy == "time":
            return self._check_time_window(metadata)
        elif strategy == "topic":
            return self._check_topic_shift(text, metadata)
        elif strategy == "hybrid":
            # 满足任一条件即创建新段
            return self._check_time_window(metadata) or self._check_topic_shift(text, metadata)
        else:
            return False

    def _check_time_window(self, metadata: dict[str, Any]) -> bool:
        """检查时间窗口是否超出"""
        if self._current_segment_id is None:
            return False

        # 获取当前段的第一条数据
        first_item = self.collection.get(self._current_segment_id)
        if not first_item:
            return False

        # 比较时间戳
        first_timestamp = datetime.fromisoformat(
            first_item["metadata"].get("timestamp", datetime.now().isoformat())
        )
        current_timestamp = datetime.fromisoformat(
            metadata.get("timestamp", datetime.now().isoformat())
        )

        time_diff = (current_timestamp - first_timestamp).total_seconds()
        return time_diff > self.config["time_window"]

    def _check_topic_shift(self, text: str, metadata: dict[str, Any]) -> bool:
        """检查话题是否切换"""
        if self._current_segment_id is None:
            return False

        # 获取当前段的最后几条数据
        segment_items = self.get_current_segment(limit=5)
        if not segment_items:
            return False

        # 计算当前文本与段内数据的平均相似度
        current_embedding = metadata.get("embedding")
        if current_embedding is None:
            current_embedding = self._get_embeddings([text])[0]

        similarities = []
        for item in segment_items:
            item_embedding = item.get("metadata", {}).get("embedding")
            if item_embedding is not None:
                # 简化：使用余弦相似度（实际应调用相似度计算函数）
                similarity = self._cosine_similarity(current_embedding, item_embedding)
                similarities.append(similarity)

        if not similarities:
            return False

        avg_similarity = sum(similarities) / len(similarities)
        threshold = self.config["topic_threshold"]

        # 相似度低于阈值，认为话题切换
        return avg_similarity < threshold

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度（简化版）"""
        # 简化实现，实际应使用 numpy 或专用库
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        return dot_product / (norm1 * norm2 + 1e-10)

    def retrieve(
        self,
        query: str | None = None,
        vector: Any = None,
        metadata: dict[str, Any] | None = None,
        top_k: int = 10,
        hints: dict[str, Any] | None = None,
        threshold: float | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索数据（跨段检索）

        Args:
            query: 查询文本
            vector: 查询向量（可选，暂不使用）
            metadata: 元数据过滤条件（可选）
            top_k: 返回的数据条数（默认10）
            hints: 检索策略提示（可选）
            threshold: 相似度阈值（可选）
            **kwargs: 额外参数
                - segment_id: 指定段ID（可选，为None则搜索所有段）
                - time_range: 时间范围(start, end)（可选）

        Returns:
            结果列表: [{"id": "...", "text": "...", "metadata": {...}, "score": 1.0}, ...]
        """
        # 从 Segment 索引查询（跨段检索，返回所有段的数据）
        data_ids = self.collection.query_by_index(
            index_name="segment_index",
            query=None,  # 传 None 让索引决定行为
            top_k=top_k,
            all_segments=True,  # 检索所有段的数据
            **kwargs,
        )

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
                        "score": 1.0,  # Segment 检索不计算相似度分数
                    }
                )

        self.logger.debug(f"Retrieved {len(results)} items from segment index")
        return results

    def get_current_segment(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        获取当前段的数据

        Args:
            limit: 最大返回数量（默认 50）

        Returns:
            当前段的数据列表
        """
        # 查询当前段的所有数据（不传segment_id，让SegmentIndex返回current_segment）
        return self.retrieve(query=None, top_k=limit)

    def get_segment_by_time(
        self, start_time: datetime, end_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """
        按时间范围获取段

        Args:
            start_time: 起始时间
            end_time: 结束时间（可选，默认当前时间）

        Returns:
            时间范围内的数据列表
        """
        end_time = end_time or datetime.now()

        return self.retrieve(
            query=None,
            top_k=1000,
            time_range=(start_time.isoformat(), end_time.isoformat()),
        )

    def create_new_segment(self, reason: str = "manual") -> None:
        """
        手动创建新段

        Args:
            reason: 创建原因（记录到日志）

        Note:
            下次insert()时会自动创建新段，无需在此处调用SegmentIndex
        """
        # 通过在SegmentIndex内部调用_create_new_segment()来创建新段
        # 我们需要访问SegmentIndex并调用其_create_new_segment()
        segment_index = self.collection.indexes.get("segment_index")
        if segment_index is not None:
            segment_index._create_new_segment()  # noqa: SLF001
            self.logger.info(f"Created new segment (reason: {reason})")
        else:
            self.logger.warning("Segment index not found, cannot create new segment")

    def get_all_segments(self) -> list[dict[str, Any]]:
        """
        获取所有段的元信息

        Returns:
            段信息列表: [{"segment_id": "...", "start_time": "...", "item_count": 10}, ...]
        """
        # 查询所有数据
        all_data = self.retrieve(query=None, top_k=10000)

        # 按段分组
        segments: dict[str, dict[str, Any]] = {}
        current_segment: str | None = None

        for item in all_data:
            # 判断是否是段起始
            if item["metadata"].get("segment_start"):
                current_segment = item["id"]
                segments[current_segment] = {
                    "segment_id": current_segment,
                    "start_time": item["metadata"].get("timestamp"),
                    "item_count": 0,
                    "items": [],
                }

            # 添加到当前段
            if current_segment and current_segment in segments:
                segments[current_segment]["item_count"] += 1
                segments[current_segment]["items"].append(item["id"])

        self.logger.info(f"Found {len(segments)} segments")
        return list(segments.values())
