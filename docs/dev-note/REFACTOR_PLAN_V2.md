# NeuroMem 架构重构方案 v2.0

> **制定日期**: 2026-01-08  
> **目标版本**: v0.3.0.0  
> **重构类型**: Breaking Change（架构级重构）

---

## 一、重构目标

### 核心理念

基于你的想法：
1. **一个 Service 创建一个 Collection 来干活**
2. **全局就一个 Collection 类型（UnifiedCollection）**，不需要派生其他类
3. **Collection 可选自定义的存储 + 自定义的索引后端**

### 设计原则

```
Service Layer (业务逻辑)
    ↓ 1:1 持有
UnifiedCollection (数据容器 + 索引容器)
    ↓ 组合使用
    ├─ Storage Backend (可插拔)
    │   ├─ TextStorage (内存/Redis/...)
    │   ├─ VectorStorage (FAISS/SageDB/Mock/...)
    │   └─ MetadataStorage (JSON/SQLite/...)
    └─ Index Backend (可插拔)
        ├─ FIFOQueueIndex
        ├─ FAISSIndex
        ├─ BM25Index
        ├─ GraphIndex
        ├─ LSHIndex
        └─ SegmentIndex
```

---

## 二、当前问题诊断

### 问题 1: 双轨并行架构（严重冗余）

**现状**:
```
BaseMemoryCollection (抽象基类 384行)
├─ VDBMemoryCollection (1,439行)  ❌ 向量专用
├─ GraphMemoryCollection (729行)   ❌ 图专用
├─ KVMemoryCollection              ❌ KV专用
└─ HybridCollection (1,161行)      ❌ 混合类型

UnifiedCollection (399行)          ✅ 统一实现
```

**代码重复度**:
- **数据存储**: 5 次实现（text_storage, metadata_storage）
- **ID生成**: 5 次实现（SHA256 哈希）
- **索引管理**: 5 次实现（create/delete/list index）
- **持久化**: 4 次实现（store/load）
- **总冗余**: ~4,200 行代码

### 问题 2: 概念混淆

**用户困惑点**:
- 应该用 `VDBMemoryCollection` 还是 `UnifiedCollection`？
- `HybridCollection` 和 `UnifiedCollection` 有什么区别？
- 为什么有些 Service 要传 `UnifiedCollection`，测试却用 `VDBMemoryCollection`？

### 问题 3: 维护成本高

**当前状态**:
- 修改索引逻辑需要同步 5 个 Collection 类
- 新增存储后端需要考虑兼容性
- 测试覆盖分散（50+ 个测试文件）

---

## 三、重构方案详细设计

### 3.1 核心架构：单一 Collection 模式

#### 删除的组件

```bash
# 完全删除以下文件
sage/neuromem/memory_collection/
├─ base_collection.py              ❌ 删除
├─ vdb_collection.py               ❌ 删除
├─ graph_collection.py             ❌ 删除
├─ kv_collection.py                ❌ 删除
├─ hybrid_collection.py            ❌ 删除
└─ enhanced_collections.py         ❌ 删除（paper features迁移到mixin）
```

#### 保留并增强的核心

