# file sage/middleware/services/neuromem/search_engine/vdb_index/__init__.py

from typing import Any  # noqa: F401

from .base_vdb_index import BaseVDBIndex


class VDBIndexFactory:
    """向量数据库索引工厂类 - 简化版本"""

    # 注册的索引类型映射
    _index_registry: dict[str, type[BaseVDBIndex]] = {}

    @classmethod
    def register_index(cls, index_type: str, index_class: type[BaseVDBIndex]):
        """注册新的索引类型"""
        if not issubclass(index_class, BaseVDBIndex):
            raise TypeError(f"Index class {index_class} must inherit from BaseVDBIndex")
        cls._index_registry[index_type.upper()] = index_class

    def create_index(self, config: dict[str, Any]) -> BaseVDBIndex:
        """
        创建索引 - 简化版本，只支持config方式创建

        Args:
            config: 配置字典，必须包含 name, dim, backend_type

        Returns:
            创建的索引实例
        """
        # 检查必要字段
        required_fields = ["name", "dim"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置中缺少必要字段: {field}")

        backend_type = config.get("backend_type", "FAISS").upper()

        if backend_type not in self._index_registry:
            raise ValueError(f"不支持的索引类型: {backend_type}")

        index_class = self._index_registry[backend_type]
        return index_class(config=config)  # type: ignore[call-arg]


# 全局工厂实例
index_factory = VDBIndexFactory()


def register_index_type(index_type: str, index_class: type[BaseVDBIndex]):
    """注册新的索引类型"""
    VDBIndexFactory.register_index(index_type, index_class)


def create_index(config: dict[str, Any]) -> BaseVDBIndex:
    """创建索引"""
    return index_factory.create_index(config)


# 注册FAISS索引（faiss-cpu是必需依赖）
def _register_faiss_index():
    """注册FAISS索引类型"""
    from .faiss_index import FaissIndex

    register_index_type("FAISS", FaissIndex)


# 注册SageDB索引（C++ vector database）
def _register_sagedb_index():
    """注册SageDB索引类型"""
    try:
        from .sagedb_index import SageDBIndex

        register_index_type("SAGEDB", SageDBIndex)
    except ImportError:
        # SageDB 可选，如果导入失败则跳过
        pass


# 执行注册
_register_faiss_index()
_register_sagedb_index()


# 导出公共接口
__all__ = [
    "VDBIndexFactory",
    "BaseVDBIndex",
    "index_factory",
    "register_index_type",
    "create_index",
]
