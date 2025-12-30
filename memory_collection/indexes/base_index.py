"""BaseIndex - 索引基类

所有索引实现必须继承此抽象类，提供统一的索引接口。

设计原则：
- 索引只存 data_id，不存原始数据
- 索引负责查询逻辑，不负责数据存储
- 支持持久化（save/load）

索引类型：
- FIFO Queue（T1.4）
- LSH（T1.5）
- FAISS Vector（T1.6）
- Graph（T1.7）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class BaseIndex(ABC):
    """
    索引抽象基类

    所有索引实现必须提供以下方法：
    - add: 添加数据到索引
    - remove: 从索引移除数据
    - query: 查询索引返回 data_id 列表
    - contains: 检查数据是否在索引中
    - size: 获取索引中的数据条数
    - save: 持久化索引到磁盘
    - load: 从磁盘加载索引
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化索引

        Args:
            config: 索引配置字典
        """
        self.config = config or {}

    @abstractmethod
    def add(self, data_id: str, text: str, metadata: dict[str, Any]) -> None:
        """
        添加数据到索引

        Args:
            data_id: 数据 ID
            text: 原始文本（用于建立索引，如向量化、BM25）
            metadata: 元数据（某些索引可能需要）

        Note:
            - 如果 data_id 已存在，应该更新索引
            - 索引只存 data_id，不存原始数据
        """
        pass

    @abstractmethod
    def remove(self, data_id: str) -> None:
        """
        从索引移除数据

        Args:
            data_id: 数据 ID

        Note:
            - 如果 data_id 不存在，不应抛出错误
        """
        pass

    @abstractmethod
    def query(self, query: Any, **params: Any) -> list[str]:
        """
        查询索引

        Args:
            query: 查询内容（类型取决于索引）
                - FIFO: None（返回队列头）
                - Vector: list[float]（相似向量）
                - BM25: str（查询文本）
                - Graph: str（起始节点 ID）
            **params: 查询参数
                - top_k: 返回结果数量
                - threshold: 相似度阈值
                - depth: 图遍历深度
                - 等等

        Returns:
            匹配的 data_id 列表（按相关性排序）

        Note:
            - 不同索引类型对 query 和 params 的要求不同
            - 应该在子类文档中明确说明
        """
        pass

    @abstractmethod
    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在索引中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    def size(self) -> int:
        """
        获取索引中的数据条数

        Returns:
            数据条数
        """
        pass

    @abstractmethod
    def save(self, path: Path | str) -> None:
        """
        持久化索引到磁盘

        Args:
            path: 保存路径（目录或文件，取决于索引类型）

        Note:
            - 应该保存所有必要的索引数据
            - 调用 load 后应该能完全恢复索引状态
        """
        pass

    @abstractmethod
    def load(self, path: Path | str) -> None:
        """
        从磁盘加载索引

        Args:
            path: 加载路径（对应 save 时的路径）

        Raises:
            FileNotFoundError: 如果路径不存在

        Note:
            - 应该完全恢复索引状态
            - 加载后索引应该立即可用
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        清空索引（可选实现）

        Note:
            - 子类可以覆盖此方法提供更高效的实现
            - 默认实现：不操作（索引创建时默认为空）
        """
        pass

    def __repr__(self) -> str:
        """返回索引的字符串表示"""
        return f"{self.__class__.__name__}(size={self.size()})"
