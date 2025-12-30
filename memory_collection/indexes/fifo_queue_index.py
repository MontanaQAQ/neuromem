"""FIFOQueueIndex - FIFO 队列索引

固定容量的先进先出队列索引，用于实现短期记忆（STM）。

设计原则：
- 固定最大容量，超出时自动淘汰最旧数据
- 只存 data_id，不存原始数据
- 支持快速检查是否在队列中
- 查询返回队列头部（最旧）的数据

使用场景：
- 短期记忆（STM）
- 最近对话历史
- 滑动窗口缓存

配置示例：
    config = {
        "max_size": 100,  # 最大容量（必需）
    }
"""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any

from .base_index import BaseIndex


class FIFOQueueIndex(BaseIndex):
    """
    FIFO 队列索引 - 固定容量的先进先出队列

    Attributes:
        max_size: 最大容量
        queue: 双端队列，存储 data_id
        id_set: 快速查找集合
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 FIFO 队列索引

        Args:
            config: 配置字典，必须包含 "max_size" 键

        Raises:
            ValueError: 如果未提供 max_size 或 max_size <= 0
        """
        super().__init__(config)

        # 设置索引类型
        self.index_type = "fifo"

        if "max_size" not in self.config:
            msg = "FIFOQueueIndex requires 'max_size' in config"
            raise ValueError(msg)

        self.max_size = self.config["max_size"]
        if self.max_size <= 0:
            msg = f"max_size must be > 0, got {self.max_size}"
            raise ValueError(msg)

        # 使用 deque 实现高效的 FIFO 队列
        self.queue: deque[str] = deque(maxlen=self.max_size)
        # 使用 set 实现 O(1) 的成员检查
        self.id_set: set[str] = set()

    def add(self, data_id: str, text: str, metadata: dict[str, Any]) -> None:
        """
        添加数据到队列

        Args:
            data_id: 数据 ID
            text: 原始文本（FIFO 不使用）
            metadata: 元数据（FIFO 不使用）

        Note:
            - 如果队列已满，自动淘汰最旧的数据（队列头）
            - 如果 data_id 已存在，先移除旧位置再添加到队尾
        """
        # 如果已存在，先移除（避免重复）
        if data_id in self.id_set:
            # 从队列中移除（需要创建新队列）
            self.queue = deque((id_ for id_ in self.queue if id_ != data_id), maxlen=self.max_size)
            self.id_set.remove(data_id)

        # 添加到队尾（deque 自动处理容量限制）
        # 如果队列已满，deque 会自动弹出队列头（最旧）
        if len(self.queue) == self.max_size:
            # 记录被淘汰的 ID
            evicted_id = self.queue[0]
            self.id_set.discard(evicted_id)

        self.queue.append(data_id)
        self.id_set.add(data_id)

    def remove(self, data_id: str) -> None:
        """
        从队列移除数据

        Args:
            data_id: 数据 ID

        Note:
            如果 data_id 不存在，不做任何操作
        """
        if data_id not in self.id_set:
            return

        # 从队列中移除
        self.queue = deque((id_ for id_ in self.queue if id_ != data_id), maxlen=self.max_size)
        self.id_set.remove(data_id)

    def query(self, query: Any = None, **params: Any) -> list[str]:
        """
        查询队列（返回所有数据，按插入顺序）

        Args:
            query: 查询内容（FIFO 不使用，传入 None）
            **params: 查询参数
                - top_k: 返回最旧的 k 条数据（可选，默认全部）

        Returns:
            data_id 列表（从旧到新）

        Examples:
            >>> index.query()  # 返回所有数据
            >>> index.query(top_k=5)  # 返回最旧的 5 条
        """
        top_k = params.get("top_k")

        # 返回所有数据（按插入顺序：旧 -> 新）
        result = list(self.queue)

        if top_k is not None and top_k > 0:
            return result[:top_k]

        return result

    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在队列中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在（O(1) 时间复杂度）
        """
        return data_id in self.id_set

    def size(self) -> int:
        """
        获取队列中的数据条数

        Returns:
            数据条数
        """
        return len(self.queue)

    def save(self, path: Path | str) -> bool:
        """
        持久化队列到磁盘

        Args:
            path: 保存路径（可以是文件或目录，目录时会创建 index.json）

        Returns:
            是否保存成功

        Note:
            保存格式：{"max_size": int, "queue": [id1, id2, ...]}
        """
        try:
            path = Path(path)

            # 如果是目录，使用默认文件名
            if path.is_dir() or not path.suffix:
                path = path / "index.json"

            path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "max_size": self.max_size,
                "queue": list(self.queue),
            }

            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception:
            return False

    def load(self, path: Path | str) -> bool:
        """
        从磁盘加载队列

        Args:
            path: 加载路径（可以是文件或目录，目录时会查找 index.json）

        Returns:
            是否加载成功
        """
        try:
            path = Path(path)

            # 如果是目录，使用默认文件名
            if path.is_dir():
                path = path / "index.json"

            if not path.exists():
                return False

            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            # 恢复配置
            self.max_size = data.get("max_size", 100)
            self.queue = deque(data.get("queue", []), maxlen=self.max_size)
            self.id_set = set(self.queue)
            self.config["max_size"] = self.max_size

            return True
        except Exception:
            return False

    def clear(self) -> None:
        """清空队列"""
        self.queue.clear()
        self.id_set.clear()