```python
# sage/neuromem/memory_collection/unified_collection.py

class UnifiedCollection:
    """
    统一数据容器 - NeuroMem 的唯一 Collection 实现

    职责:
    1. 数据管理: 原始数据的增删改查
    2. 索引容器: 动态管理多种索引
    3. 存储抽象: 可插拔的存储后端

    设计:
    - 数据只存一份 (raw_data)
    - 索引可以有多个 (动态添加/删除)
    - 存储后端可配置 (内存/Redis/SageDB/...)
    """

    def __init__(
        self,
        name: str,
        storage_backend: str = "memory",  # 新增: 存储后端选择
        storage_config: dict | None = None,
        config: dict | None = None
    ):
        self.name = name
        self.config = config or {}

        # 数据存储（可插拔后端）
        self.storage = self._create_storage(storage_backend, storage_config)

        # 索引容器
        self.indexes: dict[str, BaseIndex] = {}
        self.index_metadata: dict[str, dict] = {}

    def _create_storage(self, backend: str, config: dict | None):
        """创建可插拔的存储后端"""
        from ..storage_engine import StorageFactory

        if backend == "memory":
            return StorageFactory.create_memory_storage(config)
        elif backend == "redis":
            return StorageFactory.create_redis_storage(config)
        elif backend == "sagedb":
            return StorageFactory.create_sagedb_storage(config)
        else:
            raise ValueError(f"Unknown storage backend: {backend}")

    # === 数据操作 ===
    def insert(self, text: str, metadata: dict | None = None,
               index_names: list[str] | None = None) -> str:
        """插入数据"""
        data_id = self._generate_id(text, metadata)

        # 存储到后端
        self.storage.put(data_id, {
            "text": text,
            "metadata": metadata or {},
            "created_at": time.time()
        })

        # 更新索引
        target_indexes = index_names or list(self.indexes.keys())
        for idx_name in target_indexes:
            if idx_name in self.indexes:
                self.indexes[idx_name].add(data_id, text, metadata or {})

        return data_id

    def get(self, data_id: str) -> dict | None:
        """获取数据"""
        return self.storage.get(data_id)

    def delete(self, data_id: str) -> bool:
        """删除数据（包括所有索引）"""
        # 从所有索引移除
        for index in self.indexes.values():
            index.remove(data_id)

        # 从存储删除
        return self.storage.delete(data_id)

    # === 索引管理 ===
    def add_index(self, name: str, index_type: str,
                  config: dict | None = None) -> bool:
        """动态添加索引"""
        from .indexes import IndexFactory

        if name in self.indexes:
            return False

        self.indexes[name] = IndexFactory.create(index_type, config or {})
        self.index_metadata[name] = {
            "type": index_type,
            "config": config or {},
            "created_at": time.time()
        }
        return True

    def remove_index(self, name: str) -> bool:
        """移除索引（不影响数据）"""
        if name not in self.indexes:
            return False

        del self.indexes[name]
        del self.index_metadata[name]
        return True

    def query(self, index_name: str, query: Any, **params) -> list[dict]:
        """通过索引查询完整数据"""
        if index_name not in self.indexes:
            raise ValueError(f"Index '{index_name}' not found")

        # 查询索引获取 ID 列表
        data_ids = self.indexes[index_name].query(query, **params)

        # 获取完整数据
        results = []
        for data_id in data_ids:
            item = self.storage.get(data_id)
            if item:
                item["id"] = data_id
                results.append(item)

        return results
```

### 3.2 存储后端抽象

#### 新增存储工厂

```python
# sage/neuromem/storage_engine/storage_factory.py

class StorageBackend(ABC):
    """存储后端抽象接口"""

    @abstractmethod
    def put(self, key: str, data: dict) -> bool:
        """存储数据"""
        pass

    @abstractmethod
    def get(self, key: str) -> dict | None:
        """获取数据"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除数据"""
        pass

    @abstractmethod
    def keys(self) -> list[str]:
        """获取所有键"""
        pass


class MemoryStorage(StorageBackend):
    """内存存储（默认）"""

    def __init__(self, config: dict | None = None):
        self.data: dict[str, dict] = {}

    def put(self, key: str, data: dict) -> bool:
        self.data[key] = data
        return True

    def get(self, key: str) -> dict | None:
        return self.data.get(key)

    def delete(self, key: str) -> bool:
        if key in self.data:
            del self.data[key]
            return True
        return False

    def keys(self) -> list[str]:
        return list(self.data.keys())


class RedisStorage(StorageBackend):
    """Redis 存储"""

    def __init__(self, config: dict | None = None):
        import redis
        self.config = config or {}
        self.redis = redis.Redis(
            host=self.config.get("host", "localhost"),
            port=self.config.get("port", 6379),
            db=self.config.get("db", 0)
        )

    def put(self, key: str, data: dict) -> bool:
        import json
        self.redis.set(key, json.dumps(data))
        return True

    def get(self, key: str) -> dict | None:
        import json
        value = self.redis.get(key)
        return json.loads(value) if value else None

    # ... 其他方法


class SageDBStorage(StorageBackend):
    """SageDB 向量数据库存储（适合大规模向量数据）"""

    def __init__(self, config: dict | None = None):
        from sagedb import SageDB
        self.config = config or {}
        self.sagedb = SageDB(
            db_path=self.config.get("db_path", "./sagedb_data"),
            dim=self.config.get("dim", 768)
        )

    # ... 实现接口


class StorageFactory:
    """存储后端工厂"""

    @staticmethod
    def create(backend: str, config: dict | None = None) -> StorageBackend:
        backends = {
            "memory": MemoryStorage,
            "redis": RedisStorage,
            "sagedb": SageDBStorage,
        }

        if backend not in backends:
            raise ValueError(f"Unknown backend: {backend}")

        return backends[backend](config)
```

