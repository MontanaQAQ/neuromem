"""
MemoryManager: Collection 的统一管理器。

职责：
- 创建 Collection（根据 backend_type）
- 管理 Collection 生命周期
- 懒加载支持
- 持久化管理

设计原则：
- 使用注册表 + 工厂模式创建 Collection
- 统一持久化路径结构
- 支持扩展新的 Collection 类型
"""

from __future__ import annotations

import json
import os
import shutil
from typing import TYPE_CHECKING, Any

from sage.common.utils.logging.custom_logger import CustomLogger

from .memory_collection.base_collection import BaseMemoryCollection
from .memory_collection.graph_collection import GraphMemoryCollection
from .memory_collection.hybrid_collection import HybridCollection
from .memory_collection.kv_collection import KVMemoryCollection
from .memory_collection.vdb_collection import VDBMemoryCollection
from .utils.path_utils import get_default_data_dir

if TYPE_CHECKING:
    pass


class MemoryManager:
    """
    内存管理器，管理不同类型的 MemoryCollection 实例。

    核心职责：
    - 创建 Collection（通过注册表 + 工厂模式）
    - 管理 Collection 生命周期（加载、卸载、删除）
    - 懒加载支持（按需从磁盘加载）
    - 统一持久化管理

    使用示例：
        >>> manager = MemoryManager()
        >>> collection = manager.create_collection({
        ...     "name": "my_vdb",
        ...     "backend_type": "vdb",
        ...     "description": "向量存储"
        ... })
        >>> manager.store_collection("my_vdb")
    """

    # 类级别注册表：backend_type -> Collection 类
    _collection_registry: dict[str, type[BaseMemoryCollection]] = {
        "vdb": VDBMemoryCollection,
        "vector": VDBMemoryCollection,
        "kv": KVMemoryCollection,
        "text": KVMemoryCollection,
        "graph": GraphMemoryCollection,
        "hybrid": HybridCollection,
    }

    @classmethod
    def register_collection_type(
        cls, type_name: str, collection_class: type[BaseMemoryCollection]
    ) -> None:
        """
        注册新的 Collection 类型。

        Args:
            type_name: 类型名称（如 "hybrid", "hierarchical"）
            collection_class: Collection 类

        Example:
            >>> MemoryManager.register_collection_type("hybrid", HybridCollection)
        """
        cls._collection_registry[type_name.lower()] = collection_class

    @classmethod
    def get_registered_types(cls) -> list[str]:
        """获取所有已注册的 Collection 类型。"""
        return list(cls._collection_registry.keys())

    def __init__(self, data_dir: str | None = None):
        """
        初始化 MemoryManager。

        Args:
            data_dir: 数据存储目录，默认使用 get_default_data_dir()
        """
        self.logger = CustomLogger()

        self.collections: dict[str, BaseMemoryCollection] = {}
        self.collection_metadata: dict[str, dict[str, Any]] = {}
        self.collection_status: dict[str, str] = {}  # 状态表: "loaded" or "on_disk"

        # 从默认目录 data/sage_memory 获取 disk 中的 manager (如果有)
        self.data_dir = data_dir or get_default_data_dir()
        self.manager_path = os.path.join(self.data_dir, "manager.json")
        self.logger.info(f"MemoryManager initialized with data_dir: {self.data_dir}")
        self._load_manager()

    # ==================== 路径管理 ====================

    def _get_collection_path(self, name: str, backend_type: str) -> str:
        """
        获取 Collection 的存储路径。

        统一路径结构：data_dir/collections/{backend_type}/{name}/

        Args:
            name: Collection 名称
            backend_type: 后端类型

        Returns:
            Collection 存储路径
        """
        return os.path.join(self.data_dir, "collections", backend_type.lower(), name)

    def _get_legacy_collection_path(self, name: str, backend_type: str) -> str:
        """
        获取旧版 Collection 的存储路径（向后兼容）。

        旧路径结构：data_dir/{backend_type}_collection/{name}/

        Args:
            name: Collection 名称
            backend_type: 后端类型

        Returns:
            Collection 存储路径
        """
        return os.path.join(self.data_dir, f"{backend_type.lower()}_collection", name)

    def _find_collection_path(self, name: str, backend_type: str) -> str | None:
        """
        查找 Collection 路径（优先新路径，回退旧路径）。

        Args:
            name: Collection 名称
            backend_type: 后端类型

        Returns:
            存在的 Collection 路径，或 None
        """
        # 优先查找新路径
        new_path = self._get_collection_path(name, backend_type)
        if os.path.exists(new_path):
            return new_path

        # 回退到旧路径（向后兼容）
        legacy_path = self._get_legacy_collection_path(name, backend_type)
        if os.path.exists(legacy_path):
            return legacy_path

        return None

    # ==================== Collection CRUD ====================

    def create_collection(
        self, config: dict[str, Any] | None = None
    ) -> BaseMemoryCollection | None:
        """
        创建新的 Collection 并返回。

        使用注册表 + 工厂模式，避免硬编码类型判断。

        Args:
            config: 配置字典，必须包含:
                - name: Collection 名称
                - backend_type: 后端类型（vdb, kv, graph, vector, text 等）
                - description: 描述（可选）
                - 其他类型特定配置

        Returns:
            创建的 Collection 实例，失败返回 None
        """
        if config is None:
            config = {}

        # 检查 name 参数
        name = config.get("name")
        if not name:
            self.logger.warning("`name` is required in config but not provided.")
            return None
        if name in self.collection_metadata:
            self.logger.warning(f"Collection with name '{name}' already exists.")
            return None

        # 检查 backend_type
        backend_type = config.get("backend_type")
        if not backend_type:
            self.logger.warning("`backend_type` is required in config but not provided.")
            return None

        backend_type = backend_type.lower()

        # 通过注册表获取 Collection 类（精确匹配）
        collection_class = self._collection_registry.get(backend_type)
        if not collection_class:
            self.logger.warning(
                f"Unknown backend_type: '{backend_type}'. "
                f"Available types: {list(self._collection_registry.keys())}"
            )
            return None

        # 使用统一的 config 创建 Collection
        try:
            new_collection = collection_class(config)
        except Exception as e:
            self.logger.error(f"Failed to create collection '{name}': {e}")
            return None

        # 存储到 collections
        metadata = {
            "description": config.get("description", ""),
            "backend_type": backend_type,
        }
        self.collections[name] = new_collection
        self.collection_metadata[name] = metadata
        self.collection_status[name] = "loaded"

        self.logger.info(f"Created collection '{name}' with backend_type '{backend_type}'")

        # 注意：不立即保存 manager.json，只在 store_collection() 时保存
        # 这样避免元数据与实际数据不一致的问题

        return new_collection

    def has_collection(self, name: str) -> bool:
        """
        检查 Collection 是否存在（内存或磁盘）。

        Args:
            name: Collection 名称

        Returns:
            是否存在
        """
        return name in self.collections or name in self.collection_metadata

    def get_collection(self, name: str) -> BaseMemoryCollection | None:
        """
        获取 Collection，支持懒加载。

        优先返回内存中的实例，如不在内存则尝试从磁盘懒加载。

        Args:
            name: Collection 名称

        Returns:
            Collection 实例，不存在返回 None
        """
        # 1. 优先返回内存中的实例
        if name in self.collections:
            return self.collections[name]

        # 2. 检查是否在磁盘上（通过元数据判断）
        if name not in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' not found.")
            return None

        # 3. 懒加载
        self.logger.info(f"Lazy loading collection '{name}' from disk...")
        return self._load_collection(name)

    def delete_collection(self, name: str) -> bool:
        """
        删除 Collection：内存、元数据、磁盘三处都要删。

        Args:
            name: Collection 名称

        Returns:
            是否成功删除
        """
        existed = False
        backend_type = None

        # 1. 从内存中删除
        if name in self.collections:
            del self.collections[name]
            existed = True

        # 2. 获取 backend_type 并从元信息中删除
        if name in self.collection_metadata:
            backend_type = self.collection_metadata[name].get("backend_type")
            del self.collection_metadata[name]
            self.collection_status.pop(name, None)
            existed = True

        # 3. 删除磁盘文件（无论元信息是否存在都尝试删除）
        possible_types = [backend_type] if backend_type else ["vdb", "kv", "graph"]

        for btype in possible_types:
            if not btype:
                continue

            # 尝试新路径和旧路径
            for path in [
                self._get_collection_path(name, btype),
                self._get_legacy_collection_path(name, btype),
            ]:
                if os.path.exists(path):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                            self.logger.info(f"Deleted disk collection directory: {path}")
                        else:
                            os.remove(path)
                            self.logger.info(f"Deleted disk collection file: {path}")
                        existed = True
                    except Exception as e:
                        self.logger.warning(f"Failed to delete collection '{name}' at {path}: {e}")

        if not existed:
            self.logger.warning(f"Collection '{name}' not found.")
            return False

        self._save_manager()
        return True

    # ==================== 持久化管理 ====================

    def store_collection(self, name: str | None = None) -> dict[str, Any]:
        """
        持久化 Collection 到磁盘。

        如果指定 name 只保存一个，否则保存所有已加载的 Collection。

        Args:
            name: Collection 名称（可选，None 表示保存所有已加载的）

        Returns:
            存储结果字典：{collection_name: {"collection_path": ..., ...}, ...}
        """
        results: dict[str, Any] = {}

        # 确定要保存的 Collection 列表
        collections_to_save = (
            [name]
            if name
            else [n for n, status in self.collection_status.items() if status == "loaded"]
        )

        for cname in collections_to_save:
            if cname not in self.collections:
                self.logger.warning(f"Collection '{cname}' not in memory, skipping.")
                continue

            collection = self.collections[cname]
            if not hasattr(collection, "store"):
                self.logger.warning(f"Collection '{cname}' does not support store, skipping.")
                continue

            try:
                # 调用 Collection 的 store 方法
                # 注意：现有 Collection 的 store 方法会自己处理路径
                # 这里传递 data_dir，保持向后兼容
                result = collection.store(self.data_dir)
                results[cname] = result
                self.logger.debug(f"Stored collection '{cname}'")
            except Exception as e:
                self.logger.error(f"Failed to store collection '{cname}': {e}")
                results[cname] = {"error": str(e)}

        self._save_manager()
        return results

    def store_all(self) -> dict[str, Any]:
        """
        持久化所有 Collection + Manager 自身状态。

        Returns:
            存储结果字典
        """
        return self.store_collection(name=None)

    def _save_manager(self) -> None:
        """保存 Manager 元数据到磁盘。"""
        os.makedirs(os.path.dirname(self.manager_path), exist_ok=True)
        with open(self.manager_path, "w", encoding="utf-8") as f:
            json.dump(self.collection_metadata, f, ensure_ascii=False, indent=2)
        self.logger.debug(f"Manager info saved to {self.manager_path}")

    def _load_manager(self) -> None:
        """
        加载 Manager 元数据（只加载 metadata 和状态，不加载 Collection 本体）。
        """
        if not os.path.exists(self.manager_path):
            return
        try:
            with open(self.manager_path, encoding="utf-8") as f:
                self.collection_metadata = json.load(f)
            for name in self.collection_metadata:
                self.collection_status[name] = "on_disk"
            self.logger.debug(f"Loaded manager info from {self.manager_path}")
        except Exception as e:
            self.logger.warning(f"Failed to load manager info: {e}")

    def _load_collection(self, name: str) -> BaseMemoryCollection | None:
        """
        从磁盘懒加载 Collection 进内存。

        使用注册表获取 Collection 类，避免硬编码类型判断。

        Args:
            name: Collection 名称

        Returns:
            加载的 Collection 实例，失败返回 None
        """
        if name not in self.collection_metadata:
            self.logger.warning(f"Collection '{name}' metadata not found in manager.")
            return None

        meta = self.collection_metadata[name]
        backend_type = meta.get("backend_type")

        if not backend_type:
            self.logger.warning(f"Collection '{name}' has no backend_type in metadata.")
            return None

        # 通过注册表获取 Collection 类
        collection_class = self._collection_registry.get(backend_type.lower())
        if not collection_class:
            self.logger.warning(f"Unknown backend_type: '{backend_type}'")
            return None

        # 查找 Collection 路径
        load_path = self._find_collection_path(name, backend_type)
        if not load_path:
            self.logger.warning(f"Collection '{name}' path not found on disk.")
            return None

        try:
            # 使用 Collection 类的 load 方法
            collection = collection_class.load(name, load_path)
            self.collections[name] = collection
            self.collection_status[name] = "loaded"
            self.logger.info(f"Loaded collection '{name}' from {load_path}")
            return collection
        except Exception as e:
            self.logger.error(f"Failed to load collection '{name}': {e}")
            return None

    # ==================== 查询与列表 ====================

    def list_collections(
        self,
        backend_type: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        列出所有 Collection 的基本信息，支持过滤。

        Args:
            backend_type: 按后端类型过滤（可选）
            status: 按状态过滤（"loaded" 或 "on_disk"，可选）

        Returns:
            Collection 信息列表: [{"name": ..., "backend_type": ..., "status": ..., "description": ...}, ...]
        """
        result = []
        for name, metadata in self.collection_metadata.items():
            # 过滤 backend_type
            if backend_type and metadata.get("backend_type") != backend_type.lower():
                continue
            # 过滤状态
            current_status = self.collection_status.get(name, "unknown")
            if status and current_status != status:
                continue

            result.append(
                {
                    "name": name,
                    "backend_type": metadata.get("backend_type", "unknown"),
                    "status": current_status,
                    "description": metadata.get("description", ""),
                }
            )
        return result

    def list_collection(self, name: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """
        列出一个或所有 Collection 的基本信息（向后兼容方法）。

        Args:
            name: Collection 名称（可选，None 表示列出所有）

        Returns:
            单个 Collection 信息字典，或所有 Collection 的列表
        """
        if name:
            if name not in self.collection_metadata:
                self.logger.warning(f"Collection '{name}' not found.")
                return {}
            return {
                "name": name,
                "status": self.collection_status.get(name, "unknown"),
                **self.collection_metadata[name],
            }
        return self.list_collections()

    # ==================== 批量操作 ====================

    def unload_collection(self, name: str) -> bool:
        """
        从内存卸载 Collection（保留磁盘数据）。

        用于内存管理，释放不活跃的 Collection。

        Args:
            name: Collection 名称

        Returns:
            是否成功卸载
        """
        if name not in self.collections:
            self.logger.warning(f"Collection '{name}' not in memory.")
            return False

        # 先持久化
        self.store_collection(name)

        # 从内存删除
        del self.collections[name]
        self.collection_status[name] = "on_disk"

        self.logger.info(f"Unloaded collection '{name}' from memory")
        return True

    def clear_all(self, include_disk: bool = False) -> None:
        """
        清空所有 Collection。

        Args:
            include_disk: 是否同时删除磁盘数据
        """
        # 清空内存中的 Collection
        self.collections.clear()

        if include_disk:
            # 删除所有磁盘数据
            for name, metadata in list(self.collection_metadata.items()):
                backend_type = metadata.get("backend_type")
                if backend_type:
                    # 尝试删除新路径和旧路径
                    for path in [
                        self._get_collection_path(name, backend_type),
                        self._get_legacy_collection_path(name, backend_type),
                    ]:
                        if os.path.exists(path):
                            try:
                                shutil.rmtree(path)
                            except Exception as e:
                                self.logger.warning(f"Failed to delete {path}: {e}")

            # 清空元数据和状态
            self.collection_metadata.clear()
            self.collection_status.clear()

            # 删除 manager.json
            if os.path.exists(self.manager_path):
                try:
                    os.remove(self.manager_path)
                except Exception as e:
                    self.logger.warning(f"Failed to delete manager.json: {e}")

            self.logger.info("Cleared all collections (including disk data)")
        else:
            # 只更新状态为 on_disk
            for name in self.collection_metadata:
                self.collection_status[name] = "on_disk"
            self.logger.info("Cleared all collections from memory (disk data preserved)")

    # ==================== 重命名 ====================

    def rename(self, former_name: str, new_name: str, new_description: str | None = None) -> bool:
        """
        重命名 Collection 并更新描述。

        Args:
            former_name: 原名称
            new_name: 新名称
            new_description: 新描述（可选）

        Returns:
            是否成功重命名
        """
        if former_name not in self.collection_metadata:
            self.logger.warning(f"Collection '{former_name}' not found.")
            return False
        if new_name in self.collection_metadata:
            self.logger.warning(f"Collection '{new_name}' already exists.")
            return False

        # 重命名内存对象
        if former_name in self.collections:
            collection = self.collections.pop(former_name)
            collection.name = new_name
            self.collections[new_name] = collection

        # 重命名状态表
        if former_name in self.collection_status:
            self.collection_status[new_name] = self.collection_status.pop(former_name)

        # 更新元信息
        metadata = self.collection_metadata.pop(former_name)
        if new_description is not None:
            metadata["description"] = new_description
        self.collection_metadata[new_name] = metadata

        # 重命名磁盘目录/文件
        backend_type = metadata.get("backend_type")
        if backend_type:
            # 尝试重命名新路径
            old_path = self._get_collection_path(former_name, backend_type)
            new_path = self._get_collection_path(new_name, backend_type)
            if os.path.exists(old_path):
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                os.rename(old_path, new_path)
            else:
                # 尝试重命名旧路径
                old_legacy = self._get_legacy_collection_path(former_name, backend_type)
                new_legacy = self._get_legacy_collection_path(new_name, backend_type)
                if os.path.exists(old_legacy):
                    os.rename(old_legacy, new_legacy)

        self._save_manager()
        self.logger.info(f"Renamed collection '{former_name}' to '{new_name}'")
        return True


if __name__ == "__main__":
    import tempfile

    def print_result(expect: str, actual: str, passed: bool) -> None:
        green = "\033[92m"
        red = "\033[91m"
        endc = "\033[0m"
        print(f"预期结果：{expect}")
        print(f"实际结果：{actual}")
        print("是否通过测试：", end="")
        print(f"{green}是{endc}" if passed else f"{red}否{endc}")
        print("=" * 50)

    # 使用临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"\n测试目录: {temp_dir}\n")

        # 测试1: 创建新VDB collection（使用正确的 config 字典）
        manager = MemoryManager(data_dir=temp_dir)
        c1 = manager.create_collection({"name": "test_vdb", "backend_type": "vdb"})
        passed = c1 is not None and "test_vdb" in manager.collections
        print_result(
            "新建test_vdb后能在collections中查到",
            str("test_vdb" in manager.collections),
            passed,
        )

        # 测试2: 再次新建同名collection应警告并返回None
        c2 = manager.create_collection({"name": "test_vdb", "backend_type": "vdb"})
        passed = c2 is None
        print_result("新建已存在collection应返回None", str(c2 is None), passed)

        # 测试3: list_collection返回正确，状态为loaded
        info = manager.list_collection("test_vdb")
        passed = info is not None and info.get("status") == "loaded"
        print_result("list_collection显示状态为loaded", f"{info}", passed)

        # 测试4: get_collection取已存在的
        c3 = manager.get_collection("test_vdb")
        passed = c3 is c1
        print_result("get_collection能返回内存已加载对象", f"id相同: {c3 is c1}", passed)

        # 测试5: store_collection保存已加载collection
        result = manager.store_collection()
        path = os.path.join(temp_dir, "vdb_collection", "test_vdb")
        passed = os.path.exists(path)
        print_result("store_collection后磁盘应有数据目录", str(os.path.exists(path)), passed)

        # 测试6: 模拟"只在磁盘不在内存"的懒加载
        del manager.collections["test_vdb"]
        manager.collection_status["test_vdb"] = "on_disk"
        passed = "test_vdb" not in manager.collections and os.path.exists(path)
        print_result("未加载collection不会在collections", str(passed), passed)

        # 测试7: get_collection能从磁盘懒加载
        c4 = manager.get_collection("test_vdb")
        passed = (
            c4 is not None
            and "test_vdb" in manager.collections
            and manager.collection_status["test_vdb"] == "loaded"
        )
        print_result("get_collection能懒加载on_disk collection", str(passed), passed)

        # 测试8: rename
        r = manager.rename("test_vdb", "renamed_vdb", "renamed desc")
        passed = r and "renamed_vdb" in manager.collections
        print_result("rename操作成功", str(r), passed)

        # 测试9: list_collections 过滤功能
        manager.create_collection({"name": "kv_test", "backend_type": "kv"})
        all_vdb = manager.list_collections(backend_type="vdb")
        passed = len(all_vdb) == 1 and all_vdb[0]["name"] == "renamed_vdb"
        print_result("list_collections过滤backend_type", str(all_vdb), passed)

        # 测试10: unload_collection
        manager.store_collection("renamed_vdb")
        unload_result = manager.unload_collection("renamed_vdb")
        passed = (
            unload_result
            and "renamed_vdb" not in manager.collections
            and manager.collection_status.get("renamed_vdb") == "on_disk"
        )
        print_result("unload_collection从内存卸载", str(passed), passed)

        # 测试11: 注册表扩展
        registered = MemoryManager.get_registered_types()
        passed = "vdb" in registered and "kv" in registered and "graph" in registered
        print_result("get_registered_types返回所有类型", str(registered), passed)

        # 测试12: 用新manager对象从磁盘懒加载
        manager2 = MemoryManager(data_dir=temp_dir)
        loaded = (
            "renamed_vdb" in manager2.collection_metadata
            and manager2.collection_status.get("renamed_vdb") == "on_disk"
        )
        print_result("新manager能从磁盘加载管理信息", str(loaded), loaded)

        # 测试13: clear_all
        manager2.clear_all(include_disk=False)
        passed = len(manager2.collections) == 0
        print_result("clear_all清空内存", str(len(manager2.collections) == 0), passed)

        # 测试14: delete_collection
        manager3 = MemoryManager(data_dir=temp_dir)
        delete_result = manager3.delete_collection("renamed_vdb")
        passed = delete_result and "renamed_vdb" not in manager3.collection_metadata
        print_result("delete_collection删除collection", str(passed), passed)

        print("\n所有测试完成。临时目录将自动清理。")
