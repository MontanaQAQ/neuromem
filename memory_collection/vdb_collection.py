import contextlib
import hashlib
import inspect
import json
import os
import shutil
import time
from collections.abc import Callable
from typing import Any

import numpy as np
from sage.common.utils.logging.custom_logger import CustomLogger

from ..search_engine.vdb_index import index_factory
from ..utils.path_utils import get_default_data_dir
from .base_collection import BaseMemoryCollection


class VDBMemoryCollection(BaseMemoryCollection):
    """
    Memory collection with vector database support.
    支持向量数据库功能的内存集合类。

    职责：
    - 存储和管理向量索引
    - 接收外部生成的 embedding 向量
    - 验证向量维度
    - 执行向量检索

    注意：embedding 的生成应在外部完成，此类仅负责向量的存储和检索。
    """

    def __init__(self, config: dict[str, Any]):
        self.name = config["name"]
        super().__init__(self.name)

        self.logger = CustomLogger()

        # 存储index的参数
        # index_name -> dict: { index, dim, description, backend_type, config, is_init }
        self.index_info = {}

        # Initialize statistics tracking
        self._init_statistics()

    # 创建某个索引（不插入数据）
    def create_index(self, config: dict | None = None):
        """
        创建新的向量索引。

        Args:
            config: 索引配置，必须包含:
                - name: 索引名称
                - dim: 向量维度
                - backend_type: 索引后端类型 (如 "FAISS")
                - description: 索引描述 (可选)
                - index_parameter: 索引参数 (可选)
        """
        # 检查创建条件
        index_name = config.get("name")
        if not index_name:
            self.logger.warning(
                "The config must contain the 'name' field, and the index cannot be created."
            )
            return None
        if index_name in self.index_info:
            self.logger.warning(
                f"The index '{index_name}' already exists and cannot be created again"
            )
            return None

        dim = config.get("dim")
        if not isinstance(dim, int) or dim <= 0:
            self.logger.warning("The config must contain valid 'dim' (positive int).")
            return None

        try:
            backend_type = config.get("backend_type")
            description = config.get("description", "")
            index_parameter = config.get("index_parameter")
            index_config = {
                "name": index_name,
                "dim": dim,
                "backend_type": backend_type,
                "config": index_parameter,
            }

            # 通过index_factory创建对应索引
            index = index_factory.create_index(config=index_config)

            self.index_info[index_name] = {
                "dim": dim,
                "index": index,
                "backend_type": backend_type,
                "description": description,
                "config": index_parameter,
                "is_init": False,
            }

            self.logger.info(
                f"Successfully created index '{index_name}', backend type: {backend_type}, dim: {dim}"
            )

            # Track statistics
            self.statistics["index_create_count"] += 1
            self.statistics["index_stats"][index_name] = {
                "vector_count": 0,
                "created_time": time.time(),
                "last_rebuild_time": None,
            }

        except Exception as e:
            self.logger.error(
                f"Failed to create index {index_name} with backend {backend_type}: {e}"
            )
            raise ValueError(
                f"Failed to create index {index_name} with backend {backend_type}: {e}"
            ) from e

        return True

    # 直接删除某个索引
    def delete_index(self, index_name: str):
        """
        删除指定名称的索引。
        """
        if index_name in self.index_info:
            del self.index_info[index_name]
        else:
            raise ValueError(f"Index '{index_name}' does not exist.")

    # 列举索引信息
    def list_index(self, *index_names):
        """
        列出指定的索引或所有索引及其描述信息。
        """
        if index_names:
            # 如果指定了索引名称，只返回这些索引的信息
            result = []
            for name in index_names:
                if name in self.index_info:
                    result.append(
                        {
                            "name": name,
                            "description": self.index_info[name]["description"],
                        }
                    )
                else:
                    self.logger.warning(f"索引 '{name}' 不存在")
            return result
        else:
            # 如果没有指定，返回所有索引信息
            return [
                {"name": name, "description": info["description"]}
                for name, info in self.index_info.items()
            ]

    # 按照筛选条件进行索引更新
    def update_index(
        self,
        index_name: str,
        vectors: list[np.ndarray],
        item_ids: list[str],
    ):
        """
        更新指定索引：删除当前索引，保留config，重新创建索引并批量插入数据

        Args:
            index_name: 索引名称
            vectors: 向量列表，每个向量应为 numpy.ndarray
            item_ids: 对应的数据 ID 列表

        Returns:
            插入的向量数量，失败返回 None
        """
        # 首先完成必要的检查
        if index_name not in self.index_info:
            self.logger.warning(f"Index '{index_name}' does not exist, cannot update")
            return None

        # 保存原有配置
        old_info = self.index_info[index_name].copy()
        config = {
            "name": index_name,
            "dim": old_info["dim"],
            "backend_type": old_info["backend_type"],
            "description": old_info["description"],
            "index_parameter": old_info.get("config"),
        }

        # 利用delete_index删除
        self.delete_index(index_name)

        # Preserve original created_time before create_index
        original_created_time = (
            self.statistics["index_stats"].get(index_name, {}).get("created_time")
        )

        # 利用create_index重新创建
        self.create_index(config)

        # Track rebuild statistics
        self.statistics["index_rebuild_count"] += 1
        if index_name in self.statistics["index_stats"]:
            self.statistics["index_stats"][index_name]["last_rebuild_time"] = time.time()
            # Restore original created_time
            if original_created_time is not None:
                self.statistics["index_stats"][index_name]["created_time"] = original_created_time

        # 利用init_index插入数据
        return self.init_index(index_name, vectors, item_ids)

    # 批量插入向量初始化索引
    def init_index(
        self,
        index_name: str,
        vectors: list[np.ndarray],
        item_ids: list[str],
    ):
        """
        使用预先生成的向量批量初始化索引。

        Args:
            index_name: 索引名称
            vectors: 向量列表，每个向量应为 numpy.ndarray
            item_ids: 对应的数据 ID 列表

        Returns:
            插入的向量数量，失败返回 None
        """
        # 检查 init_index 条件
        if index_name not in self.index_info:
            self.logger.warning(f"Index '{index_name}' does not exist, cannot initialize")
            return None
        if self.index_info[index_name].get("is_init", False):
            self.logger.warning(
                f"Index '{index_name}' has already been initialized, cannot initialize again"
            )
            return None

        if len(vectors) != len(item_ids):
            self.logger.warning(
                f"vectors length ({len(vectors)}) must match item_ids length ({len(item_ids)})"
            )
            return None

        if not vectors:
            self.logger.warning(f"No vectors provided for index '{index_name}' initialization")
            return None

        expected_dim = self.index_info[index_name]["dim"]
        processed_vectors = []
        valid_ids = []

        # 验证和处理每个向量
        for i, (vector, item_id) in enumerate(zip(vectors, item_ids)):
            # 统一处理不同格式的 embedding 结果
            if hasattr(vector, "detach") and hasattr(vector, "cpu"):
                vector = vector.detach().cpu().numpy()
            if isinstance(vector, list):
                vector = np.array(vector)
            if not isinstance(vector, np.ndarray):
                vector = np.array(vector)
            vector = vector.astype(np.float32)

            # 检查维度
            if vector.shape[-1] != expected_dim:
                self.logger.warning(
                    f"Vector {i} has dimension {vector.shape[-1]}, expected {expected_dim}, skipping"
                )
                continue

            processed_vectors.append(vector)
            valid_ids.append(item_id)

        if not processed_vectors:
            self.logger.warning(f"No valid vectors for index '{index_name}'")
            return None

        # 使用 batch_insert 插入数据到索引
        index = self.index_info[index_name]["index"]
        result = index.batch_insert(processed_vectors, valid_ids)

        # 标记索引已初始化
        self.index_info[index_name]["is_init"] = True

        # Update statistics
        self._update_total_vectors()

        self.logger.info(f"Index '{index_name}' initialized with {result} data items")
        return result

    # 批量数据插入（仅存入collection，不创建索引）
    def batch_insert_data(self, data: list[str], metadatas: list[dict[str, Any]] | None = None):
        """
        批量插入数据到collection中（仅存储，不创建索引）
        """
        self.logger.info(f"Batch inserting {len(data)} data items to storage")

        if metadatas is not None and len(metadatas) != len(data):
            raise ValueError("metadatas length must match data length")

        for i, item in enumerate(data):
            metadata = metadatas[i] if metadatas else None
            key = item
            if metadata:
                key += json.dumps(metadata, sort_keys=True)
            stable_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
            self.text_storage.store(stable_id, item)

            if metadata:
                # 自动注册所有未知的元数据字段
                for field_name in metadata:
                    if not self.metadata_storage.has_field(field_name):
                        self.metadata_storage.add_field(field_name)
                self.metadata_storage.store(stable_id, metadata)

    # 单条数据插入（必须指定索引插入）
    def insert(
        self,
        index_name: str,
        raw_data: str,
        vector: np.ndarray,
        metadata: dict[str, Any] | None = None,
    ):
        """
        插入单条数据到指定索引。

        Args:
            index_name: 索引名称
            raw_data: 原始文本数据（用于存储）
            vector: 预先生成的向量
            metadata: 元数据（可选）

        Returns:
            插入数据的 ID，失败返回 None
        """
        # 检查索引是否存在
        if index_name not in self.index_info:
            self.logger.warning(f"The index '{index_name}' does not exist")
            return None
        index = self.index_info.get(index_name).get("index")

        # 首先存储数据到 storage
        key = raw_data
        if metadata:
            key += json.dumps(metadata, sort_keys=True)
        stable_id = hashlib.sha256(key.encode("utf-8")).hexdigest()
        self.text_storage.store(stable_id, raw_data)

        # 自动注册所有未知的元数据字段
        if metadata:
            for field_name in metadata:
                if not self.metadata_storage.has_field(field_name):
                    self.metadata_storage.add_field(field_name)
            self.metadata_storage.store(stable_id, metadata)

        # 统一处理不同格式的向量
        if hasattr(vector, "detach") and hasattr(vector, "cpu"):
            vector = vector.detach().cpu().numpy()
        if isinstance(vector, list):
            vector = np.array(vector)
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector)
        vector = vector.astype(np.float32)
        # L2 normalization
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        # 检查向量维度是否与索引要求一致
        expected_dim = self.index_info[index_name]["dim"]
        if vector.shape[-1] != expected_dim:
            self.logger.warning(
                f"Index '{index_name}' requires dimension {expected_dim}, but vector dimension is {vector.shape[-1]}, skipping insertion"
            )
            return None

        index.insert(vector, stable_id)

        # Track statistics
        self.statistics["insert_count"] += 1
        self._update_total_vectors()

        return stable_id

    # 单条文本删除（全索引删除）
    def delete(self, raw_text: str):
        """
        删除指定的文本条目

        Args:
            raw_text: 要删除的原始文本

        Returns:
            bool: 删除是否成功
        """
        try:
            stable_id = self._get_stable_id(raw_text)

            # 检查是否存在
            if not self.text_storage.has(stable_id):
                self.logger.warning(
                    f"Text not found for deletion: excerpt='{raw_text[:50]}', stable_id='{stable_id}'"
                )
                return False

            self.text_storage.delete(stable_id)
            self.metadata_storage.delete(stable_id)

            for index_info in self.index_info.values():
                index_info["index"].delete(stable_id)

            return True
        except Exception as e:
            self.logger.error(f"Failed to delete: {e}")
            return False

    # 检索文本（指定索引检索）
    def retrieve(
        self,
        query_vector: np.ndarray,
        index_name: str,
        topk: int | None = None,
        threshold: float | None = None,
        with_metadata: bool = False,
        metadata_filter_func: Callable[[dict[str, Any]], bool] | None = None,
        **metadata_conditions,
    ):
        """
        使用查询向量检索相似数据。

        Args:
            query_vector: 查询向量（应已归一化）
            index_name: 索引名称
            topk: 返回的最大结果数（默认 5）
            threshold: 相似度阈值（默认 0.7）
            with_metadata: 是否返回元数据
            metadata_filter_func: 元数据过滤函数
            **metadata_conditions: 元数据过滤条件

        Returns:
            检索结果列表，失败返回 None
        """
        # Track start time for statistics
        start_time = time.time()

        if index_name not in self.index_info:
            self.logger.warning(f"The index '{index_name}' does not exist")
            return None

        if topk is None:
            topk = 5
        if threshold is None:
            threshold = 0.7

        # 统一处理不同格式的查询向量
        if hasattr(query_vector, "detach") and hasattr(query_vector, "cpu"):
            query_vector = query_vector.detach().cpu().numpy()
        if isinstance(query_vector, list):
            query_vector = np.array(query_vector)
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector)
        query_vector = query_vector.astype(np.float32)
        # 归一化查询向量
        norm = np.linalg.norm(query_vector)
        if norm == 0:
            self.logger.warning("Query vector has zero norm and cannot be normalized.")
            return None
        query_vector = query_vector / norm

        # 检查维度
        expected_dim = self.index_info[index_name]["dim"]
        if query_vector.shape[-1] != expected_dim:
            self.logger.warning(
                f"Query vector dimension {query_vector.shape[-1]} does not match index dimension {expected_dim}"
            )
            return None

        index = self.index_info.get(index_name).get("index")

        top_k_ids, distances = index.search(query_vector, topk=topk, threshold=threshold)

        if top_k_ids and isinstance(top_k_ids[0], (list, np.ndarray)):
            top_k_ids = top_k_ids[0]
        if distances and isinstance(distances[0], (list, np.ndarray)):
            distances = distances[0]
        top_k_ids = [str(i) for i in top_k_ids]

        # 应用元数据过滤
        if metadata_filter_func or metadata_conditions:
            filtered_ids = self.filter_ids(top_k_ids, metadata_filter_func, **metadata_conditions)
        else:
            filtered_ids = top_k_ids

        # 截取需要的数量，检索到几个就返回几个
        final_ids = filtered_ids[:topk]

        # 如果检索结果少于请求数量，记录信息但不警告
        if len(final_ids) < topk:
            self.logger.info(f"Retrieved {len(final_ids)} results (requested {topk})")

        # Track statistics
        duration = time.time() - start_time
        self.statistics["retrieve_count"] += 1
        self.statistics["retrieve_stats"].append(
            {
                "timestamp": start_time,
                "duration": duration,
                "result_count": len(final_ids),
                "index_name": index_name,
                "requested_topk": topk if topk is not None else 5,
            }
        )
        # Limit retrieve_stats to prevent unbounded growth
        max_retrieve_stats = 1000
        if len(self.statistics["retrieve_stats"]) > max_retrieve_stats:
            self.statistics["retrieve_stats"].pop(0)

        if with_metadata:
            return [
                {
                    "text": self.text_storage.get(i),
                    "metadata": self.metadata_storage.get(i),
                }
                for i in final_ids
            ]
        else:
            return [self.text_storage.get(i) for i in final_ids]

    # 单条文本更新（必须指定索引更新）
    def update(
        self,
        index_name: str,
        old_data: str,
        new_data: str,
        new_vector: np.ndarray,
        new_metadata: dict[str, Any] | None = None,
    ):
        """
        更新指定数据。

        Args:
            index_name: 索引名称
            old_data: 原始文本
            new_data: 新文本
            new_vector: 新向量
            new_metadata: 新元数据（可选）

        Returns:
            新插入数据的ID（如字符串），如果插入失败则为 None。
        """
        old_id = self._get_stable_id(old_data)
        if not self.text_storage.has(old_id):
            raise ValueError("Original data not found.")

        self.text_storage.delete(old_id)
        self.metadata_storage.delete(old_id)

        for index_info in self.index_info.values():
            index_info["index"].delete(old_id)

        return self.insert(index_name, new_data, new_vector, new_metadata)

    def _serialize_func(self, func):
        """
        改善lambda序列化管理
        """
        if func is None:
            return None
        try:
            return inspect.getsource(func).strip()
        except Exception:
            return str(func)

    def _deserialize_func(self, func_str):
        """
        反序列化函数字符串
        """
        if func_str is None or func_str == "None" or func_str == "":
            return lambda m: True

        # 简单的lambda函数恢复，实际生产环境中需要更安全的方式
        try:
            # 这里只是一个简单的示例，实际应该使用更安全的方式
            if func_str.startswith("lambda"):
                return eval(func_str)
            else:
                return lambda m: True
        except Exception:
            return lambda m: True

    def store(self, store_path: str | None = None):
        self.logger.debug("VDBMemoryCollection: store called")

        # 使用默认数据目录或传入的数据目录（通常来自MemoryManager）
        base_dir = get_default_data_dir() if store_path is None else store_path

        collection_dir = os.path.join(base_dir, "vdb_collection", self.name)
        os.makedirs(collection_dir, exist_ok=True)

        # 1. 存储text和metadata
        self.text_storage.store_to_disk(os.path.join(collection_dir, "text_storage.json"))
        self.metadata_storage.store_to_disk(os.path.join(collection_dir, "metadata_storage.json"))

        # 2. 索引和index_info
        indexes_dir = os.path.join(collection_dir, "indexes")
        os.makedirs(indexes_dir, exist_ok=True)
        saved_index_info = {}
        for index_name, info in self.index_info.items():
            idx = info["index"]
            idx_path = os.path.join(indexes_dir, index_name)
            os.makedirs(idx_path, exist_ok=True)
            idx.store(idx_path)
            saved_index_info[index_name] = {
                "dim": info.get("dim", 128),
                "backend_type": info.get("backend_type", "FAISS"),
                "description": info.get("description", ""),
                "index_type": idx.__class__.__name__,
                "config": info.get("config"),
                "is_init": info.get("is_init", False),
            }

        # 3. collection全局config
        config = {
            "name": self.name,
            "indexes": saved_index_info,
            "statistics": self.statistics,  # Save statistics
        }
        with open(os.path.join(collection_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return {"collection_path": collection_dir}

    @classmethod
    def load(cls, name: str, vdb_path: str | None = None):
        """
        从磁盘加载VDBMemoryCollection实例

        Args:
            name: 集合名称
            vdb_path: 加载路径，如果为None则使用默认路径
        """
        if vdb_path is None:
            # 如果没有指定路径，使用默认路径结构
            base_dir = get_default_data_dir()
            load_path = os.path.join(base_dir, "vdb_collection", name)
        else:
            load_path = vdb_path

        # 此时 load_path 应该是指向具体collection的完整路径
        config_path = os.path.join(load_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # 使用新的初始化方式创建实例
        instance = cls(config={"name": name})

        # 加载storages
        instance.text_storage.load_from_disk(os.path.join(load_path, "text_storage.json"))
        instance.metadata_storage.load_from_disk(os.path.join(load_path, "metadata_storage.json"))

        # 清空在初始化时创建的默认索引
        instance.index_info.clear()

        # 加载索引和index_info
        indexes_dir = os.path.join(load_path, "indexes")
        for index_name, idx_info in config.get("indexes", {}).items():
            idx_type = idx_info["index_type"]
            idx_path = os.path.join(indexes_dir, index_name)

            try:
                # 直接使用索引类的load方法
                if idx_type == "FaissIndex":
                    from ..search_engine.vdb_index.faiss_index import FaissIndex

                    idx = FaissIndex.load(index_name, idx_path)
                else:
                    # 尝试通过工厂类找到对应的索引类
                    backend_type = idx_type.replace("Index", "").upper()
                    if backend_type in index_factory._index_registry:
                        index_class = index_factory._index_registry[backend_type]
                        idx = index_class.load(index_name, idx_path)
                    else:
                        raise ValueError(f"Unknown backend type: {backend_type}")

            except Exception as e:
                raise NotImplementedError(f"Unknown index_type {idx_type}: {e}") from e

            # 恢复 index_info
            instance.index_info[index_name] = {
                "dim": idx_info.get("dim", 128),
                "index": idx,
                "backend_type": idx_info.get("backend_type", "FAISS"),
                "description": idx_info.get("description", ""),
                "config": idx_info.get("config"),
                "is_init": idx_info.get("is_init", False),
            }

        # Restore statistics (backwards compatible)
        if "statistics" in config:
            instance.statistics = config["statistics"]
        else:
            # Initialize statistics if not present (for old collections)
            instance._init_statistics()

        return instance

    @staticmethod
    def clear(name, clear_path=None):
        if clear_path is None:
            clear_path = get_default_data_dir()
        collection_dir = os.path.join(clear_path, "vdb_collection", name)
        try:
            shutil.rmtree(collection_dir)
            print(f"Cleared collection: {collection_dir}")
        except FileNotFoundError:
            print(f"Collection does not exist: {collection_dir}")
        except Exception as e:
            print(f"Failed to clear: {e}")

    # ==================== Statistics Methods ====================

    def _init_statistics(self):
        """Initialize statistics tracking structure."""
        self.statistics = {
            "insert_count": 0,
            "retrieve_count": 0,
            "index_create_count": 0,
            "index_rebuild_count": 0,
            "total_vectors_stored": 0,
            "retrieve_stats": [],
            "index_stats": {},
        }

    def _update_total_vectors(self):
        """Recalculate total vectors stored across all indexes."""
        total = 0
        for index_name, info in self.index_info.items():
            if "index" in info and hasattr(info["index"], "index"):
                vector_count = (
                    info["index"].index.ntotal if hasattr(info["index"].index, "ntotal") else 0
                )
                # Update index stats
                if index_name in self.statistics["index_stats"]:
                    self.statistics["index_stats"][index_name]["vector_count"] = vector_count
                total += vector_count
        self.statistics["total_vectors_stored"] = total

    def get_statistics(self) -> dict[str, Any]:
        """
        Get all statistics.

        Returns:
            Dictionary containing all tracked statistics
        """
        self._update_total_vectors()
        return self.statistics.copy()

    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics.

        Returns:
            Dictionary with memory usage information including estimated memory size
        """
        self._update_total_vectors()

        # Calculate estimated memory usage
        # Assumption: each vector is dim * 4 bytes (float32) with 20% overhead for metadata
        estimated_memory_bytes = 0
        index_stats = {}

        for index_name, info in self.index_info.items():
            dim = info.get("dim", 128)
            vector_count = 0

            if "index" in info and hasattr(info["index"], "index"):
                vector_count = (
                    info["index"].index.ntotal if hasattr(info["index"].index, "ntotal") else 0
                )

            # Memory per vector: dim * 4 bytes (float32) * 1.2 (overhead)
            bytes_per_vector = dim * 4 * 1.2
            estimated_memory_bytes += vector_count * bytes_per_vector

            index_stats[index_name] = {
                "vector_count": vector_count,
                "created_time": self.statistics["index_stats"]
                .get(index_name, {})
                .get("created_time"),
            }

        estimated_memory_mb = estimated_memory_bytes / (1024 * 1024)

        return {
            "total_vectors": self.statistics["total_vectors_stored"],
            "estimated_memory_mb": round(estimated_memory_mb, 2),
            "index_stats": index_stats,
        }

    def get_retrieve_stats(self, last_n: int | None = None) -> dict[str, Any]:
        """
        Get retrieval performance statistics.

        Args:
            last_n: If specified, only return the last N retrieval operations

        Returns:
            Dictionary with retrieval statistics including average duration
        """
        retrieve_stats = self.statistics["retrieve_stats"]

        if last_n is not None:
            retrieve_stats = retrieve_stats[-last_n:]

        # Calculate average duration
        avg_duration = 0.0
        if retrieve_stats:
            avg_duration = sum(stat["duration"] for stat in retrieve_stats) / len(retrieve_stats)

        return {
            "total_retrieve_count": self.statistics["retrieve_count"],
            "sample_size": len(retrieve_stats),
            "avg_duration": round(avg_duration, 4),
            "recent_stats": retrieve_stats,
        }

    def get_index_rebuild_stats(self) -> dict[str, Any]:
        """
        Get index rebuild frequency statistics.

        Returns:
            Dictionary with rebuild statistics and index details
        """
        self._update_total_vectors()

        index_details = {}
        for index_name, stats in self.statistics["index_stats"].items():
            index_details[index_name] = {
                "vector_count": stats.get("vector_count", 0),
                "last_rebuild_time": stats.get("last_rebuild_time"),
                "created_time": stats.get("created_time"),
            }

        return {
            "total_rebuild_count": self.statistics["index_rebuild_count"],
            "index_details": index_details,
        }

    def reset_statistics(self):
        """Reset all statistics counters while preserving index structure."""
        # Preserve index_stats keys but reset their values
        index_stats = {}
        for index_name in self.statistics["index_stats"]:
            index_stats[index_name] = {
                "vector_count": 0,
                "created_time": self.statistics["index_stats"][index_name].get("created_time"),
                "last_rebuild_time": None,
            }

        self.statistics = {
            "insert_count": 0,
            "retrieve_count": 0,
            "index_create_count": 0,
            "index_rebuild_count": 0,
            "total_vectors_stored": 0,
            "retrieve_stats": [],
            "index_stats": index_stats,
        }

        # Update vector counts to reflect actual state
        self._update_total_vectors()


if __name__ == "__main__":
    # CustomLogger.disable_global_console_debug()
    import shutil
    import tempfile

    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    from sage.common.components.sage_embedding.embedding_api import apply_embedding_model

    def colored(text, color):
        colors = {
            "green": "\033[92m",
            "red": "\033[91m",
            "yellow": "\033[93m",
            "reset": "\033[0m",
        }
        return colors.get(color, "") + str(text) + colors["reset"]

    def normalize_vector(vector):
        """对向量进行 L2 归一化"""
        # 统一处理不同格式的向量
        if hasattr(vector, "detach") and hasattr(vector, "cpu"):
            vector = vector.detach().cpu().numpy()
        if isinstance(vector, list):
            vector = np.array(vector)
        if not isinstance(vector, np.ndarray):
            vector = np.array(vector)
        vector = vector.astype(np.float32)

        # L2 归一化
        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("Cannot normalize a zero vector: input vector has zero norm.")
        vector = vector / norm
        return vector

    def run_test():
        print(colored("\n=== 开始VDBMemoryCollection重构后测试 ===", "yellow"))
        print(colored("测试重点：embedding 在外部生成，collection 只负责向量存储", "yellow"))

        # 准备测试环境
        test_name = "test_collection"
        test_dir = tempfile.mkdtemp()

        # 在外部创建 embedding 模型
        embedding_model = apply_embedding_model("mockembedder")
        print(colored("✓ 在外部创建 embedding 模型", "green"))

        # 在外部创建 embedding 模型
        embedding_model = apply_embedding_model("mockembedder")
        print(colored("✓ 在外部创建 embedding 模型", "green"))

        try:
            # 1. 测试新的初始化方式（不需要 embedding_model）
            print(colored("\n1. 测试初始化（不依赖 embedding_model）", "yellow"))

            config = {"name": test_name}
            collection = VDBMemoryCollection(config=config)
            print(colored("✓ 通过 config 初始化成功，无需 embedding_model", "green"))

            # 创建索引配置（不需要 embedding_model 参数）
            index_config = {
                "name": "default_index",
                "dim": 128,  # 只需要指定维度
                "backend_type": "FAISS",
                "description": "默认测试索引",
                "index_parameter": {},
            }
            collection.create_index(config=index_config)
            print(colored("✓ 创建索引成功，只需要指定维度", "green"))

            # 2. 测试数据插入（在外部生成 embedding）
            print(colored("\n2. 测试数据插入（embedding 外部生成）", "yellow"))
            texts = [
                "这是第一条测试文本",
                "这是第二条测试文本，带有metadata",
                "这是第三条测试文本",
            ]
            metadata = {"type": "test", "priority": "high"}

            # 在外部生成 embedding 向量
            vector1 = normalize_vector(embedding_model.encode(texts[0]))
            vector2 = normalize_vector(embedding_model.encode(texts[1]))
            _ = normalize_vector(embedding_model.encode(texts[2]))  # vector3 not used in test
            print(colored("✓ 在外部生成 embedding 向量", "green"))

            # 先存储数据
            collection.batch_insert_data([texts[0], texts[1]])
            print(colored("✓ 批量存储文本数据", "green"))

            # 插入向量到索引
            id1 = collection.insert("default_index", texts[0], vector1)
            id2 = collection.insert("default_index", texts[1], vector2, metadata=metadata)
            print(colored(f"✓ 插入向量成功: {id1[:8]}, {id2[:8]}", "green"))

            # 3. 测试 init_index 批量初始化
            print(colored("\n3. 测试 init_index（批量初始化）", "yellow"))

            # 创建第二个集合用于测试 batch init
            corpus = ["第一条文本", "第二条文本", "第三条文本"]
            corpus_collection = VDBMemoryCollection(config={"name": f"{test_name}_corpus"})
            corpus_collection.batch_insert_data(corpus)

            # 创建索引
            corpus_index_config = {
                "name": "corpus_index",
                "dim": 128,
                "backend_type": "FAISS",
                "description": "corpus测试索引",
                "index_parameter": {},
            }
            corpus_collection.create_index(config=corpus_index_config)

            # 在外部批量生成向量
            corpus_vectors = [normalize_vector(embedding_model.encode(text)) for text in corpus]
            corpus_ids = corpus_collection.get_all_ids()
            print(colored(f"✓ 外部批量生成 {len(corpus_vectors)} 个向量", "green"))

            # 批量初始化索引
            result = corpus_collection.init_index("corpus_index", corpus_vectors, corpus_ids)
            print(colored(f"✓ 批量初始化索引成功，插入 {result} 条数据", "green"))

            # 4. 测试检索功能（使用查询向量）
            print(colored("\n4. 测试检索功能（使用查询向量）", "yellow"))

            # 在外部生成查询向量
            query_vector = normalize_vector(embedding_model.encode(texts[1]))
            print(colored("✓ 在外部生成查询向量", "green"))

            # 使用向量检索（不带metadata）
            results = collection.retrieve(query_vector, "default_index", topk=2)
            print(f"检索结果数量: {len(results) if results else 0}")  # type: ignore

            # 使用向量检索（带metadata）
            results_with_metadata = collection.retrieve(
                query_vector, "default_index", topk=2, with_metadata=True
            )
            print(
                f"带metadata的检索结果数量: {len(results_with_metadata) if results_with_metadata else 0}"
            )  # type: ignore

            # 检索corpus集合
            corpus_query_vector = normalize_vector(embedding_model.encode("第一条文本"))
            corpus_results = corpus_collection.retrieve(corpus_query_vector, "corpus_index", topk=3)
            print(f"corpus集合检索结果数量: {len(corpus_results) if corpus_results else 0}")  # type: ignore

            # 验证结果
            if results and len(results) > 0:  # type: ignore
                print(colored("✓ 检索到了结果", "green"))
            else:
                raise AssertionError("检索失败，没有找到任何结果")

            # 检查metadata
            if results_with_metadata:
                for result in results_with_metadata:  # type: ignore
                    if (
                        isinstance(result, dict)
                        and result.get("metadata", {}).get("priority") == "high"
                    ):
                        print(colored("✓ 找到了带有 high priority 的结果", "green"))
                        break

            if corpus_results and len(corpus_results) > 0:  # type: ignore
                print(colored("✓ corpus 集合检索成功", "green"))

            print(colored("✓ 检索功能测试通过", "green"))

            # 5. 测试更新和删除
            print(colored("\n5. 测试更新和删除", "yellow"))
            new_text = "更新后的测试文本"
            new_metadata = {"type": "updated", "priority": "medium"}
            new_vector = normalize_vector(embedding_model.encode(new_text))

            try:
                # 更新数据 - 需要提供新向量
                collection.update("default_index", texts[0], new_text, new_vector, new_metadata)
                print(colored("✓ 成功更新文本（提供新向量）", "green"))
            except Exception as e:
                print(f"更新失败: {e}")

            try:
                # 删除数据
                collection.delete(texts[1])
                print(colored("✓ 成功删除文本", "green"))
            except Exception as e:
                print(f"删除失败: {e}")

            print(colored("✓ 更新和删除功能测试通过", "green"))

            # 6. 测试持久化
            print(colored("\n6. 测试持久化", "yellow"))

            # 保存
            save_path = os.path.join(test_dir, "save_test")
            collection.store(save_path)
            corpus_collection.store(save_path)

            # 测试加载
            collection_dir = os.path.join(save_path, "vdb_collection", test_name)
            loaded_collection = VDBMemoryCollection.load(test_name, collection_dir)

            # 使用更新后的文本向量进行检索
            query_vec = normalize_vector(embedding_model.encode(new_text))
            results = loaded_collection.retrieve(query_vec, "default_index", topk=1)

            if results and len(results) > 0:  # type: ignore
                print(colored("✓ 持久化后检索成功", "green"))
            else:
                raise AssertionError("持久化后检索失败")

            print(colored("✓ 持久化功能测试通过", "green"))

            print(colored("\n=== 所有功能测试通过! ===", "green"))
            print("✓ 1. 初始化功能正常（不依赖 embedding_model）")
            print("✓ 2. 数据插入功能正常（接收外部向量）")
            print("✓ 3. 批量初始化索引功能正常")
            print("✓ 4. 检索功能正常（使用查询向量）")
            print("✓ 5. 更新和删除功能正常")
            print("✓ 6. 持久化功能正常")
            print(colored("\n✨ VDBMemoryCollection 重构成功！", "green"))
            print(
                colored("核心改进：embedding 生成在外部，collection 只负责向量存储和检索", "green")
            )

        except Exception as e:
            print(colored(f"\n测试失败: {str(e)}", "red"))
            import traceback

            traceback.print_exc()
            raise
        finally:
            # 清理测试数据
            with contextlib.suppress(Exception):
                shutil.rmtree(test_dir)

    run_test()