### 3.3 Service 层保持不变

**关键点**: Service 层完全不需要修改！

```python
# sage/neuromem/services/partitional/fifo_queue_service.py

class FIFOQueueService(BaseMemoryService):
    """FIFO 队列服务 - 无需修改"""

    def __init__(self, collection: UnifiedCollection, config: dict | None = None):
        # 接收 UnifiedCollection（之前就是这样）
        super().__init__(collection, config)

    def _setup_indexes(self):
        # 调用 collection.add_index()（API 保持不变）
        self.collection.add_index("fifo_queue", "fifo", {"max_size": 100})

    # insert/retrieve 等方法无需修改
```

**为什么不用改？**
- Service 通过 `BaseMemoryService` 持有 `UnifiedCollection`
- 只调用 `collection.add_index()`, `collection.insert()`, `collection.query()` 等公开 API
- 这些 API 在重构前后保持一致

---

## 四、重构实施计划

### Phase 1: 准备阶段（Week 1）

#### 任务 1.1: 标记 Deprecated

```python
# sage/neuromem/memory_collection/base_collection.py

import warnings

class BaseMemoryCollection(ABC):
    """
    [DEPRECATED] 将在 v0.3.0.0 中移除

    请使用 UnifiedCollection 替代。

    迁移指南: docs/dev-note/MIGRATION_GUIDE.md
    """

    def __init__(self, config: dict):
        warnings.warn(
            "BaseMemoryCollection is deprecated and will be removed in v0.3.0.0. "
            "Use UnifiedCollection instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # ... 原有代码
```

同样标记:
- `VDBMemoryCollection`
- `GraphMemoryCollection`
- `KVMemoryCollection`
- `HybridCollection`

#### 任务 1.2: 创建迁移文档

```bash
touch docs/dev-note/MIGRATION_GUIDE.md
```

内容示例:
```markdown
# Collection 迁移指南

## 旧代码 → 新代码

### VDBMemoryCollection → UnifiedCollection

**之前**:
```python
from sage.neuromem import VDBMemoryCollection

collection = VDBMemoryCollection({"name": "my_vdb"})
collection.create_index({
    "name": "vector_index",
    "backend_type": "FAISS",
    "dim": 768
})
```

**之后**:
```python
from sage.neuromem import UnifiedCollection

collection = UnifiedCollection("my_vdb")
collection.add_index("vector_index", "faiss", {"dim": 768})
```

### HybridCollection → UnifiedCollection

**之前**:
```python
collection = HybridCollection({"name": "hybrid"})
collection.create_index({"name": "vec", "backend_type": "FAISS", "dim": 768})
collection.create_index({"name": "bm25", "backend_type": "BM25"})
```

**之后**:
```python
collection = UnifiedCollection("hybrid")
collection.add_index("vec", "faiss", {"dim": 768})
collection.add_index("bm25", "bm25", {})
```
```

#### 任务 1.3: 增强 UnifiedCollection

```python
# 增加存储后端支持
class UnifiedCollection:
    def __init__(
        self,
        name: str,
        storage_backend: str = "memory",
        storage_config: dict | None = None,
        config: dict | None = None
    ):
        # ... 实现如 3.1 所示
```

#### 任务 1.4: 实现 StorageFactory

按照 3.2 节实现存储工厂和各种存储后端。

---

### Phase 2: 测试迁移（Week 2-3）

#### 任务 2.1: 迁移 Collection 单元测试

**步骤**:
1. 创建新测试文件 `tests/unit/neuromem/test_unified_collection_complete.py`
2. 合并所有旧测试用例:
   - `test_vdb_collection.py` → UnifiedCollection + FAISS index
   - `test_graph_collection.py` → UnifiedCollection + Graph index
   - `test_kv_collection.py` → UnifiedCollection + BM25 index
   - `test_hybrid_collection.py` → UnifiedCollection + 多索引

