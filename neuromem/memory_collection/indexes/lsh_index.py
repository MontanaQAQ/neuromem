"""LSHIndex - LSH（局部敏感哈希）索引

基于 LSH 算法的相似性索引，用于快速近似相似搜索。

设计原则：
- 使用 MinHash + LSH Forest 实现
- 自动将文本转换为 n-gram shingles
- 支持快速近似相似搜索（比 FAISS 更快但精度略低）
- 适用于文本去重和相似检测

使用场景：
- 文本去重
- 近似相似搜索
- 快速查找重复内容

配置示例：
    config = {
        "n_gram": 3,           # n-gram 大小（默认 3）
        "num_perm": 128,       # MinHash 排列数（默认 128，影响精度）
        "threshold": 0.5,      # 默认相似度阈值（0-1，默认 0.5）
    }
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from datasketch import MinHash, MinHashLSH

from .base_index import BaseIndex

logger = logging.getLogger(__name__)


class LSHIndex(BaseIndex):
    """
    LSH 索引 - 基于 MinHash 的局部敏感哈希

    Attributes:
        n_gram: n-gram 大小
        num_perm: MinHash 排列数（影响精度）
        threshold: 默认相似度阈值
        lsh: MinHashLSH 对象
        minhashes: data_id -> MinHash 映射
        texts: data_id -> 原始文本 映射（用于重建索引）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 LSH 索引

        Args:
            config: 配置字典
                - n_gram: n-gram 大小（默认 3）
                - num_perm: MinHash 排列数（默认 128）
                - threshold: 默认相似度阈值（默认 0.5）
        """
        super().__init__(config)

        # 配置参数
        self.n_gram = self.config.get("n_gram", 3)
        self.num_perm = self.config.get("num_perm", 128)
        self.threshold = self.config.get("threshold", 0.5)

        # 索引数据
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self.minhashes: dict[str, MinHash] = {}
        self.texts: dict[str, str] = {}

    def _get_shingles(self, text: str) -> set[str]:
        """
        将文本转换为 n-gram shingles

        Args:
            text: 原始文本

        Returns:
            n-gram shingles 集合

        Examples:
            >>> self._get_shingles("hello")  # n_gram=3
            {'hel', 'ell', 'llo'}
        """
        if len(text) < self.n_gram:
            # 文本太短，直接返回整个文本
            return {text}

        shingles = set()
        for i in range(len(text) - self.n_gram + 1):
            shingles.add(text[i : i + self.n_gram])

        return shingles

    def _create_minhash(self, text: str) -> MinHash:
        """
        创建文本的 MinHash 签名

        Args:
            text: 原始文本

        Returns:
            MinHash 对象
        """
        minhash = MinHash(num_perm=self.num_perm)
        shingles = self._get_shingles(text)

        for shingle in shingles:
            minhash.update(shingle.encode("utf-8"))

        return minhash

    def add(
        self, data_id: str, text: str = "", metadata: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """
        添加文本或向量到 LSH 索引

        Args:
            data_id: 数据 ID
            text: 原始文本（如果提供vector则可选）
            metadata: 元数据（LSH 不使用）
            **kwargs: 扩展参数
                - vector: 预计算的embedding向量（可选，暂未实现）

        Note:
            - 如果 data_id 已存在，先移除旧的再添加新的
            - vector参数暂不支持，会抛出NotImplementedError

        Raises:
            NotImplementedError: 如果传入vector参数（向量LSH尚未实现）
        """
        # 检查是否提供了向量（暂不支持）
        if "vector" in kwargs:
            # TODO: 向量LSH（使用Random Projection或其他向量LSH算法）
            # 参考实现：https://github.com/FALCONN-LIB/FALCONN
            raise NotImplementedError(
                "Vector-based LSH not yet implemented. "
                "Use text-based MinHash LSH for now. "
                "For vector similarity, consider using FAISSIndex instead."
            )

        # 现有的文本MinHash逻辑（保持不变）
        # 如果已存在，先移除
        if data_id in self.minhashes:
            self.lsh.remove(data_id)

        # 创建 MinHash
        minhash = self._create_minhash(text)

        # 添加到 LSH 和缓存
        self.lsh.insert(data_id, minhash)
        self.minhashes[data_id] = minhash
        self.texts[data_id] = text

    def remove(self, data_id: str) -> None:
        """
        从 LSH 索引移除数据

        Args:
            data_id: 数据 ID

        Note:
            如果 data_id 不存在，不做任何操作
        """
        if data_id not in self.minhashes:
            return

        self.lsh.remove(data_id)
        del self.minhashes[data_id]
        del self.texts[data_id]

    def query(self, query: str | None = None, **params: Any) -> list[str]:
        """
        查询相似文本

        Args:
            query: 查询文本
            **params: 查询参数
                - threshold: 相似度阈值（可选，覆盖默认值）
                - top_k: 返回结果数量（可选，默认返回所有匹配）

        Returns:
            相似的 data_id 列表

        Raises:
            ValueError: 如果 query 为 None

        Examples:
            >>> index.query("hello world")
            >>> index.query("hello world", threshold=0.7, top_k=5)
        """
        if query is None:
            msg = "LSHIndex requires a query text (str)"
            raise ValueError(msg)

        # 获取参数
        threshold = params.get("threshold", self.threshold)
        top_k = params.get("top_k")

        # 创建查询 MinHash
        query_minhash = self._create_minhash(query)

        # 查询相似项
        # 注意：LSH.query() 返回所有 Jaccard 相似度 >= threshold 的项
        if threshold != self.threshold:
            # 如果阈值不同，需要临时创建新的 LSH
            temp_lsh = MinHashLSH(threshold=threshold, num_perm=self.num_perm)
            for data_id, mh in self.minhashes.items():
                temp_lsh.insert(data_id, mh)
            results = temp_lsh.query(query_minhash)
        else:
            results = self.lsh.query(query_minhash)

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
        return data_id in self.minhashes

    def size(self) -> int:
        """
        获取索引中的数据条数

        Returns:
            数据条数
        """
        return len(self.minhashes)

    def clear(self) -> None:
        """
        清空索引
        """
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self.minhashes.clear()
        self.texts.clear()

    def save(self, save_dir: Path) -> None:
        """
        持久化索引到磁盘

        Args:
            save_dir: 保存目录

        Note:
            - 保存配置、texts、minhashes
            - LSH 对象需要重建（不持久化）
        """
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        # 保存配置
        config_path = save_dir / "config.json"
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

        # 保存文本
        texts_path = save_dir / "texts.json"
        with texts_path.open("w", encoding="utf-8") as f:
            json.dump(self.texts, f, ensure_ascii=False, indent=2)

        logger.info(f"LSHIndex saved to {save_dir}")

    def load(self, load_dir: Path) -> None:
        """
        从磁盘加载索引

        Args:
            load_dir: 加载目录

        Note:
            - 加载配置和文本后，重建 LSH 索引
        """
        load_dir = Path(load_dir)

        # 加载配置
        config_path = load_dir / "config.json"
        with config_path.open("r", encoding="utf-8") as f:
            self.config = json.load(f)

        # 更新参数
        self.n_gram = self.config.get("n_gram", 3)
        self.num_perm = self.config.get("num_perm", 128)
        self.threshold = self.config.get("threshold", 0.5)

        # 加载文本
        texts_path = load_dir / "texts.json"
        with texts_path.open("r", encoding="utf-8") as f:
            self.texts = json.load(f)

        # 重建 LSH 索引
        self.lsh = MinHashLSH(threshold=self.threshold, num_perm=self.num_perm)
        self.minhashes.clear()

        for data_id, text in self.texts.items():
            minhash = self._create_minhash(text)
            self.lsh.insert(data_id, minhash)
            self.minhashes[data_id] = minhash

        logger.info(f"LSHIndex loaded from {load_dir}, {len(self.texts)} items")
