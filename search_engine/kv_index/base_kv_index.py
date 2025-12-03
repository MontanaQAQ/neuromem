# file sage/middleware/services/neuromem/search_engine/kv_index/base_kv_index.py

"""
Base class for KV (Key-Value) indexes.

KV indexes provide text-based retrieval (e.g., BM25) with support for:
- Full-text search
- Sorted retrieval by metadata fields
- Range queries on metadata
"""

from abc import ABC, abstractmethod
from typing import Any, Literal


class BaseKVIndex(ABC):
    """
    Abstract base class for KV (Key-Value) indexes.

    Provides interface for:
    - Text insertion and deletion
    - Full-text search (BM25, etc.)
    - Sorted search by metadata fields
    - Range queries on metadata
    - Persistence (store/load)
    """

    def __init__(
        self,
        config: dict | None = None,
        texts: list[str] | None = None,
        ids: list[str] | None = None,
    ):
        """
        Initialize the base class for KV Index.

        Args:
            config: Configuration dictionary
            texts: Optional initial texts
            ids: Optional initial IDs
        """
        self.config = config or {}
        self.name = self.config.get("name", None)

    # ============ Basic CRUD Operations ============

    @abstractmethod
    def insert(self, text: str, id: str) -> None:
        """
        Insert a new entry.

        Args:
            text: Text content
            id: Unique identifier
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        """
        Delete an entry by id.

        Args:
            id: Identifier of entry to delete
        """
        pass

    @abstractmethod
    def update(self, id: str, new_text: str) -> None:
        """
        Update the entry corresponding to the given id.

        Args:
            id: Identifier of entry to update
            new_text: New text content
        """
        pass

    # ============ Search Operations ============

    @abstractmethod
    def search(self, query: str, topk: int = 10) -> list[str]:
        """
        Search for relevant entries and return the most relevant ids.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of matching IDs sorted by relevance
        """
        pass

    @abstractmethod
    def search_with_scores(self, query: str, topk: int = 10) -> list[tuple[str, float]]:
        """
        Search for relevant entries with scores.

        Args:
            query: Search query text
            topk: Maximum number of results

        Returns:
            List of (id, score) tuples sorted by score descending
        """
        pass

    @abstractmethod
    def search_with_sort(
        self,
        query: str,
        topk: int = 10,
        sort_by: str | None = None,
        sort_order: Literal["asc", "desc"] = "desc",
        metadata_getter: Any | None = None,
    ) -> list[str]:
        """
        Search with optional sorting by metadata field.

        Args:
            query: Search query text
            topk: Maximum number of results
            sort_by: Metadata field name to sort by (e.g., "timestamp")
            sort_order: Sort order ("asc" or "desc")
            metadata_getter: Callable to get metadata for an ID
                            Should accept (id: str) -> dict

        Returns:
            List of matching IDs sorted by the specified field
        """
        pass

    @abstractmethod
    def search_range(
        self,
        field: str,
        min_value: Any,
        max_value: Any,
        topk: int = 10,
        metadata_getter: Any | None = None,
    ) -> list[str]:
        """
        Range query on a metadata field.

        Args:
            field: Metadata field name to query
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            topk: Maximum number of results
            metadata_getter: Callable to get metadata for an ID

        Returns:
            List of matching IDs within the range
        """
        pass

    # ============ Persistence ============

    @classmethod
    @abstractmethod
    def load(cls, name: str, root_path: str) -> "BaseKVIndex":
        """
        Load the index instance from disk.

        Args:
            name: Index name
            root_path: Directory path to load from

        Returns:
            Loaded index instance
        """
        pass

    @abstractmethod
    def store(self, root_path: str) -> dict[str, Any]:
        """
        Store the index data to the specified directory.

        Args:
            root_path: Directory path to save to

        Returns:
            Storage metadata
        """
        pass

    @staticmethod
    @abstractmethod
    def clear(dir_path: str) -> None:
        """
        Remove all index data under the specified directory.

        Args:
            dir_path: Directory to clear
        """
        pass

    # ============ Statistics ============

    def count(self) -> int:
        """
        Get the number of entries in the index.

        Returns:
            Number of entries
        """
        raise NotImplementedError("Subclass should implement count()")

    def get_all_ids(self) -> list[str]:
        """
        Get all IDs in the index.

        Returns:
            List of all IDs
        """
        raise NotImplementedError("Subclass should implement get_all_ids()")