**示例**:
```python
# tests/unit/neuromem/test_unified_collection_complete.py

class TestUnifiedCollectionVectorIndexes:
    """原 VDBMemoryCollection 的测试用例"""

    def test_faiss_index(self):
        collection = UnifiedCollection("test_faiss")
        collection.add_index("vec", "faiss", {"dim": 768})

        # 插入向量数据
        collection.insert("text1", {"vector": [0.1] * 768})

        # 查询
        results = collection.query("vec", query_vector=[0.1] * 768, top_k=5)
        assert len(results) > 0


class TestUnifiedCollectionGraphIndexes:
    """原 GraphMemoryCollection 的测试用例"""

    def test_graph_index(self):
        collection = UnifiedCollection("test_graph")
        collection.add_index("graph", "graph", {})

        # 添加图数据
        collection.insert("node1", {"edges": ["node2"]})

        # 图查询
        results = collection.query("graph", query="node1", depth=2)
        assert len(results) > 0


class TestUnifiedCollectionMultiIndex:
    """原 HybridCollection 的测试用例"""

    def test_multiple_indexes(self):
        collection = UnifiedCollection("test_multi")
        collection.add_index("vec", "faiss", {"dim": 768})
        collection.add_index("bm25", "bm25", {})
        collection.add_index("graph", "graph", {})

        # 插入数据到所有索引
        collection.insert("text1", {"vector": [0.1] * 768})

        # 分别查询
        vec_results = collection.query("vec", [0.1] * 768, top_k=5)
        bm25_results = collection.query("bm25", "text1", top_k=5)

        assert len(vec_results) > 0
        assert len(bm25_results) > 0
```

#### 任务 2.2: 迁移 Service 测试

**步骤**:
1. 确认所有 Service 测试已使用 `UnifiedCollection`（已完成）
2. 移除测试中对旧 Collection 的依赖
3. 验证所有 Service 测试通过

```bash
# 搜索并替换
rg "VDBMemoryCollection|GraphMemoryCollection|KVMemoryCollection|HybridCollection" tests/
```

#### 任务 2.3: 迁移 Paper Features 测试

```python
# tests/test_paper_features.py

# 之前
collection = VDBMemoryCollectionWithFeatures({"name": "test"})

# 之后 - 使用 Mixin 模式
from sage.neuromem.memory_collection.paper_features import (
    TripleStorageMixin,
    LinkEvolutionMixin
)

class EnhancedUnifiedCollection(UnifiedCollection, TripleStorageMixin, LinkEvolutionMixin):
    """增强版 UnifiedCollection（支持 paper features）"""
    pass

collection = EnhancedUnifiedCollection("test")
```

---

### Phase 3: 代码清理（Week 4）

#### 任务 3.1: 删除旧 Collection 文件

```bash
# 删除以下文件
rm sage/neuromem/memory_collection/base_collection.py
rm sage/neuromem/memory_collection/vdb_collection.py
rm sage/neuromem/memory_collection/graph_collection.py
rm sage/neuromem/memory_collection/kv_collection.py
rm sage/neuromem/memory_collection/hybrid_collection.py
rm sage/neuromem/memory_collection/enhanced_collections.py
```

#### 任务 3.2: 更新 __init__.py

```python
# sage/neuromem/memory_collection/__init__.py

"""
Memory Collection Module - 统一数据容器

v0.3.0.0 重大变更:
- 移除 BaseMemoryCollection, VDBMemoryCollection, GraphMemoryCollection 等
- 统一使用 UnifiedCollection
- 支持可插拔的存储后端（Memory/Redis/SageDB）
"""

from .unified_collection import UnifiedCollection

# Paper features (通过 Mixin 实现)
from .paper_features import (
    TripleStorageMixin,
    LinkEvolutionMixin,
    ConflictDetectionMixin,
    # ... 其他 mixins
)

__all__ = [
    "UnifiedCollection",
    "TripleStorageMixin",
    "LinkEvolutionMixin",
    "ConflictDetectionMixin",
]
```

#### 任务 3.3: 删除旧测试文件

