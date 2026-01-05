"""SegmentIndex - 分段索引

基于时间或内容的分段索引，将数据分组到不同的段中。

设计原则：
- 支持时间分段（基于时间戳）和内容分段（基于关键词）
- 每个段独立管理，支持段内检索
- 自动管理段的创建和维护
- 支持按段查询和跨段查询

使用场景：
- 时间序列数据（按时间分段）
- 主题分组（按关键词分段）
- 会话管理（按会话 ID 分段）

配置示例：
    # 时间分段
    config = {
        "strategy": "time",           # 分段策略：time/keyword/custom
        "segment_size": 100,          # 每段最大条数（时间策略）
        "segment_duration": 3600,     # 每段时长（秒，可选）
    }

    # 关键词分段
    config = {
        "strategy": "keyword",
        "keyword_field": "category",  # 元数据中的关键词字段
    }
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .base_index import BaseIndex

logger = logging.getLogger(__name__)


class SegmentIndex(BaseIndex):
    """
    分段索引 - 按时间或内容将数据分组到段中

    Attributes:
        strategy: 分段策略（time/keyword/custom）
        segment_size: 每段最大条数（时间策略）
        segment_duration: 每段时长（秒，时间策略）
        keyword_field: 关键词字段名（关键词策略）
        segments: 段 ID -> data_id 列表
        data_to_segment: data_id -> 段 ID 映射
        segment_metadata: 段 ID -> 元数据（创建时间、关键词等）
        current_segment_id: 当前活跃段 ID（时间策略）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化分段索引

        Args:
            config: 配置字典
                - strategy: 分段策略（time/keyword/custom，默认 "time"）
                - segment_size: 每段最大条数（默认 100）
                - segment_duration: 每段时长（秒，可选）
                - keyword_field: 关键词字段名（关键词策略，默认 "category"）

        Raises:
            ValueError: 如果策略不支持
        """
        super().__init__(config)

        # 配置参数
        self.strategy = self.config.get("strategy", "time")

        # 扩展支持的策略列表（topic和hybrid暂时回退到time）
        supported_strategies = {"time", "keyword", "custom", "topic", "hybrid"}
        if self.strategy not in supported_strategies:
            msg = f"Unsupported strategy: '{self.strategy}'. Supported: {supported_strategies}"
            raise ValueError(msg)

        # Topic和Hybrid策略暂时回退到time模式
        if self.strategy in {"topic", "hybrid"}:
            logger.warning(
                f"Strategy '{self.strategy}' is experimental and not fully implemented. "
                "Falling back to 'time' strategy. "
                "TODO: Implement topic-based segmentation with embedding similarity."
            )
            self.original_strategy = self.strategy  # 保存原始策略用于调试
            self.strategy = "time"  # 回退到time模式

        self.segment_size = self.config.get("segment_size", 100)
        self.segment_duration = self.config.get("segment_duration", None)
        self.keyword_field = self.config.get("keyword_field", "category")

        # 索引数据
        self.segments: dict[str, list[str]] = {}
        self.data_to_segment: dict[str, str] = {}
        self.segment_metadata: dict[str, dict[str, Any]] = {}
        self.current_segment_id: str | None = None
        self._segment_counter = 0  # 段计数器，确保segment_id唯一

    def _get_timestamp(self) -> float:
        """
        获取当前时间戳（秒）

        Returns:
            当前时间戳
        """
        return datetime.now().timestamp()

    def _create_new_segment(self, segment_id: str | None = None, **metadata: Any) -> str:
        """
        创建新段

        Args:
            segment_id: 段 ID（可选，默认自动生成）
            **metadata: 段元数据

        Returns:
            段 ID
        """
        if segment_id is None:
            # 自动生成段 ID（使用计数器确保唯一性）
            self._segment_counter += 1
            segment_id = f"seg_{self._segment_counter}"

        self.segments[segment_id] = []
        self.segment_metadata[segment_id] = {
            "created_at": self._get_timestamp(),
            **metadata,
        }

        logger.debug(f"Created new segment: {segment_id}")
        return segment_id

    def _get_segment_for_data(self, data_id: str, text: str, metadata: dict[str, Any]) -> str:
        """
        根据策略确定数据应该放入哪个段

        Args:
            data_id: 数据 ID
            text: 原始文本
            metadata: 元数据

        Returns:
            段 ID
        """
        if self.strategy == "time":
            return self._get_time_segment(metadata)
        elif self.strategy == "keyword":
            return self._get_keyword_segment(metadata)
        else:  # custom
            # 自定义策略：使用元数据中的 "segment_id"
            segment_id = metadata.get("segment_id", "default")
            # 确保段存在
            if segment_id not in self.segments:
                self._create_new_segment(segment_id)
            return segment_id

    def _get_time_segment(self, metadata: dict[str, Any]) -> str:
        """
        时间策略：按时间或大小分段

        Args:
            metadata: 元数据（可能包含 timestamp）

        Returns:
            段 ID
        """
        # 如果没有当前段，创建新段
        if self.current_segment_id is None:
            self.current_segment_id = self._create_new_segment()
            return self.current_segment_id

        current_segment = self.segments[self.current_segment_id]

        # 检查是否需要创建新段
        need_new_segment = False

        # 1. 检查大小限制
        if len(current_segment) >= self.segment_size:
            need_new_segment = True

        # 2. 检查时长限制（如果配置了）
        if self.segment_duration is not None:
            segment_created_at = self.segment_metadata[self.current_segment_id]["created_at"]
            current_time = self._get_timestamp()
            if current_time - segment_created_at >= self.segment_duration:
                need_new_segment = True

        # 创建新段
        if need_new_segment:
            self.current_segment_id = self._create_new_segment()

        return self.current_segment_id

    def _get_keyword_segment(self, metadata: dict[str, Any]) -> str:
        """
        关键词策略：按元数据中的关键词分段

        Args:
            metadata: 元数据

        Returns:
            段 ID
        """
        keyword = metadata.get(self.keyword_field, "default")
        segment_id = f"seg_{keyword}"

        # 如果段不存在，创建新段
        if segment_id not in self.segments:
            self._create_new_segment(segment_id, keyword=keyword)

        return segment_id

    def add(
        self, data_id: str, text: str = "", metadata: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """
        添加数据到分段索引

        Args:
            data_id: 数据 ID
            text: 原始文本（分段不使用）
            metadata: 元数据（用于确定段）
            **kwargs: 扩展参数
                - timestamp: 自定义时间戳（可选）
                - embedding: 向量表示（topic策略使用，暂未实现）
                - segment_start: 强制创建新段的标记（可选）

        Note:
            - 如果 data_id 已存在，先移除旧的再添加新的
            - 根据策略自动分配到合适的段
            - timestamp和embedding参数会被保存到metadata中
        """
        metadata = metadata or {}

        # 处理kwargs参数
        if "timestamp" in kwargs:
            metadata["timestamp"] = kwargs["timestamp"]
        if "embedding" in kwargs:
            metadata["embedding"] = kwargs["embedding"]
        if "segment_start" in kwargs and kwargs["segment_start"]:
            # 强制创建新段标记
            self._create_new_segment()

        # 如果已存在，先移除
        if data_id in self.data_to_segment:
            self.remove(data_id)

        # 确定段 ID
        segment_id = self._get_segment_for_data(data_id, text, metadata)

        # 添加到段
        self.segments[segment_id].append(data_id)
        self.data_to_segment[data_id] = segment_id

    def remove(self, data_id: str) -> None:
        """
        从分段索引移除数据

        Args:
            data_id: 数据 ID

        Note:
            如果 data_id 不存在，不做任何操作
        """
        if data_id not in self.data_to_segment:
            return

        segment_id = self.data_to_segment[data_id]

        # 从段中移除
        if segment_id in self.segments:
            self.segments[segment_id] = [id_ for id_ in self.segments[segment_id] if id_ != data_id]

            # 如果段为空，可以选择删除段（可选）
            # 这里保留空段，因为可能还会有新数据加入

        # 从映射中移除
        del self.data_to_segment[data_id]

    def query(self, query: str | None = None, **params: Any) -> list[str]:
        """
        查询分段索引

        Args:
            query: 查询内容
                - 时间策略：None（返回当前段）或段 ID
                - 关键词策略：关键词字符串或段 ID
                - 自定义策略：段 ID
            **params: 查询参数
                - segment_id: 指定段 ID（优先级高于 query）
                - all_segments: 是否返回所有段的数据（默认 False）
                - top_k: 返回结果数量（可选）

        Returns:
            data_id 列表

        Examples:
            >>> index.query()  # 返回当前段
            >>> index.query(segment_id="seg_123")  # 返回指定段
            >>> index.query(all_segments=True)  # 返回所有段
            >>> index.query("sports")  # 关键词策略：返回 "sports" 段
        """
        # 获取参数
        segment_id = params.get("segment_id")
        all_segments = params.get("all_segments", False)
        top_k = params.get("top_k")

        # 确定要查询的段
        if all_segments:
            # 返回所有段的数据
            results = []
            for seg_data_ids in self.segments.values():
                results.extend(seg_data_ids)
        elif segment_id is not None:
            # 返回指定段
            results = self.segments.get(segment_id, [])
        elif query is not None:
            # 根据 query 确定段
            if self.strategy == "keyword":
                segment_id = f"seg_{query}"
                results = self.segments.get(segment_id, [])
            else:
                # 其他策略：query 视为段 ID
                results = self.segments.get(query, [])
        else:
            # 默认：返回当前段（时间策略）
            if self.current_segment_id is not None:
                results = self.segments.get(self.current_segment_id, [])
            else:
                results = []

        # 限制结果数量
        if top_k is not None and top_k > 0:
            results = results[:top_k]

        return results

    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在索引中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在
        """
        return data_id in self.data_to_segment

    def size(self) -> int:
        """
        获取索引中的数据条数

        Returns:
            数据条数
        """
        return len(self.data_to_segment)

    def clear(self) -> None:
        """
        清空索引
        """
        self.segments.clear()
        self.data_to_segment.clear()
        self.segment_metadata.clear()
        self.current_segment_id = None

    def get_segment_info(self) -> dict[str, Any]:
        """
        获取段信息

        Returns:
            段信息字典
                - total_segments: 总段数
                - segments: 段 ID -> 段大小 + 元数据
        """
        segment_info = {
            "total_segments": len(self.segments),
            "segments": {},
        }

        for segment_id, data_ids in self.segments.items():
            segment_info["segments"][segment_id] = {
                "size": len(data_ids),
                "metadata": self.segment_metadata.get(segment_id, {}),
            }

        return segment_info

    def save(self, save_dir: Path) -> None:
        """
        持久化索引到磁盘

        Args:
            save_dir: 保存目录
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 保存配置
        config_path = save_dir / "config.json"
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

        # 保存段数据
        data = {
            "segments": self.segments,
            "data_to_segment": self.data_to_segment,
            "segment_metadata": self.segment_metadata,
            "current_segment_id": self.current_segment_id,
            "segment_counter": self._segment_counter,
        }

        data_path = save_dir / "segments.json"
        with data_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"SegmentIndex saved to {save_dir}")

    def load(self, load_dir: Path) -> None:
        """
        从磁盘加载索引

        Args:
            load_dir: 加载目录
        """
        load_dir = Path(load_dir)

        # 加载配置
        config_path = load_dir / "config.json"
        with config_path.open("r", encoding="utf-8") as f:
            self.config = json.load(f)

        # 更新参数
        self.strategy = self.config.get("strategy", "time")
        self.segment_size = self.config.get("segment_size", 100)
        self.segment_duration = self.config.get("segment_duration", None)
        self.keyword_field = self.config.get("keyword_field", "category")

        # 加载段数据
        data_path = load_dir / "segments.json"
        with data_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.segments = data["segments"]
        self.data_to_segment = data["data_to_segment"]
        self.segment_metadata = data["segment_metadata"]
        self.current_segment_id = data["current_segment_id"]
        self._segment_counter = data.get("segment_counter", 0)

        logger.info(
            f"SegmentIndex loaded from {load_dir}, "
            f"{len(self.segments)} segments, {len(self.data_to_segment)} items"
        )
