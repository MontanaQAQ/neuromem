"""IndexFactory - 索引工厂

统一创建各种索引类型的工厂类。

设计原则：
- 使用注册表模式，支持动态注册新索引
- 提供类型检查和错误提示
- 扩展时无需修改工厂代码

使用示例：
    # 创建索引
    index = IndexFactory.create("fifo", {"max_size": 100})

    # 注册自定义索引
    IndexFactory.register("my_index", MyIndexClass)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .base_index import BaseIndex

logger = logging.getLogger(__name__)


class IndexFactory:
    """
    索引工厂 - 统一创建各种索引类型

    Attributes:
        _registry: 索引类型注册表 {type_name: IndexClass}
    """

    _registry: dict[str, type[BaseIndex]] = {}

    @classmethod
    def create(cls, index_type: str, config: dict[str, Any] | None = None) -> BaseIndex:
        """
        创建索引实例

        Args:
            index_type: 索引类型名称（如 "fifo", "faiss", "lsh", "graph"）
            config: 索引配置字典

        Returns:
            索引实例

        Raises:
            ValueError: 如果索引类型未注册

        Examples:
            >>> index = IndexFactory.create("fifo", {"max_size": 100})
            >>> index = IndexFactory.create("faiss", {"dim": 128, "metric": "cosine"})
        """
        if index_type not in cls._registry:
            available_types = ", ".join(sorted(cls._registry.keys()))
            msg = f"Unknown index type: '{index_type}'. Available types: [{available_types}]"
            raise ValueError(msg)

        index_class = cls._registry[index_type]
        config = config or {}

        logger.debug(f"Creating index of type '{index_type}' with config: {config}")
        return index_class(config)

    @classmethod
    def register(cls, index_type: str, index_class: type[BaseIndex]) -> None:
        """
        注册索引类型

        Args:
            index_type: 索引类型名称（建议小写，如 "fifo", "faiss"）
            index_class: 索引类（必须继承 BaseIndex）

        Raises:
            TypeError: 如果 index_class 不是 BaseIndex 的子类

        Examples:
            >>> class MyIndex(BaseIndex):
            ...     pass
            >>> IndexFactory.register("my_index", MyIndex)

        Note:
            - 同名注册会覆盖旧的索引类
            - 建议在索引模块的 __init__.py 中自动注册
        """
        from .base_index import BaseIndex

        if not issubclass(index_class, BaseIndex):
            msg = f"{index_class} must be a subclass of BaseIndex"
            raise TypeError(msg)

        if index_type in cls._registry:
            logger.warning(
                f"Index type '{index_type}' already registered, "
                f"overwriting with {index_class.__name__}"
            )

        cls._registry[index_type] = index_class
        logger.info(f"Registered index type '{index_type}' -> {index_class.__name__}")

    @classmethod
    def list_types(cls) -> list[str]:
        """
        列出所有已注册的索引类型

        Returns:
            索引类型名称列表（按字母顺序）

        Examples:
            >>> IndexFactory.list_types()
            ['faiss', 'fifo', 'graph', 'lsh']
        """
        return sorted(cls._registry.keys())

    @classmethod
    def is_registered(cls, index_type: str) -> bool:
        """
        检查索引类型是否已注册

        Args:
            index_type: 索引类型名称

        Returns:
            是否已注册

        Examples:
            >>> IndexFactory.is_registered("fifo")
            True
            >>> IndexFactory.is_registered("unknown")
            False
        """
        return index_type in cls._registry

    @classmethod
    def unregister(cls, index_type: str) -> bool:
        """
        注销索引类型（谨慎使用）

        Args:
            index_type: 索引类型名称

        Returns:
            是否成功注销（False 表示类型不存在）

        Note:
            - 仅在测试或动态插件场景使用
            - 可能导致现有代码失败
        """
        if index_type not in cls._registry:
            return False

        del cls._registry[index_type]
        logger.info(f"Unregistered index type '{index_type}'")
        return True

    @classmethod
    def clear_registry(cls) -> None:
        """
        清空注册表（仅用于测试）

        Warning:
            - 会导致所有索引类型不可用
            - 仅在单元测试中使用
        """
        cls._registry.clear()
        logger.warning("Cleared all registered index types")