```bash
# 删除已迁移的测试
rm tests/components/sage_mem/test_vdb_collection.py
rm tests/components/sage_mem/test_graph_collection.py
rm tests/components/sage_mem/test_kv_collection.py
rm tests/test_hybrid_collection.py
```

---

### Phase 4: 文档和发布（Week 5）

#### 任务 4.1: 更新文档

1. **README.md**: 更新快速开始示例
2. **API_REFERENCE.md**: 移除旧 Collection，突出 UnifiedCollection
3. **CONTRIBUTING.md**: 更新开发指南
4. **CHANGELOG.md**: 添加 Breaking Change 说明

#### 任务 4.2: 更新 Copilot Instructions

```markdown
# sage/.github/copilot-instructions.md

## 架构变更（v0.3.0.0）

### Collection 层

**唯一实现**: `UnifiedCollection`
- 数据只存一份 (通过可插拔 StorageBackend)
- 索引可以有多个 (通过 IndexFactory 创建)
- 支持存储后端: Memory, Redis, SageDB

**已移除**:
- ❌ BaseMemoryCollection
- ❌ VDBMemoryCollection
- ❌ GraphMemoryCollection
- ❌ KVMemoryCollection
- ❌ HybridCollection

### 使用示例

```python
from sage.neuromem import MemoryManager

# 创建 Collection（默认内存存储）
manager = MemoryManager()
collection = manager.create_collection("my_data")

# 自定义存储后端
collection = UnifiedCollection(
    name="my_data",
    storage_backend="redis",
    storage_config={"host": "localhost", "port": 6379}
)

# 动态添加索引
collection.add_index("vec", "faiss", {"dim": 768})
collection.add_index("bm25", "bm25", {})

# 插入数据
collection.insert("hello world", {"vector": [0.1] * 768})

# 查询
results = collection.query("vec", query_vector=[0.1] * 768, top_k=5)
```
```

#### 任务 4.3: 发布版本

```bash
# 1. 更新版本号
# pyproject.toml: version = "0.3.0.0"
# sage/neuromem/_version.py: __version__ = "0.3.0.0"

# 2. Git 提交
git add .
git commit -m "refactor: unify all collections into UnifiedCollection (Breaking Change)"
git tag v0.3.0.0
git push origin main-dev --tags

# 3. 发布到 PyPI
cd /home/zrc/develop_item/bench/neuromem
sage-pypi-publisher build . -o /tmp/neuromem-build -u -r pypi --no-dry-run
```

---

## 五、向后兼容性策略

### 5.1 临时兼容层（可选）

如果需要渐进式迁移，可提供兼容层:

```python
# sage/neuromem/memory_collection/compat.py

import warnings
from .unified_collection import UnifiedCollection

class VDBMemoryCollection(UnifiedCollection):
    """
    [DEPRECATED] 兼容层 - 将在 v0.4.0.0 移除
    """

    def __init__(self, config: dict):
        warnings.warn(
            "VDBMemoryCollection is deprecated. Use UnifiedCollection instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(name=config["name"], config=config)

    def create_index(self, config: dict):
        """旧 API 兼容"""
        return self.add_index(
            name=config["name"],
            index_type=config["backend_type"].lower(),
            config=config
        )

# 同样实现 GraphMemoryCollection, HybridCollection 等
```

### 5.2 迁移工具

```python
# sage/neuromem/utils/migrate.py

def migrate_collection_from_disk(old_path: str, new_path: str):
    """
    迁移旧版本持久化的 Collection 到新格式
    """
    # 1. 加载旧格式
    old_data = load_old_format(old_path)

    # 2. 转换为新格式
    collection = UnifiedCollection(old_data["name"])

    # 迁移数据
    for item in old_data["text_storage"]:
        collection.insert(item["text"], item["metadata"])

    # 迁移索引
    for idx in old_data["indexes"]:
        collection.add_index(idx["name"], idx["type"], idx["config"])

    # 3. 保存新格式
    save_collection(collection, new_path)
```

---

## 六、风险评估与缓解

### 风险 1: 外部用户依赖旧 API

**影响**: 高（Breaking Change）

**缓解措施**:
1. 提供详细的迁移指南
2. 在 v0.2.x 添加 DeprecationWarning
3. 发布 v0.3.0.0 前通知用户（文档/Release Notes）
4. 提供兼容层（可选，见 5.1）

