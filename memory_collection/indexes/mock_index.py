"""MockIndex - 临时 mock 索引实现

⚠️ 仅用于 T1.2 测试！
在 T1.3 完成 BaseIndex 后，会被真实的索引实现替代。

设计目标：
- 提供最小化的索引接口
- 支持基本的 add/remove/query 操作
- 允许 T1.2 的测试通过
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base_index import BaseIndex

if TYPE_CHECKING:
    pass


class MockIndex(BaseIndex):
    """
    临时 Mock 索引 - 用于 T1.2 测试

    实现：
    - 使用简单的 list 存储 data_id
    - query 返回所有 data_id（忽略查询参数）
    - 仅供测试，不提供实际的索引功能
    """

    def __init__(self, index_type: str | None = None, config: dict[str, Any] | None = None):
        """
        初始化 MockIndex

        Args:
            index_type: 索引类型（用于记录，不影响行为）
            config: 索引配置（用于记录，不影响行为）
        """
        # 支持两种调用方式：MockIndex(type, config) 和 MockIndex(config)
        if isinstance(index_type, dict):
            # MockIndex(config) 形式
            super().__init__(index_type)
            self.index_type = "mock"
        else:
            # MockIndex(type, config) 形式
            super().__init__(config or {})
            self.index_type = index_type or "mock"

        self._data_ids: list[str] = []  # 简单存储 data_id 列表

    def add(self, data_id: str, text: str, metadata: dict[str, Any]) -> None:
        """
        添加数据到索引

        Args:
            data_id: 数据 ID
            text: 文本内容（mock 版本不使用）
            metadata: 元数据（mock 版本不使用）
        """
        if data_id not in self._data_ids:
            self._data_ids.append(data_id)

    def remove(self, data_id: str) -> None:
        """
        从索引移除数据

        Args:
            data_id: 数据 ID
        """
        if data_id in self._data_ids:
            self._data_ids.remove(data_id)

    def query(self, query: Any, **params: Any) -> list[str]:
        """
        查询索引（mock 版本返回所有数据）

        Args:
            query: 查询内容（mock 版本忽略）
            **params: 查询参数（支持 top_k）

        Returns:
            data_id 列表
        """
        # 支持 top_k 参数
        top_k = params.get("top_k")
        if top_k is not None:
            return self._data_ids[:top_k]
        return self._data_ids.copy()

    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在索引中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在
        """
        return data_id in self._data_ids

    def size(self) -> int:
        """
        获取索引中的数据条数

        Returns:
            数据条数
        """
        return len(self._data_ids)

    def save(self, path: Path | str) -> None:
        """
        持久化索引到磁盘（mock 版本为空实现）

        Args:
            path: 保存路径
        """
        # Mock 版本不实现持久化
        pass

    def load(self, path: Path | str) -> None:
        """
        从磁盘加载索引（mock 版本为空实现）

        Args:
            path: 加载路径
        """
        # Mock 版本不实现持久化
        pass

    def clear(self) -> None:
        """
        清空索引

        Note:
            清空所有存储的 data_id
        """
        self._data_ids.clear()

    def __repr__(self) -> str:
        """返回索引的字符串表示"""
        return f"MockIndex(type='{self.index_type}', size={len(self._data_ids)})"
