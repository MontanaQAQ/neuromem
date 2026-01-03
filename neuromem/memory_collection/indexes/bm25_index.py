"""BM25Index - BM25 文本检索索引

基于 BM25 算法的文本检索索引，适用于关键词搜索。

设计原则：
- 使用 bm25s 库实现高效检索
- 自动检测中英文并选择合适的分词器
- 支持动态插入和删除（自动重建索引）
- 持久化支持

使用场景：
- 关键词检索
- 文档搜索
- 问答系统

配置示例：
    config = {
        "backend": "numba",  # bm25s backend (可选，默认 "numba")
        "language": "auto",  # 语言：auto/zh/en (可选，默认 "auto")
        "custom_stopwords": None,  # 自定义停用词 (可选)
    }
"""

from __future__ import annotations

import logging
import pickle
from pathlib import Path
from typing import Any

import bm25s
import Stemmer

from .base_index import BaseIndex

# 抑制 bm25s 的 DEBUG 日志
logging.getLogger("bm25s").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class BM25Index(BaseIndex):
    """
    BM25 文本检索索引

    Attributes:
        backend: bm25s 后端类型
        language: 语言设置（auto/zh/en）
        custom_stopwords: 自定义停用词
        tokenizer: 分词器
        bm25: bm25s 索引对象
        id_to_idx: data_id -> 内部索引位置
        idx_to_id: 内部索引位置 -> data_id
        texts: 文本列表（用于重建索引）
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        初始化 BM25 索引

        Args:
            config: 配置字典
                - backend: bm25s backend (默认 "numba")
                - language: 语言设置 (默认 "auto")
                - custom_stopwords: 自定义停用词 (默认 None)
        """
        super().__init__(config)

        # 配置参数
        self.backend = self.config.get("backend", "numba")
        self.language = self.config.get("language", "auto")
        self.custom_stopwords = self.config.get("custom_stopwords", None)

        # 索引数据
        self.tokenizer = None
        self.bm25 = None
        self.id_to_idx: dict[str, int] = {}
        self.idx_to_id: dict[int, str] = {}
        self.texts: list[str] = []
        self.tokens: list[list[str]] = []

    def _is_chinese(self, text: str) -> bool:
        """
        判断文本是否包含中文字符

        Args:
            text: 文本

        Returns:
            是否包含中文
        """
        return any("\u4e00" <= ch <= "\u9fff" for ch in text)

    def _get_tokenizer(self, sample_text: str):
        """
        根据文本内容和配置选择分词器

        Args:
            sample_text: 样本文本（用于自动检测语言）

        Returns:
            分词器对象
        """
        # 确定语言
        if self.language == "zh":
            is_zh = True
        elif self.language == "en":
            is_zh = False
        else:  # auto
            is_zh = self._is_chinese(sample_text)

        # 创建分词器
        if is_zh:
            return bm25s.tokenization.Tokenizer(stopwords=self.custom_stopwords or "zh")
        else:
            stemmer = Stemmer.Stemmer("english")
            return bm25s.tokenization.Tokenizer(
                stopwords=self.custom_stopwords or "en", stemmer=stemmer
            )

    def _rebuild_index(self) -> None:
        """
        重建 BM25 索引（在插入/删除后调用）

        Note:
            - 重新分词所有文本
            - 重建 bm25s 索引
        """
        if not self.texts:
            self.tokenizer = None
            self.bm25 = None
            self.tokens = []
            return

        # 创建分词器（基于第一条文本）
        self.tokenizer = self._get_tokenizer(self.texts[0])

        # 分词
        self.tokens = self.tokenizer.tokenize(self.texts, show_progress=False)  # type: ignore

        # 构建 BM25 索引
        self.bm25 = bm25s.BM25(corpus=self.texts, backend=self.backend)
        self.bm25.index(self.tokens, show_progress=False)

    def add(self, data_id: str, text: str, metadata: dict[str, Any]) -> None:
        """
        添加文本到索引

        Args:
            data_id: 数据 ID
            text: 原始文本
            metadata: 元数据（BM25 不使用）

        Note:
            - 如果 data_id 已存在，更新文本并重建索引
            - 添加后会自动重建索引
        """
        # 如果已存在，先删除
        if data_id in self.id_to_idx:
            self.remove(data_id)

        # 添加到末尾
        idx = len(self.texts)
        self.texts.append(text)
        self.id_to_idx[data_id] = idx
        self.idx_to_id[idx] = data_id

        # 重建索引
        self._rebuild_index()

    def remove(self, data_id: str) -> None:
        """
        从索引移除文本

        Args:
            data_id: 数据 ID

        Note:
            - 如果 data_id 不存在，不做任何操作
            - 移除后会自动重建索引
        """
        if data_id not in self.id_to_idx:
            return

        # 获取索引位置
        idx = self.id_to_idx[data_id]

        # 移除文本
        self.texts.pop(idx)

        # 重建映射（所有数据ID保持不变，但索引位置需要重新分配）
        old_idx_to_id = self.idx_to_id.copy()
        self.id_to_idx = {}
        self.idx_to_id = {}

        # 重新分配索引位置（跳过被删除的位置）
        new_idx = 0
        for old_idx in range(len(self.texts) + 1):
            if old_idx == idx:
                continue  # 跳过被删除的位置
            if old_idx in old_idx_to_id:
                id_ = old_idx_to_id[old_idx]
                self.id_to_idx[id_] = new_idx
                self.idx_to_id[new_idx] = id_
                new_idx += 1

        # 重建索引
        self._rebuild_index()

    def query(self, query: Any, **params: Any) -> list[str]:
        """
        查询索引（BM25 文本检索）

        Args:
            query: 查询文本（str）
            **params: 查询参数
                - top_k: 返回结果数量（默认 5）
                - min_score: 最小分数阈值（可选）

        Returns:
            匹配的 data_id 列表（按相关性降序）

        Examples:
            >>> index.query("人工智能", top_k=10)
            >>> index.query("AI", min_score=1.0)
        """
        if not isinstance(query, str):
            msg = "BM25Index.query() requires string query"
            raise TypeError(msg)

        if self.bm25 is None or not self.texts:
            return []

        top_k = params.get("top_k", 5)
        min_score = params.get("min_score")

        # 分词
        query_tokens = self.tokenizer.tokenize([query], show_progress=False)[0]  # type: ignore

        # 搜索
        scores = self.bm25.get_scores(query_tokens)  # type: ignore

        # 排序并过滤
        results = []
        for idx in sorted(range(len(scores)), key=lambda i: -scores[i]):
            score = float(scores[idx])

            # 分数阈值过滤
            if min_score is not None and score < min_score:
                break

            data_id = self.idx_to_id[idx]
            results.append(data_id)

            # top_k 限制
            if len(results) >= top_k:
                break

        return results

    def contains(self, data_id: str) -> bool:
        """
        检查数据是否在索引中

        Args:
            data_id: 数据 ID

        Returns:
            是否存在
        """
        return data_id in self.id_to_idx

    def size(self) -> int:
        """
        获取索引中的文本数量

        Returns:
            文本数量
        """
        return len(self.texts)

    def save(self, path: Path | str) -> None:
        """
        持久化索引到磁盘

        Args:
            path: 保存路径（文件，.pkl 格式）

        Note:
            使用 pickle 保存整个索引对象
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 保存整个对象（使用 pickle）
        save_data = {
            "config": self.config,
            "id_to_idx": self.id_to_idx,
            "idx_to_id": self.idx_to_id,
            "texts": self.texts,
            "backend": self.backend,
            "language": self.language,
            "custom_stopwords": self.custom_stopwords,
        }

        with path.open("wb") as f:
            pickle.dump(save_data, f)

    def load(self, path: Path | str) -> None:
        """
        从磁盘加载索引

        Args:
            path: 加载路径（文件，.pkl 格式）

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        path = Path(path)
        if not path.exists():
            msg = f"Index file not found: {path}"
            raise FileNotFoundError(msg)

        # 加载数据
        with path.open("rb") as f:
            data = pickle.load(f)

        # 恢复配置
        self.config = data["config"]
        self.backend = data.get("backend", "numba")
        self.language = data.get("language", "auto")
        self.custom_stopwords = data.get("custom_stopwords", None)

        # 恢复映射和文本
        self.id_to_idx = data["id_to_idx"]
        self.idx_to_id = data["idx_to_id"]
        self.texts = data["texts"]

        # 重建 BM25 索引
        if self.texts:
            self._rebuild_index()
        else:
            self.bm25 = None
            self.tokenizer = None

    def clear(self) -> None:
        """清空索引"""
        self.texts.clear()
        self.id_to_idx.clear()
        self.idx_to_id.clear()
        self.tokens.clear()
        self.tokenizer = None
        self.bm25 = None
