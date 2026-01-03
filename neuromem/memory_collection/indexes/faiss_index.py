"""FAISSIndex - FAISS 向量索引实现

基于 FAISS 库的向量索引，支持高效的相似度搜索。

特性：
- 支持多种距离度量（L2, Inner Product, Cosine）
- 标记删除机制（tombstone）
- 自动重建索引（达到阈值时）
- 向量去重
- 持久化支持

依赖：
- faiss-cpu 或 faiss-gpu
- numpy
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from .base_index import BaseIndex

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 尝试导入 faiss，如果失败给出友好提示
try:
    import faiss
except ImportError:
    logger.error(
        "FAISS not installed. Please install it with: "
        "pip install faiss-cpu  # for CPU version, or "
        "pip install faiss-gpu  # for GPU version"
    )
    raise


class FAISSIndex(BaseIndex):
    """
    FAISS 向量索引

    支持特性：
    - 向量相似度搜索
    - 多种距离度量（L2, IP, Cosine）
    - 标记删除机制
    - 自动索引重建
    - 持久化

    配置参数：
        dim (int): 向量维度，必需
        metric (str): 距离度量，可选值 "l2", "ip", "cosine"，默认 "cosine"
        index_type (str): FAISS 索引类型，默认 "IndexFlatIP"
        tombstone_threshold (int): 墓碑阈值，默认 100
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 FAISS 索引

        Args:
            config: 配置字典

        Raises:
            ValueError: 如果 dim 未指定
        """
        super().__init__(config)

        # 获取必要参数
        self.dim = self.config.get("dim")
        if self.dim is None:
            msg = "Vector dimension 'dim' is required in config"
            raise ValueError(msg)

        self.dim = int(self.dim)

        # 距离度量
        metric = self.config.get("metric", "cosine").lower()
        if metric == "cosine":
            self.metric = faiss.METRIC_INNER_PRODUCT
            self.normalize = True  # Cosine 需要归一化
        elif metric == "ip":
            self.metric = faiss.METRIC_INNER_PRODUCT
            self.normalize = False
        elif metric == "l2":
            self.metric = faiss.METRIC_L2
            self.normalize = False
        else:
            msg = f"Unsupported metric: {metric}. Use 'l2', 'ip', or 'cosine'"
            raise ValueError(msg)

        # 索引类型
        index_type = self.config.get("index_type", "IndexFlatIP")
        self.index_type = index_type

        # ID 映射
        self.id_map: dict[int, str] = {}  # int_id -> string_id
        self.rev_map: dict[str, int] = {}  # string_id -> int_id
        self.next_id: int = 1

        # 向量存储（用于重建索引和去重）
        self.vector_store: dict[str, np.ndarray] = {}  # string_id -> vector
        self.vector_hashes: dict[str, str] = {}  # hash -> string_id

        # 墓碑机制
        self.tombstones: set[str] = set()
        self.tombstone_threshold = self.config.get("tombstone_threshold", 100)

        # 创建 FAISS 索引
        self._faiss_index = self._create_faiss_index()

        logger.info(
            f"Created FAISSIndex: dim={self.dim}, metric={metric}, "
            f"type={index_type}, normalize={self.normalize}"
        )

    def _create_faiss_index(self) -> faiss.IndexIDMap:
        """
        创建 FAISS 底层索引

        Returns:
            FAISS IndexIDMap 实例
        """
        # 简化版本：只支持 Flat 索引
        if self.metric == faiss.METRIC_L2:
            base_index = faiss.IndexFlatL2(self.dim)
        else:  # METRIC_INNER_PRODUCT
            base_index = faiss.IndexFlatIP(self.dim)

        # 包装为 IndexIDMap 以支持自定义 ID
        return faiss.IndexIDMap(base_index)

    def _normalize_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        归一化向量（用于 cosine 相似度）

        Args:
            vector: 输入向量

        Returns:
            归一化后的向量
        """
        norm = np.linalg.norm(vector)
        if norm > 0:
            return vector / norm
        return vector

    def _get_vector_hash(self, vector: np.ndarray) -> str:
        """
        计算向量哈希值（用于去重）

        Args:
            vector: 向量

        Returns:
            MD5 哈希字符串
        """
        return hashlib.md5(vector.tobytes()).hexdigest()

    def _text_to_vector(self, text: str) -> np.ndarray:
        """
        将文本转换为向量（临时实现：随机向量）

        Args:
            text: 文本

        Returns:
            向量

        Note:
            这是一个临时实现，实际应该使用 Embedding 模型
            在 Service 层会提供真实的向量
        """
        # 使用文本哈希作为种子，保证相同文本生成相同向量
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.RandomState(seed)
        vector = rng.randn(self.dim).astype("float32")
        if self.normalize:
            vector = self._normalize_vector(vector)
        return vector

    def add(self, data_id: str, text: str, metadata: dict[str, Any]) -> None:
        """
        添加数据到索引

        Args:
            data_id: 数据 ID
            text: 文本内容（会转换为向量）
            metadata: 元数据（可能包含预计算的向量）

        Note:
            - 如果 metadata 包含 'vector' 字段，直接使用
            - 否则将文本转换为向量
            - 检测重复向量并跳过
        """
        # 获取或生成向量
        if "vector" in metadata and metadata["vector"] is not None:
            vector = np.array(metadata["vector"], dtype="float32")
        else:
            vector = self._text_to_vector(text)

        # 确保维度正确
        if vector.shape[0] != self.dim:
            msg = f"Vector dimension {vector.shape[0]} does not match index dimension {self.dim}"
            raise ValueError(msg)

        # 归一化（如果需要）
        if self.normalize:
            vector = self._normalize_vector(vector)

        # 检测重复
        vector_hash = self._get_vector_hash(vector)
        if vector_hash in self.vector_hashes:
            existing_id = self.vector_hashes[vector_hash]
            if existing_id != data_id:
                logger.debug(f"Duplicate vector detected, skipping: {data_id}")
                return

        # 分配或获取 int ID
        if data_id in self.rev_map:
            # 更新现有向量
            int_id = self.rev_map[data_id]
            # 从墓碑中移除（如果存在）
            self.tombstones.discard(data_id)
        else:
            # 新增向量
            int_id = self.next_id
            self.next_id += 1
            self.id_map[int_id] = data_id
            self.rev_map[data_id] = int_id

        # 添加到 FAISS 索引
        vector_2d = vector.reshape(1, -1)
        int_id_array = np.array([int_id], dtype=np.int64)
        self._faiss_index.add_with_ids(vector_2d, int_id_array)

        # 存储向量和哈希
        self.vector_store[data_id] = vector
        self.vector_hashes[vector_hash] = data_id

        logger.debug(f"Added vector for {data_id} (int_id={int_id})")

    def remove(self, data_id: str) -> None:
        """
        从索引移除数据（标记删除）

        Args:
            data_id: 数据 ID

        Note:
            - 使用墓碑机制，不立即删除
            - 达到阈值时触发索引重建
        """
        if data_id not in self.rev_map:
            logger.debug(f"Data ID not in index: {data_id}")
            return

        # 标记为墓碑
        self.tombstones.add(data_id)
        logger.debug(f"Marked {data_id} as tombstone ({len(self.tombstones)} total)")

        # 检查是否需要重建索引
        if len(self.tombstones) >= self.tombstone_threshold:
            self._rebuild_index()

    def _rebuild_index(self) -> None:
        """
        重建索引（清除墓碑）

        Note:
            - 收集所有有效向量
            - 重新创建 FAISS 索引
            - 更新 ID 映射
        """
        logger.info(
            f"Rebuilding index: {len(self.tombstones)} tombstones, "
            f"{len(self.vector_store)} total vectors"
        )

        # 收集有效向量
        valid_vectors = []
        valid_ids = []
        new_id_map = {}
        new_rev_map = {}
        new_vector_hashes = {}
        new_vector_store = {}

        next_id = 1
        for string_id, vector in self.vector_store.items():
            if string_id not in self.tombstones:
                valid_vectors.append(vector)
                valid_ids.append(string_id)

                new_rev_map[string_id] = next_id
                new_id_map[next_id] = string_id
                new_vector_store[string_id] = vector

                vector_hash = self._get_vector_hash(vector)
                new_vector_hashes[vector_hash] = string_id

                next_id += 1

        # 重新创建索引
        self._faiss_index = self._create_faiss_index()

        # 批量添加有效向量
        if valid_vectors:
            vectors_2d = np.vstack(valid_vectors)
            int_ids = np.array([new_rev_map[sid] for sid in valid_ids], dtype=np.int64)
            self._faiss_index.add_with_ids(vectors_2d, int_ids)

        # 更新映射
        self.id_map = new_id_map
        self.rev_map = new_rev_map
        self.vector_hashes = new_vector_hashes
        self.vector_store = new_vector_store
        self.next_id = next_id
        self.tombstones.clear()

        logger.info(f"Index rebuilt: {len(valid_ids)} vectors retained")

    def query(self, query: Any, **params: Any) -> list[str]:
        """
        查询索引

        Args:
            query: 查询向量（list 或 np.ndarray）或文本
            **params:
                top_k (int): 返回结果数量，默认 10
                threshold (float): 相似度阈值（可选）

        Returns:
            匹配的 data_id 列表

        Raises:
            ValueError: 如果查询向量维度不匹配
        """
        # 转换查询为向量
        if isinstance(query, str):
            query_vector = self._text_to_vector(query)
        elif isinstance(query, (list, np.ndarray)):
            query_vector = np.array(query, dtype="float32")
        else:
            msg = f"Unsupported query type: {type(query)}"
            raise ValueError(msg)

        # 确保维度正确
        if query_vector.shape[0] != self.dim:
            msg = f"Query vector dimension {query_vector.shape[0]} does not match index dimension {self.dim}"
            raise ValueError(msg)

        # 归一化（如果需要）
        if self.normalize:
            query_vector = self._normalize_vector(query_vector)

        # 获取参数
        top_k = params.get("top_k", 10)
        threshold = params.get("threshold")

        # 调整 top_k 以过滤墓碑
        search_k = min(top_k + len(self.tombstones), self._faiss_index.ntotal)
        if search_k == 0:
            return []

        # 搜索
        query_2d = query_vector.reshape(1, -1)
        distances, int_ids = self._faiss_index.search(query_2d, search_k)

        # 转换 int ID 到 string ID，过滤墓碑
        results = []
        for dist, int_id in zip(distances[0], int_ids[0]):
            if int_id == -1:  # FAISS 返回 -1 表示没有更多结果
                break

            string_id = self.id_map.get(int_id)
            if string_id and string_id not in self.tombstones:
                # 应用阈值过滤
                if threshold is not None:
                    if self.metric == faiss.METRIC_L2:
                        if dist > threshold:
                            continue
                    else:  # METRIC_INNER_PRODUCT
                        if dist < threshold:
                            continue

                results.append(string_id)
                if len(results) >= top_k:
                    break

        return results

    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在索引中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在（且未被标记为墓碑）
        """
        return data_id in self.rev_map and data_id not in self.tombstones

    def size(self) -> int:
        """
        获取索引中的有效数据条数

        Returns:
            数据条数（不包括墓碑）
        """
        return len(self.vector_store) - len(self.tombstones)

    def save(self, path: Path | str) -> None:
        """
        持久化索引到磁盘

        Args:
            path: 保存目录

        Note:
            保存内容：
            - faiss_index.bin: FAISS 索引
            - metadata.json: ID 映射、墓碑等元数据
            - vectors.npy: 向量存储
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # 保存 FAISS 索引
        faiss.write_index(self._faiss_index, str(path / "faiss_index.bin"))

        # 保存元数据
        metadata = {
            "config": self.config,
            "id_map": {str(k): v for k, v in self.id_map.items()},
            "rev_map": self.rev_map,
            "next_id": self.next_id,
            "tombstones": list(self.tombstones),
            "vector_hashes": self.vector_hashes,
        }
        with open(path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # 保存向量存储
        vectors_data = {k: v.tolist() for k, v in self.vector_store.items()}
        with open(path / "vectors.json", "w") as f:
            json.dump(vectors_data, f)

        logger.info(f"Saved FAISSIndex to {path}")

    def load(self, path: Path | str) -> None:
        """
        从磁盘加载索引

        Args:
            path: 加载目录

        Raises:
            FileNotFoundError: 如果路径不存在
        """
        path = Path(path)
        if not path.exists():
            msg = f"Index path does not exist: {path}"
            raise FileNotFoundError(msg)

        # 加载 FAISS 索引
        self._faiss_index = faiss.read_index(str(path / "faiss_index.bin"))

        # 加载元数据
        with open(path / "metadata.json") as f:
            metadata = json.load(f)

        self.config = metadata["config"]
        self.id_map = {int(k): v for k, v in metadata["id_map"].items()}
        self.rev_map = metadata["rev_map"]
        self.next_id = metadata["next_id"]
        self.tombstones = set(metadata["tombstones"])
        self.vector_hashes = metadata["vector_hashes"]

        # 加载向量存储
        with open(path / "vectors.json") as f:
            vectors_data = json.load(f)
        self.vector_store = {k: np.array(v, dtype="float32") for k, v in vectors_data.items()}

        logger.info(f"Loaded FAISSIndex from {path}")

    def clear(self) -> None:
        """清空索引"""
        # 重新创建一个空的 FAISS 索引
        self._create_index()
        # 清空映射和元数据
        self.id_map.clear()
        self.rev_map.clear()
        self.next_id = 0
        self.tombstones.clear()
        self.vector_hashes.clear()
        self.vector_store.clear()
        logger.info("Cleared FAISSIndex")

    def __repr__(self) -> str:
        """返回索引的字符串表示"""
        return f"FAISSIndex(dim={self.dim}, size={self.size()}, tombstones={len(self.tombstones)})"
