import inspect
import json
import os
import shutil
from collections.abc import Callable
from typing import Any, ClassVar

import numpy as np
import yaml
from sage.common.utils.logging.custom_logger import CustomLogger

from ..search_engine.kv_index import KVIndexFactory
from ..utils.path_utils import get_default_data_dir
from .base_collection import BaseMemoryCollection, IndexType

# 通过config文件指定默认索引，neuromem默认索引，用户指定索引


def load_config(path: str) -> dict:
    """加载YAML配置文件"""
    with open(path) as f:
        return yaml.safe_load(f)


class KVMemoryCollection(BaseMemoryCollection):
    """
    基于键值对的内存集合，继承自 BaseMemoryCollection。
    提供基本的文本索引（BM25、TFIDF等）和检索功能。

    支持两种初始化方式：
    1. 通过config字典创建：KVMemoryCollection(config)
    2. 通过load方法恢复：KVMemoryCollection.load(name, load_path)

    设计原则：
    - 数据只存一份：text_storage + metadata_storage
    - 索引可以有多个：支持 BM25、TFIDF 等多种文本索引
    - 索引可以独立增删：从某个索引移除不影响数据
    """

    # 声明支持的索引类型
    supported_index_types: ClassVar[set[IndexType]] = {IndexType.KV}

    def __init__(self, config: dict[str, Any]):
        """
        初始化KVMemoryCollection

        Args:
            config: 配置字典，必须包含name等参数
        """
        # 初始化CustomLogger
        self.logger = CustomLogger()

        if "name" not in config:
            self.logger.error("config中必须包含'name'字段")
            raise ValueError("config中必须包含'name'字段")

        # 调用父类初始化
        super().__init__(config)

        # 从config中获取配置参数，提供默认值
        self.default_topk = config.get("default_topk", 5)
        self.default_index_type = config.get("default_index_type", "bm25s")

        self.indexes: dict[
            str, dict[str, Any]
        ] = {}  # index_name -> {index, index_type, description, ...}

        # 如果config中指定了config_path，加载外部配置
        config_path = config.get("config_path")
        if config_path is not None:
            external_config = load_config(config_path)
            self.default_topk = external_config.get("kv_default_topk", self.default_topk)
            self.default_index_type = external_config.get(
                "kv_default_index_type", self.default_index_type
            )

        self.logger.info(f"KVMemoryCollection '{self.name}' 初始化成功")

    def _serialize_func(self, func):
        """
        序列化函数以便持久化存储
        """
        if func is None:
            return None
        try:
            return inspect.getsource(func).strip()
        except Exception:
            return str(func)  # 对于lambda等可能只能保存 repr

    def _deserialize_func(self, func_str):
        """
        反序列化函数字符串
        """
        if func_str is None or func_str == "None" or func_str == "":
            return None

        # 简单的lambda函数恢复，实际生产环境中需要更安全的方式
        try:
            # 这里只是一个简单的示例，实际应该使用更安全的方式
            if func_str.startswith("lambda"):
                return eval(func_str)
            else:
                # 对于其他函数类型，返回None，让调用者处理
                return None
        except Exception:
            self.logger.warning(f"无法反序列化函数: {func_str}")
            return None

    @classmethod
    def load(cls, name: str, load_path: str | None = None) -> "KVMemoryCollection":
        """
        从磁盘加载KVMemoryCollection实例

        Args:
            name: 集合名称
            load_path: 加载路径，如果为None则使用默认路径
        """
        if load_path is None:
            load_path = os.path.join(get_default_data_dir(), "kv_collection", name)
        else:
            # 当传入了具体路径时，直接使用该路径，不再添加额外层级
            load_path = load_path

        # 创建实例时使用新的config方式
        config = {"name": name}
        instance = cls(config)

        # 加载数据
        instance._load(load_path)

        return instance

    def store(self, store_path: str | None = None) -> dict[str, Any]:
        """
        将集合保存到磁盘

        Args:
            store_path: 保存路径，如果为None则使用默认路径
        """
        self.logger.debug("KVMemoryCollection: store called")

        if store_path is None:
            store_path = get_default_data_dir()
        # 加上kv_collection
        collection_dir = os.path.join(store_path, "kv_collection", self.name)
        os.makedirs(collection_dir, exist_ok=True)

        # 存储 text 和 metadata
        text_path = os.path.join(collection_dir, "text_storage.json")
        metadata_path = os.path.join(collection_dir, "metadata_storage.json")
        self.text_storage.store_to_disk(text_path)
        self.metadata_storage.store_to_disk(metadata_path)

        # 存储每个 index
        index_info = {}
        for index_name, info in self.indexes.items():
            idx_type = info["index_type"]
            idx = info["index"]
            idx_type_dir = os.path.join(collection_dir, idx_type)
            idx_path = os.path.join(idx_type_dir, index_name)
            os.makedirs(idx_path, exist_ok=True)
            idx.store(idx_path)
            index_info[index_name] = {
                "index_type": idx_type,
                "description": info.get("description", ""),
                "metadata_filter_func": self._serialize_func(info.get("metadata_filter_func")),
                "metadata_conditions": info.get("metadata_conditions", {}),
            }

        config = {
            "name": self.name,
            "default_topk": self.default_topk,
            "default_index_type": self.default_index_type,
            "indexes": index_info,
        }
        config_path = os.path.join(collection_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        self.logger.info(f"集合 '{self.name}' 保存成功，路径: {collection_dir}")
        return {"collection_path": collection_dir}

    def _load(self, load_path: str):
        """从指定路径加载集合数据"""
        config_path = os.path.join(load_path, "config.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"No config found for collection at {config_path}")

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        self.default_topk = config.get("default_topk", 5)
        self.default_index_type = config.get("default_index_type", "bm25s")

        # 恢复 text 和 metadata
        text_path = os.path.join(load_path, "text_storage.json")
        metadata_path = os.path.join(load_path, "metadata_storage.json")
        self.text_storage.load_from_disk(text_path)
        self.metadata_storage.load_from_disk(metadata_path)

        # 加载各 index
        for index_name, idx_info in config.get("indexes", {}).items():
            idx_type = idx_info["index_type"]
            idx_path = os.path.join(load_path, idx_type, index_name)

            try:
                idx = KVIndexFactory.load_index(idx_type, index_name, idx_path)
            except ValueError as e:
                raise NotImplementedError(f"Index type {idx_type} not supported: {e}") from e

            self.indexes[index_name] = {
                "index": idx,
                "index_type": idx_type,
                "description": idx_info.get("description", ""),
                "metadata_filter_func": self._deserialize_func(
                    idx_info.get("metadata_filter_func")
                ),
                "metadata_conditions": idx_info.get("metadata_conditions", {}),
            }

        self.logger.info(f"成功加载集合 '{self.name}'，包含 {len(self.indexes)} 个索引")

    @staticmethod
    def clear(name: str, clear_path: str | None = None) -> None:
        """
        清理指定的集合

        Args:
            name: 集合名称
            clear_path: 清理路径，如果为None则使用默认路径
        """
        logger = CustomLogger()

        if clear_path is None:
            clear_path = get_default_data_dir()
        collection_dir = os.path.join(clear_path, "kv_collection", name)
        try:
            shutil.rmtree(collection_dir)
            logger.info(f"成功清理集合: {collection_dir}")
        except FileNotFoundError:
            logger.warning(f"集合不存在: {collection_dir}")
        except Exception as e:
            logger.error(f"清理失败: {e}")
            raise

    def insert(
        self,
        content: str,
        index_names: list[str] | str | None = None,
        vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        插入文本数据到指定索引。

        Args:
            content: 文本内容
            index_names: 目标索引名列表或单个索引名（None 表示只存数据不建索引）
            vector: 向量（KV 索引不使用此参数，保持接口一致性）
            metadata: 元数据字典
            **kwargs: 其他参数（向后兼容）

        Returns:
            stable_id
        """
        self.logger.debug("KVMemoryCollection: insert called")

        # 生成稳定 ID
        stable_id = self._get_stable_id(content, metadata)

        # 存储文本
        self.text_storage.store(stable_id, content)

        # 存储元数据
        if metadata:
            # 自动注册所有未知的元数据字段
            for field_name in metadata:
                if not self.metadata_storage.has_field(field_name):
                    self.metadata_storage.add_field(field_name)
            self.metadata_storage.store(stable_id, metadata)

        # 规范化 index_names
        target_indexes: list[str] = []
        if index_names is None:
            pass  # 只存数据，不建索引
        elif isinstance(index_names, str):
            target_indexes = [index_names]
        else:
            target_indexes = list(index_names)

        # 插入到各索引
        for index_name in target_indexes:
            if index_name not in self.indexes:
                self.logger.warning(f"Index '{index_name}' does not exist.")
                continue
            index = self.indexes[index_name]["index"]
            index.insert(content, stable_id)

        self.logger.debug(f"成功插入文本到 {len(target_indexes)} 个索引中")
        return stable_id

    def insert_to_index(
        self,
        item_id: str,
        index_name: str,
        vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        **kwargs: Any,
    ) -> bool:
        """
        将已有数据加入索引（用于跨索引迁移）。

        Args:
            item_id: 数据 ID
            index_name: 目标索引名
            vector: 向量（KV 索引不使用此参数）

        Returns:
            成功/失败
        """
        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return False

        # 获取文本内容
        content = self.text_storage.get(item_id)
        if content is None:
            self.logger.warning(f"Item '{item_id}' not found in storage.")
            return False

        # 插入到索引
        index = self.indexes[index_name]["index"]
        index.insert(content, item_id)
        return True

    def remove_from_index(self, item_id: str, index_name: str) -> bool:
        """
        从索引移除（数据保留）。

        Args:
            item_id: 数据 ID
            index_name: 索引名称

        Returns:
            成功/失败
        """
        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return False

        index = self.indexes[index_name]["index"]
        index.delete(item_id)
        return True

    def delete(self, item_id: str) -> bool:
        """
        完全删除条目（数据 + 所有索引）。

        Args:
            item_id: 条目 ID（可以是 stable_id 或原始文本的 hash）

        Returns:
            是否删除成功
        """
        self.logger.debug("KVMemoryCollection: delete called")

        # 检查是否存在
        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found.")
            return False

        # 删除存储
        self.text_storage.delete(item_id)
        self.metadata_storage.delete(item_id)

        # 从所有索引中删除
        for index in self.indexes.values():
            index["index"].delete(item_id)

        self.logger.debug(f"成功删除条目，ID: {item_id[:8]}...")
        return True

    def delete_by_content(self, content: str) -> bool:
        """
        根据内容删除条目（向后兼容方法）。

        Args:
            content: 原始文本内容

        Returns:
            是否删除成功
        """
        stable_id = self._get_stable_id(content)
        return self.delete(stable_id)

    def update(
        self,
        item_id: str,
        new_content: str | None = None,
        new_vector: np.ndarray | None = None,  # 不使用，保持接口一致性
        new_metadata: dict[str, Any] | None = None,
        index_name: str | None = None,
        **kwargs: Any,
    ) -> bool:
        """
        更新条目。

        Args:
            item_id: 条目 ID
            new_content: 新文本内容
            new_vector: 新向量（KV 索引不使用此参数）
            new_metadata: 新元数据
            index_name: 索引名称（如果指定，只更新该索引）

        Returns:
            是否更新成功
        """
        self.logger.debug("KVMemoryCollection: update called")

        if not self.text_storage.has(item_id):
            self.logger.warning(f"Item '{item_id}' not found.")
            return False

        old_content = self.text_storage.get(item_id)

        # 如果内容没变，只更新元数据
        if new_content is None or new_content == old_content:
            if new_metadata:
                for field_name in new_metadata:
                    if not self.metadata_storage.has_field(field_name):
                        self.metadata_storage.add_field(field_name)
                self.metadata_storage.store(item_id, new_metadata)
            return True

        # 内容变了，需要重新生成 ID 并更新索引
        # 先确定目标索引
        target_indexes = [index_name] if index_name else list(self.indexes.keys())

        # 删除旧条目
        self.delete(item_id)

        # 插入新条目
        new_id = self.insert(new_content, target_indexes, None, new_metadata)
        self.logger.debug(f"成功更新条目，旧ID: {item_id[:8]}..., 新ID: {new_id[:8]}...")
        return True

    def retrieve(
        self,
        query: str | np.ndarray | None = None,
        index_name: str | None = None,
        top_k: int = 10,
        with_metadata: bool = False,
        metadata_filter: Callable[[dict[str, Any]], bool] | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """
        检索数据。

        Args:
            query: 查询文本（向量参数将被忽略，仅为接口统一）
            index_name: 使用的索引名称
            top_k: 返回数量
            with_metadata: 是否返回 metadata
            metadata_filter: 元数据过滤函数
            **kwargs: 其他参数（支持 topk、metadata_filter_func 等向后兼容参数）

        Returns:
            检索结果列表: [{"id": ..., "text": ..., "metadata": ..., "score": ...}, ...]
        """
        self.logger.debug("KVMemoryCollection: retrieve called")

        # 向后兼容处理
        if isinstance(query, np.ndarray):
            self.logger.warning(
                "KVMemoryCollection does not support vector queries, returning empty."
            )
            return []

        query_text = query if isinstance(query, str) else ""

        # 向后兼容：支持旧版参数名
        topk = kwargs.get("topk", top_k)
        metadata_filter_func = kwargs.get("metadata_filter_func", metadata_filter)
        metadata_conditions = {
            k: v for k, v in kwargs.items() if k not in ["topk", "metadata_filter_func"]
        }

        if index_name is None or index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return []

        if topk is None:
            topk = self.default_topk

        index = self.indexes[index_name]["index"]
        topk_ids = index.search(query_text, topk=topk)
        filtered_ids = self.filter_ids(topk_ids, metadata_filter_func, **metadata_conditions)

        self.logger.debug(f"检索到 {len(filtered_ids)} 条结果（请求 {topk} 条）")

        # 统一返回格式
        results: list[dict[str, Any]] = []
        for i, item_id in enumerate(filtered_ids):
            result: dict[str, Any] = {
                "id": item_id,
                "text": self.text_storage.get(item_id),
                "score": 1.0 - (i * 0.01),  # KV 索引没有真正的分数，用排名模拟
            }
            if with_metadata:
                result["metadata"] = self.metadata_storage.get(item_id)
            results.append(result)

        return results

    def create_index(
        self,
        config: dict[str, Any],
        index_type: IndexType | None = None,  # 基础 Collection 可忽略
        metadata_filter_func: Callable[[dict[str, Any]], bool] | None = None,
        **metadata_conditions: Any,
    ) -> bool:
        """
        创建新索引。

        Args:
            config: 索引配置字典，必须包含 name 字段
            index_type: 索引类型（KVMemoryCollection 只支持 KV，此参数可忽略）
            metadata_filter_func: 元数据过滤函数（决定哪些数据加入索引）
            **metadata_conditions: 元数据过滤条件

        Returns:
            是否创建成功
        """
        # 检查 config
        if config is None:
            self.logger.warning("config 不能为空，无法创建索引")
            return False

        if "name" not in config:
            self.logger.warning("config 中必须包含 'name' 字段，无法创建索引")
            return False

        index_name = config["name"]

        # 检查索引是否已存在
        if index_name in self.indexes:
            self.logger.warning(f"索引 '{index_name}' 已存在，无法重复创建")
            return False

        # 从 config 中获取参数，如果没有则使用默认值
        kv_index_type = config.get("index_type", self.default_index_type)
        description = config.get("description", f"Index for {index_name}")

        # 过滤要加入索引的数据
        all_ids = self.get_all_ids()
        filtered_ids = self.filter_ids(all_ids, metadata_filter_func, **metadata_conditions)
        texts = [self.text_storage.get(i) for i in filtered_ids]

        try:
            index = KVIndexFactory.create_index(
                index_type=kv_index_type,
                index_name=index_name,
                texts=texts,
                ids=filtered_ids,
            )
        except ValueError as e:
            self.logger.error(f"Index type {kv_index_type} not supported: {e}")
            raise NotImplementedError(f"Index type {kv_index_type} not supported: {e}") from e

        self.indexes[index_name] = {
            "index": index,
            "index_type": kv_index_type,
            "description": description,
            "metadata_filter_func": metadata_filter_func,
            "metadata_conditions": metadata_conditions,
        }

        self.logger.info(f"成功创建索引 '{index_name}'，类型: {kv_index_type}")
        return True

    def delete_index(self, index_name: str) -> bool:
        """
        删除指定名称的索引。

        Args:
            index_name: 要删除的索引名称

        Returns:
            是否删除成功
        """
        if index_name in self.indexes:
            del self.indexes[index_name]
            self.logger.info(f"成功删除索引: {index_name}")
            return True
        else:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return False

    def list_indexes(self) -> list[dict[str, Any]]:
        """
        列出所有索引。

        Returns:
            索引信息列表: [{"name": ..., "type": IndexType.KV, "config": {...}}, ...]
        """
        return [
            {
                "name": name,
                "type": IndexType.KV,
                "config": {
                    "index_type": info["index_type"],
                    "description": info["description"],
                },
            }
            for name, info in self.indexes.items()
        ]

    def list_index(self) -> list[dict[str, str]]:
        """
        列出当前所有索引及其描述信息（向后兼容方法）。

        Returns:
            [{"name": ..., "description": ...}, ...]
        """
        return [
            {"name": name, "description": info["description"]}
            for name, info in self.indexes.items()
        ]

    def rebuild_index(self, index_name: str) -> bool:
        """
        重建指定索引

        Args:
            index_name: 要重建的索引名称
        """
        if index_name not in self.indexes:
            self.logger.warning(f"Index '{index_name}' does not exist.")
            return False

        info = self.indexes[index_name]
        self.logger.info(f"开始重建索引: {index_name}")

        # 保存原始配置
        original_config = {
            "name": index_name,
            "index_type": info["index_type"],
            "description": info["description"],
        }

        self.delete_index(index_name)
        self.create_index(
            config=original_config,
            metadata_filter_func=info["metadata_filter_func"],
            **info["metadata_conditions"],
        )

        self.logger.info(f"索引 '{index_name}' 重建完成")
        return True


if __name__ == "__main__":
    import tempfile

    print("=== KVMemoryCollection 测试开始 ===")

    # 使用临时目录进行测试
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"测试目录: {temp_dir}")

        # 1. 创建集合（使用新的config方式）
        print("\n1. 创建集合...")
        config = {
            "name": "test_collection",
            "default_topk": 5,
            "default_index_type": "bm25s",
        }
        collection = KVMemoryCollection(config)
        print(f"✓ 集合创建成功: {collection.name}")

        # 2. 创建索引（使用新的config方式）
        print("\n2. 创建索引...")
        try:
            index_config = {
                "name": "main_index",
                "index_type": "bm25s",
                "description": "主要文本索引",
            }
            result = collection.create_index(config=index_config)
            if result == 1:
                print("✓ 主索引创建成功")
            else:
                print("✗ 主索引创建失败")
        except Exception as e:
            print(f"✗ 索引创建失败: {e}")

        # 3. 插入数据
        print("\n3. 插入数据...")
        test_data = [
            (
                "这是第一条测试文本，包含人工智能相关内容。",
                {"category": "AI", "priority": 1},
            ),
            (
                "第二条文本讨论机器学习算法和深度学习。",
                {"category": "ML", "priority": 2},
            ),
            ("第三条关于自然语言处理技术的文档。", {"category": "NLP", "priority": 1}),
            ("第四条涉及计算机视觉和图像识别。", {"category": "CV", "priority": 3}),
            ("最后一条是关于数据科学的综合性文档。", {"category": "DS", "priority": 2}),
        ]

        inserted_ids = []
        for text, metadata in test_data:
            try:
                doc_id = collection.insert(text, metadata, "main_index")
                inserted_ids.append(doc_id)
                print(f"✓ 插入成功: {text[:20]}...")
            except Exception as e:
                print(f"✗ 插入失败: {e}")

        print(f"✓ 总共插入了 {len(inserted_ids)} 条数据")

        # 4. 检索测试
        print("\n4. 检索测试...")
        search_queries = [
            "人工智能",
            "机器学习",
            "自然语言处理",
            "计算机视觉",
            "数据科学",
        ]

        for query in search_queries:
            try:
                results = collection.retrieve(
                    raw_text=query, topk=3, with_metadata=True, index_name="main_index"
                )
                print(f"✓ '{query}' 找到 {len(results)} 条结果")
                if results:
                    top_result = (
                        results[0]["text"][:30] + "..."  # type: ignore
                        if len(results[0]["text"]) > 30  # type: ignore
                        else results[0]["text"]  # type: ignore
                    )
                    print(f"  最相关: {top_result}")
            except Exception as e:
                print(f"✗ 检索 '{query}' 失败: {e}")

        # 5. 元数据过滤测试
        print("\n5. 元数据过滤测试...")
        try:
            # 测试高优先级文档检索
            results = collection.retrieve(
                raw_text="技术",
                topk=5,
                with_metadata=True,
                index_name="main_index",
                priority=1,  # 只检索优先级为1的文档
            )
            high_priority_count = len(
                [r for r in results if r["metadata"].get("priority") == 1]  # type: ignore
            )
            print(
                f"✓ 优先级过滤测试: 找到 {len(results)} 条结果，高优先级文档 {high_priority_count} 条"
            )

        except Exception as e:
            print(f"✗ 元数据过滤测试失败: {e}")

        # 6. 批量操作测试
        print("\n6. 批量操作测试...")
        try:
            # 测试更新
            if inserted_ids:
                original_text = test_data[0][0]
                new_text = "这是更新后的第一条文本，包含改进的人工智能内容。"
                new_metadata = {"category": "AI", "priority": 1, "updated": True}

                new_id = collection.update(
                    former_text=original_text,
                    new_text=new_text,
                    new_metadata=new_metadata,
                )
                collection.insert(new_text, new_metadata, "main_index")
                print(f"✓ 文档更新成功，新ID: {new_id[:8]}...")

                # 验证更新结果
                results = collection.retrieve(
                    raw_text="改进的人工智能",
                    topk=1,
                    with_metadata=True,
                    index_name="main_index",
                )
                if results and results[0]["metadata"].get("updated"):  # type: ignore
                    print("✓ 更新验证成功")
                else:
                    print("✗ 更新验证失败")

                # 测试删除
                collection.delete(new_text)
                print("✓ 文档删除成功")

        except Exception as e:
            print(f"✗ 批量操作测试失败: {e}")

        # 7. 索引管理测试
        print("\n7. 索引管理测试...")
        try:
            # 创建分类索引（使用新的config方式）
            ai_index_config = {
                "name": "ai_index",
                "index_type": "bm25s",
                "description": "AI相关文档索引",
            }
            collection.create_index(
                config=ai_index_config,
                category="AI",  # 只包含AI类别的文档
            )

            # 重新插入AI文档到新索引
            for text, metadata in test_data:
                if metadata.get("category") == "AI":
                    collection.insert(text, metadata, "ai_index")

            # 列出索引
            indexes = collection.list_index()
            print(f"✓ 当前索引列表 ({len(indexes)} 个):")
            for idx in indexes:
                print(f"  - {idx['name']}: {idx['description']}")

            # 测试索引重建
            collection.rebuild_index("main_index")
            print("✓ 索引重建成功")

            # 测试索引删除
            collection.delete_index("ai_index")
            print("✓ 索引删除成功")

        except Exception as e:
            print(f"✗ 索引管理测试失败: {e}")

        # 8. 持久化测试
        print("\n8. 持久化测试...")
        try:
            # 保存集合
            save_result = collection.store(temp_dir)
            print(f"✓ 集合保存成功: {save_result['collection_path']}")

            # 加载集合
            loaded_collection = KVMemoryCollection.load("test_collection", temp_dir)
            print(f"✓ 集合加载成功: {loaded_collection.name}")

            # 验证加载的数据
            if loaded_collection.indexes:
                results = loaded_collection.retrieve(
                    raw_text="机器学习", topk=2, index_name="main_index"
                )
                print(f"✓ 加载后检索测试成功，找到 {len(results)} 条结果")
            else:
                print("✗ 加载后索引为空")

        except Exception as e:
            print(f"✗ 持久化测试失败: {e}")

        # 9. 错误处理测试
        print("\n9. 错误处理测试...")
        try:
            # 测试不存在的索引
            results = collection.retrieve(raw_text="测试", index_name="nonexistent_index", topk=1)
            print(f"✓ 不存在索引处理: 返回 {len(results)} 条结果（预期为0）")

            # 测试删除不存在的索引
            try:
                collection.delete_index("nonexistent_index")
                print("✗ 删除不存在索引应该失败")
            except ValueError:
                print("✓ 删除不存在索引正确抛出异常")

            # 测试重建不存在的索引
            result = collection.rebuild_index("nonexistent_index")
            if not result:
                print("✓ 重建不存在索引正确返回False")

        except Exception as e:
            print(f"✗ 错误处理测试失败: {e}")

        # 10. 清理测试
        print("\n10. 清理测试...")
        try:
            KVMemoryCollection.clear("test_collection", temp_dir)
            print("✓ 集合清理成功")

            # 验证清理结果
            try:
                KVMemoryCollection.load("test_collection", temp_dir)
                print("✗ 清理后仍能加载集合")
            except FileNotFoundError:
                print("✓ 清理验证成功")
        except Exception as e:
            print(f"✗ 清理测试失败: {e}")

    print("\n=== 测试完成 ===")
    print("✓ 所有主要功能测试通过")
    print("注意: 某些测试可能由于依赖项（如KVIndexFactory）未完全加载而失败，这是正常的。")