### 风险 2: Paper Features 功能丢失

**影响**: 中

**缓解措施**:
1. 将 Paper Features 重构为 Mixin 模式
2. 创建 `EnhancedUnifiedCollection` 示例
3. 保留所有 Paper Features 测试用例

### 风险 3: 测试覆盖不足

**影响**: 中

**缓解措施**:
1. 合并所有旧测试到 `test_unified_collection_complete.py`
2. 确保测试覆盖率 > 90%
3. 运行完整的 E2E 测试

### 风险 4: 性能回退

**影响**: 低

**缓解措施**:
1. 运行性能基准测试（`tests/performance/test_benchmarks.py`）
2. 对比重构前后性能
3. 如有回退，分析并优化

---

## 七、成功指标

### 代码量减少
- [ ] Collection 层代码从 8,488 行 → < 3,000 行（-65%）
- [ ] 删除 ~6,000 行冗余代码

### 架构清晰
- [ ] 只有 1 个 Collection 类（UnifiedCollection）
- [ ] 存储后端完全可插拔（3+ 个实现）
- [ ] 索引管理完全独立（6+ 个 Index 类型）

### 测试覆盖
- [ ] 所有旧测试迁移到新框架
- [ ] 测试覆盖率保持 > 90%
- [ ] E2E 测试全部通过

### 文档完整
- [ ] 迁移指南完成
- [ ] API 文档更新
- [ ] 示例代码更新

### 用户体验
- [ ] Service 层 API 不变（零修改）
- [ ] MemoryManager API 保持兼容
- [ ] 提供清晰的错误提示

---

## 八、时间线

| 阶段 | 时间 | 关键任务 | 输出 |
|------|------|----------|------|
| Phase 1 | Week 1 | 标记 Deprecated, 增强 UnifiedCollection | DeprecationWarning, StorageFactory |
| Phase 2 | Week 2-3 | 迁移所有测试 | 测试覆盖 > 90% |
| Phase 3 | Week 4 | 删除旧代码, 清理测试 | 代码减少 -65% |
| Phase 4 | Week 5 | 文档更新, 发布 v0.3.0.0 | PyPI 发布 |

**总计**: 5 周

---

## 九、决策检查清单

在开始重构前，确认以下问题：

- [ ] **是否接受 Breaking Change？** v0.3.0.0 将不兼容 v0.2.x
- [ ] **Paper Features 如何处理？** 建议迁移到 Mixin 模式
- [ ] **是否需要兼容层？** 可选，延长迁移期
- [ ] **存储后端优先级？** 先实现 Memory, Redis, SageDB
- [ ] **测试迁移策略？** 合并到 `test_unified_collection_complete.py`
- [ ] **文档更新负责人？** 需指定
- [ ] **发布时间窗口？** 建议预留 5 周

---

## 十、参考资料

- [CODE_REDUNDANCY_ANALYSIS.md](./CODE_REDUNDANCY_ANALYSIS.md) - 冗余分析报告
- [ARCHITECTURE_COMPARISON.txt](./ARCHITECTURE_COMPARISON.txt) - 架构对比图
- [UnifiedCollection 实现](../../sage/neuromem/memory_collection/unified_collection.py)
- [Service 抽象基类](../../sage/neuromem/services/base_service.py)

---

## 附录 A: 快速命令参考

### 搜索旧 Collection 使用

```bash
# 搜索代码中的旧 Collection 引用
rg "VDBMemoryCollection|GraphMemoryCollection|KVMemoryCollection|HybridCollection" \
   --type py \
   -g '!__pycache__' \
   -g '!*.pyc'

# 搜索测试文件
rg "VDBMemoryCollection|GraphMemoryCollection" tests/

# 统计行数
wc -l sage/neuromem/memory_collection/*.py
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 只运行 Collection 测试
pytest tests/unit/neuromem/ -v

# 运行性能基准
pytest tests/performance/test_benchmarks.py -v
```

### 代码检查

```bash
# 类型检查
mypy sage/neuromem/memory_collection/

# 代码格式
ruff check sage/neuromem/memory_collection/
```

---

**文档版本**: v2.0  
**最后更新**: 2026-01-08  
**审核状态**: 待审核
