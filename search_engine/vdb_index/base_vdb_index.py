# file sage/core/sage.middleware.services.neuromem./search_engine/vdb_index/base_vdb_index.py

from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class BaseVDBIndex(ABC):
    def __init__(self):  # noqa: B027
        """ """

    @abstractmethod
    def insert(self, vector: np.ndarray, string_id: str) -> int:
        """插入单个向量

        Returns:
            int: 1表示成功，0表示失败
        """
        pass

    @abstractmethod
    def batch_insert(self, vectors: list[np.ndarray], string_ids: list[str]) -> int:
        """批量插入向量

        Returns:
            int: 成功插入的向量数量
        """
        pass

    @abstractmethod
    def delete(self, string_id: str) -> int:
        """删除一个向量（物理或逻辑）

        Returns:
            int: 1表示成功，0表示失败
        """
        pass

    @abstractmethod
    def update(self, string_id: str, new_vector: np.ndarray) -> int:
        """更新向量内容

        Returns:
            int: 1表示成功，0表示失败
        """
        pass

    @abstractmethod
    def search(self, query_vector: np.ndarray, topk: int = 10) -> tuple[list[str], list[float]]:
        """向量检索，返回 (string_id, 距离) 列表"""
        pass

    @classmethod
    @abstractmethod
    def load(cls, name: str, dir_path: str) -> "BaseVDBIndex":
        """
        加载索引实例。
        Load the index instance.

        Args:
            name: 索引名称
            dir_path: 索引存储目录路径
        """
        pass

    @abstractmethod
    def store(self, dir_path: str) -> dict[str, Any]:
        """
        存储索引数据到指定目录。
        Store the index data to the specified directory.

        Args:
            dir_path: 索引存储目录路径

        Returns:
            Dict[str, Any]: 存储的元数据
        """
        pass
