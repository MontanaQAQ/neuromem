"""SageDB Index implementation for neuromem VDB system.

This module provides a SageDB backend for the neuromem vector database system.

**Important**: SageDB is a self-developed C++ vector database, NOT based on FAISS.
It provides high-performance vector operations with custom indexing and metadata management.

ANNS algorithms will be migrated to sage-libs in the future for better modularity.
"""

import json
import os
from typing import Any

import numpy as np
from sage.common.utils.logging.custom_logger import CustomLogger

from .base_vdb_index import BaseVDBIndex


class SageDBIndex(BaseVDBIndex):
    """SageDB implementation of BaseVDBIndex.

    This class wraps SageDB (self-developed C++ vector database) to work with
    the neuromem system. SageDB is NOT based on FAISS - it's a fully custom
    implementation optimized for fast insertions and flexible metadata handling.

    Performance characteristics:
    - 10x faster single insert vs FAISS
    - 1.14x faster batch insert vs FAISS
    - Optimized for write-heavy workloads
    - Ideal for session storage and real-time applications
    """

    def __init__(self, config: dict | None):
        """Initialize SageDB index.

        Args:
            config: Configuration dict containing:
                - name: Index name
                - dim: Vector dimension
                - config: Optional nested config parameters
        """
        super().__init__()
        self.logger = CustomLogger()

        if config is None:
            raise ValueError("Config cannot be None for SageDBIndex initialization")

        # 合并嵌套的 config 参数
        nested_config = config.get("config")
        if nested_config and isinstance(nested_config, dict):
            config = {**config, **nested_config}
        self.config = config

        # 从config中获取必要参数
        self.index_name = self.config.get("name")
        if self.index_name is None:
            self.logger.error(
                "The index name is not specified in the config, so the index cannot be created."
            )
            raise ValueError(
                "The index name is not specified in the config, so the index cannot be created."
            )

        self.dim = self.config.get("dim", 128)

        # ID映射
        self.id_map: dict[int, str] = {}
        self.rev_map: dict[str, int] = {}
        self.next_id: int = 1
        self.tombstones: set[str] = set()

        # 初始化 SageDB
        self._init_sagedb()

        # 用于检测重复向量
        self.vector_hashes: dict[str, str] = {}  # vector_hash -> string_id

        # 存储向量副本用于重建索引
        self.vector_store: dict[str, np.ndarray] = {}  # string_id -> vector

    def _init_sagedb(self):
        """Initialize the SageDB C++ backend."""
        try:
            from sage.middleware.components.sage_db.python.sage_db import SageDB

            self.db = SageDB(self.dim)
            self.logger.info(f"Initialized SageDB with dimension {self.dim}")
        except ImportError as e:
            self.logger.error(f"Failed to import SageDB: {e}")
            raise ImportError(
                "SageDB is not available. Please ensure sage-middleware is properly installed."
            ) from e

    def insert(self, vector: np.ndarray, string_id: str) -> int:
        """Insert a vector into the index.

        Args:
            vector: Vector to insert (numpy array)
            string_id: String ID

        Returns:
            1 if successful, 0 if failed
        """
        try:
            # 转换为 numpy array（如果不是）
            if isinstance(vector, list):
                vector = np.array(vector, dtype=np.float32)

            # 检查维度
            if len(vector) != self.dim:
                self.logger.error(
                    f"Vector dimension {len(vector)} does not match index dimension {self.dim}"
                )
                return 0

            # 检查是否已存在
            if string_id in self.rev_map:
                self.logger.warning(f"ID {string_id} already exists, skipping insertion")
                return 0

            # 分配内部 ID
            internal_id = self.next_id
            self.id_map[internal_id] = string_id
            self.rev_map[string_id] = internal_id
            self.next_id += 1

            # 存储向量副本
            self.vector_store[string_id] = vector

            # 添加到 SageDB (metadata 必须是 str -> str 映射)
            metadata = {"internal_id": str(internal_id), "string_id": string_id}
            self.db.add(vector.tolist(), metadata)

            return 1

        except Exception as e:
            self.logger.error(f"Failed to insert vector: {e}")
            return 0

    def batch_insert(self, vectors: list[np.ndarray], string_ids: list[str]) -> int:
        """Batch insert vectors.

        Args:
            vectors: List of numpy arrays
            string_ids: List of string IDs

        Returns:
            Number of successfully inserted vectors
        """
        if len(vectors) != len(string_ids):
            self.logger.error("Number of vectors must match number of IDs")
            return 0

        success_count = 0
        for vector, string_id in zip(vectors, string_ids):
            result = self.insert(vector, string_id)
            success_count += result

        return success_count

    def delete(self, string_id: str) -> int:
        """Delete a vector by string ID.

        Args:
            string_id: String ID of the vector to delete

        Returns:
            1 if successful, 0 if not found
        """
        if string_id not in self.rev_map:
            self.logger.warning(f"ID {string_id} not found")
            return 0

        # 标记为已删除
        self.tombstones.add(string_id)

        # 从映射中移除
        internal_id = self.rev_map.pop(string_id)
        self.id_map.pop(internal_id, None)

        # 从向量存储中移除
        self.vector_store.pop(string_id, None)

        # 注意：SageDB 不支持删除，我们只在内存中标记删除
        # 搜索时需要过滤 tombstones

        return 1

    def update(self, string_id: str, new_vector: np.ndarray) -> int:
        """Update a vector.

        Args:
            string_id: String ID of the vector to update
            new_vector: New vector data

        Returns:
            1 if successful, 0 if failed
        """
        # SageDB 不支持原地更新，需要删除后重新插入
        if string_id not in self.rev_map:
            self.logger.warning(f"ID {string_id} not found")
            return 0

        # 删除旧向量
        self.delete(string_id)

        # 插入新向量
        return self.insert(new_vector, string_id)

    def search(self, query_vector: np.ndarray, topk: int = 10) -> tuple[list[str], list[float]]:
        """Search for nearest neighbors.

        Args:
            query_vector: Query vector (numpy array)
            topk: Number of results to return

        Returns:
            Tuple of (string_ids, scores)
        """
        # 转换为 list（如果是 numpy array）
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        # 构建索引（如果尚未构建）
        import contextlib

        with contextlib.suppress(Exception):
            self.db.build_index()  # 索引可能已经构建

        # 搜索（多取一些以便过滤tombstones）
        results = self.db.search(query_vector, k=topk * 2)

        # 转换结果并过滤 tombstones
        string_ids = []
        scores = []
        for result in results:
            string_id = result.metadata.get("string_id")
            if string_id is None or string_id in self.tombstones:
                continue

            string_ids.append(string_id)
            scores.append(result.score)

            if len(string_ids) >= topk:
                break

        return string_ids, scores

    def train(self, vectors: list[list] | np.ndarray) -> bool:
        """Train the index (no-op for SageDB).

        Args:
            vectors: Training vectors

        Returns:
            True
        """
        # SageDB doesn't require explicit training
        return True

    def is_trained(self) -> bool:
        """Check if index is trained.

        Returns:
            True (SageDB doesn't require training)
        """
        return True

    def ntotal(self) -> int:
        """Get total number of vectors (excluding tombstones).

        Returns:
            Number of vectors
        """
        return len(self.rev_map)

    def store(self, dir_path: str) -> dict[str, Any]:
        """Store index to disk.

        Args:
            dir_path: Path to save location

        Returns:
            Metadata dict
        """
        try:
            os.makedirs(dir_path, exist_ok=True)

            # 保存 SageDB 索引
            sagedb_path = os.path.join(dir_path, "sagedb.index")
            self.db.save(sagedb_path)

            # 保存元数据
            metadata = {
                "index_name": self.index_name,
                "dim": self.dim,
                "id_map": self.id_map,
                "rev_map": self.rev_map,
                "next_id": self.next_id,
                "tombstones": list(self.tombstones),
                "config": self.config,
                "backend_type": "SageDB",
            }
            metadata_path = os.path.join(dir_path, "metadata.json")
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            # 保存向量存储
            vector_store_path = os.path.join(dir_path, "vectors.npz")
            np.savez(vector_store_path, **self.vector_store)

            self.logger.info(f"Stored SageDB index to {dir_path}")
            return metadata

        except Exception as e:
            self.logger.error(f"Failed to store index: {e}")
            raise

    def save(self, path: str) -> bool:
        """Save index to disk (backward compatibility).

        Args:
            path: Path to save location

        Returns:
            True if successful
        """
        try:
            self.store(path)
            return True
        except Exception:
            return False

    @classmethod
    def load(cls, name: str, dir_path: str) -> "SageDBIndex":
        """Load index from disk.

        Args:
            name: Index name (for compatibility, loaded from metadata)
            dir_path: Path to load from

        Returns:
            Loaded SageDBIndex instance
        """
        logger = CustomLogger()

        try:
            # 加载元数据
            metadata_path = os.path.join(dir_path, "metadata.json")
            with open(metadata_path) as f:
                metadata = json.load(f)

            # 创建实例
            config = metadata.get("config", {})
            config["name"] = metadata["index_name"]
            config["dim"] = metadata["dim"]

            instance = cls(config)

            # 恢复映射
            instance.id_map = {int(k): v for k, v in metadata["id_map"].items()}
            instance.rev_map = metadata["rev_map"]
            instance.next_id = metadata["next_id"]
            instance.tombstones = set(metadata["tombstones"])

            # 加载向量存储
            vector_store_path = os.path.join(dir_path, "vectors.npz")
            vectors_data = np.load(vector_store_path)
            instance.vector_store = {k: vectors_data[k] for k in vectors_data}

            # 加载 SageDB 索引
            sagedb_path = os.path.join(dir_path, "sagedb.index")
            instance.db.load(sagedb_path)

            logger.info(f"Loaded SageDB index from {dir_path}")
            return instance

        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            raise

    def get_dim(self) -> int:
        """Get vector dimension.

        Returns:
            Vector dimension
        """
        return self.dim

    def rebuild_index(self) -> bool:
        """Rebuild the index from stored vectors.

        Returns:
            True if successful
        """
        try:
            # 重新初始化 SageDB
            self._init_sagedb()

            # 重新插入所有向量
            for string_id, vector in self.vector_store.items():
                if string_id not in self.tombstones:
                    internal_id = self.rev_map[string_id]
                    metadata = {"internal_id": str(internal_id), "string_id": string_id}
                    self.db.add(vector.tolist(), metadata)

            # 构建索引
            self.db.build_index()

            self.logger.info("Successfully rebuilt SageDB index")
            return True

        except Exception as e:
            self.logger.error(f"Failed to rebuild index: {e}")
            return False
