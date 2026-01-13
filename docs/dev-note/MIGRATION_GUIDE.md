# Collection 迁移指南 (v0.2.x → v0.3.0.0)

> **版本**: v0.3.0.0  
> **迁移类型**: Breaking Change  
> **迁移时间**: 预计 1 小时

---

## 概述

v0.3.0.0 将所有 Collection 类统一为唯一的 `UnifiedCollection`，旧的 Collection 类已被移除。

### 删除的类

- ❌ `BaseMemoryCollection` → 使用 `UnifiedCollection`
- ❌ `VDBMemoryCollection` → 使用 `UnifiedCollection` + FAISS index
- ❌ `GraphMemoryCollection` → 使用 `UnifiedCollection` + Graph index
- ❌ `KVMemoryCollection` → 使用 `UnifiedCollection` + BM25 index
- ❌ `HybridCollection` → 使用 `UnifiedCollection` + 多索引
- ❌ `VDBMemoryCollectionWithFeatures` → 使用 `UnifiedCollection` + Mixin
- ❌ `GraphMemoryCollectionWithFeatures` → 使用 `UnifiedCollection` + Mixin
- ❌ `HybridCollectionWithFeatures` → 使用 `UnifiedCollection` + Mixin

### 新功能

- ✅ **可插拔存储后端**: Memory/Redis/SageDB
- ✅ **动态索引管理**: 运行时添加/删除索引
- ✅ **统一API**: 所有操作通过 `UnifiedCollection`
- ✅ **Mixin 模式**: Paper Features 通过继承组合

---

## 迁移映射

### 1. VDBMemoryCollection → UnifiedCollection

#### 之前 (v0.2.x)

```python
from sage.neuromem.memory_collection import VDBMemoryCollection

# 创建 VDB Collection
collection = VDBMemoryCollection({"name": "my_vdb"})

# 创建索引
collection.create_index({
    "name": "vector_index",
    "backend_type": "FAISS",
    "dim": 768,
    "description": "My vector index"
})

# 插入数据
data_id = collection.insert_with_embedding(
    content="Hello world",
    embedding_vector=[0.1] * 768,
    index_name="vector_index",
    metadata={"source": "test"}
)

# 检索
results = collection.retrieve(
    query_vector=[0.1] * 768,
    index_name="vector_index",
    top_k=5
)
```

#### 之后 (v0.3.0.0)

```python
from sage.neuromem.memory_collection import UnifiedCollection

# 创建 Collection（默认内存存储）
collection = UnifiedCollection("my_vdb")

# 添加 FAISS 索引
collection.add_index("vector_index", "faiss", {"dim": 768})

# 插入数据（向量在 metadata 中）
data_id = collection.insert(
    text="Hello world",
    metadata={"source": "test", "vector": [0.1] * 768}
)

# 检索
results = collection.query(
    index_name="vector_index",
    query=[0.1] * 768,
    top_k=5
)
```

---

### 2. GraphMemoryCollection → UnifiedCollection

#### 之前 (v0.2.x)

```python
from sage.neuromem.memory_collection import GraphMemoryCollection

collection = GraphMemoryCollection({"name": "my_graph"})

# 创建图索引
collection.create_index({"name": "graph_index"})

# 添加节点和边
collection.insert(
    content="Node1",
    metadata={"edges": ["Node2", "Node3"]},
    index_name="graph_index"
)

# 图查询
results = collection.retrieve_by_graph(
    start_node_id=node_id,
    depth=2,
    index_name="graph_index"
)
```

#### 之后 (v0.3.0.0)

```python
from sage.neuromem.memory_collection import UnifiedCollection

collection = UnifiedCollection("my_graph")

# 添加图索引
collection.add_index("graph_index", "graph", {})

# 添加节点（边信息在 metadata 中）
data_id = collection.insert(
    text="Node1",
    metadata={"edges": ["Node2", "Node3"]}
)

# 图查询
results = collection.query(
    index_name="graph_index",
    query={"start_id": data_id, "depth": 2}
)
```

---

### 3. KVMemoryCollection → UnifiedCollection

#### 之前 (v0.2.x)

```python
from sage.neuromem.memory_collection import KVMemoryCollection

collection = KVMemoryCollection({"name": "my_kv"})

# 创建 BM25 索引
collection.create_index({
    "name": "bm25_index",
    "backend_type": "BM25"
})

# 插入文本
collection.insert(
    content="This is a document",
    index_name="bm25_index",
    metadata={"source": "test"}
)

# 文本检索
results = collection.retrieve(
    query="document",
    index_name="bm25_index",
    top_k=5
)
```

#### 之后 (v0.3.0.0)

```python
from sage.neuromem.memory_collection import UnifiedCollection

collection = UnifiedCollection("my_kv")

# 添加 BM25 索引
collection.add_index("bm25_index", "bm25", {})

# 插入文本
data_id = collection.insert(
    text="This is a document",
    metadata={"source": "test"}
)

# 文本检索
results = collection.query(
    index_name="bm25_index",
    query="document",
    top_k=5
)
```

---

### 4. HybridCollection → UnifiedCollection

#### 之前 (v0.2.x)

```python
from sage.neuromem.memory_collection import HybridCollection

collection = HybridCollection({"name": "hybrid"})

# 创建多个索引
collection.create_index({
    "name": "vec",
    "backend_type": "FAISS",
    "dim": 768
}, index_type=IndexType.VDB)

collection.create_index({
    "name": "bm25",
    "backend_type": "BM25"
}, index_type=IndexType.KV)

# 插入数据（自动加入所有索引）
collection.insert(
    content="Hello",
    vector=[0.1] * 768,
    index_names=["vec", "bm25"]
)

# 多索引检索 + RRF 融合
results = collection.retrieve_multi(
    queries=[
        ("vec", [0.1] * 768),
        ("bm25", "Hello")
    ],
    fusion_strategy="rrf",
    top_k=10
)
```

#### 之后 (v0.3.0.0)

```python
from sage.neuromem.memory_collection import UnifiedCollection

collection = UnifiedCollection("hybrid")

# 添加多个索引
collection.add_index("vec", "faiss", {"dim": 768})
collection.add_index("bm25", "bm25", {})

# 插入数据（自动加入所有索引）
data_id = collection.insert(
    text="Hello",
    metadata={"vector": [0.1] * 768},
    index_names=["vec", "bm25"]  # 可选，None 表示所有索引
)

# 多索引检索（RRF 融合由 Service 层处理）
vec_results = collection.query("vec", [0.1] * 768, top_k=10)
bm25_results = collection.query("bm25", "Hello", top_k=10)

# 使用 Service 层的 RRF 融合（推荐）
from sage.neuromem.services import MemoryServiceRegistry

service = MemoryServiceRegistry.create(
    "hybrid_retrieval",
    collection=collection,
    config={"fusion_strategy": "rrf"}
)
results = service.retrieve_multi([
    ("vec", [0.1] * 768),
    ("bm25", "Hello")
], top_k=10)
```

---

### 5. Enhanced Collections with Paper Features

#### 之前 (v0.2.x)

```python
from sage.neuromem.memory_collection import (
    VDBMemoryCollectionWithFeatures,
    GraphMemoryCollectionWithFeatures
)

# VDB with features
vdb_collection = VDBMemoryCollectionWithFeatures({"name": "vdb"})
vdb_collection.create_index({"name": "vec", "dim": 768, "backend_type": "FAISS"})

# 冲突检测
result = vdb_collection.insert_with_conflict_check(
    content="John is 25",
    vector=[0.1] * 768,
    index_name="vec",
    resolution="replace"
)

# Token 预算过滤
results = vdb_collection.retrieve_with_budget(
    query=[0.1] * 768,
    index_name="vec",
    token_budget=2000
)

# Graph with features
graph_collection = GraphMemoryCollectionWithFeatures({"name": "graph"})
graph_collection.create_index({"name": "g"})

# A-Mem: 结构化笔记
note_id = graph_collection.insert_note(
    content="Alice is a developer",
    keywords=["Alice", "developer"],
    tags=["person", "job"],
    context="User profile"
)
```

#### 之后 (v0.3.0.0)

```python
from sage.neuromem.memory_collection import UnifiedCollection
from sage.neuromem.memory_collection.paper_features import (
    PaperFeaturesMixin,
    GraphPaperFeaturesMixin
)

# 创建增强版 Collection (Mixin 模式)
class EnhancedVDBCollection(UnifiedCollection, PaperFeaturesMixin):
    pass

class EnhancedGraphCollection(UnifiedCollection, GraphPaperFeaturesMixin):
    pass

# VDB with features
vdb_collection = EnhancedVDBCollection("vdb")
vdb_collection.add_index("vec", "faiss", {"dim": 768})

# 冲突检测（Mixin 提供）
result = vdb_collection.insert_with_conflict_check(
    content="John is 25",
    vector=[0.1] * 768,
    index_name="vec",
    resolution="replace"
)

# Token 预算过滤
results = vdb_collection.retrieve_with_budget(
    query=[0.1] * 768,
    index_name="vec",
    token_budget=2000
)

# Graph with features
graph_collection = EnhancedGraphCollection("graph")
graph_collection.add_index("g", "graph", {})

# A-Mem: 结构化笔记（Mixin 提供）
note_id = graph_collection.insert_note(
    content="Alice is a developer",
    keywords=["Alice", "developer"],
    tags=["person", "job"],
    context="User profile"
)
```

---

## 新功能：可插拔存储后端

v0.3.0.0 引入了可插拔的存储后端，支持多种持久化方式。

### 内存存储（默认）

```python
collection = UnifiedCollection(
    "my_data",
    storage_backend="memory"
)
```

### Redis 存储

```python
collection = UnifiedCollection(
    "my_data",
    storage_backend="redis",
    storage_config={
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "prefix": "neuromem:"
    }
)
```

### SageDB 向量数据库

```python
collection = UnifiedCollection(
    "my_data",
    storage_backend="sagedb",
    storage_config={
        "db_path": "./sagedb_data",
        "dim": 768
    }
)
```

### 自定义存储后端

```python
from sage.neuromem.storage_engine import StorageBackend, StorageFactory

class MyCustomStorage(StorageBackend):
    def put(self, key, data):
        # 自定义存储逻辑
        pass

    def get(self, key):
        # 自定义获取逻辑
        pass

    # ... 实现其他方法

# 注册自定义后端
StorageFactory.register("mycustom", MyCustomStorage)

# 使用自定义后端
collection = UnifiedCollection(
    "my_data",
    storage_backend="mycustom",
    storage_config={"option": "value"}
)
```

---

## API 变更对照表

| 旧 API | 新 API | 说明 |
|--------|--------|------|
| `VDBMemoryCollection(config)` | `UnifiedCollection(name, storage_backend, ...)` | 统一构造函数 |
| `collection.create_index(config, index_type)` | `collection.add_index(name, index_type, config)` | 简化参数顺序 |
| `collection.insert_with_embedding(content, vector, ...)` | `collection.insert(text, metadata={"vector": ...})` | 统一 insert 接口 |
| `collection.retrieve(query, index_name, ...)` | `collection.query(index_name, query, ...)` | 统一查询接口 |
| `collection.retrieve_multi(queries, fusion)` | Service 层处理 | 多索引融合移至 Service |
| `collection.insert_to_index(id, index)` | `collection.insert_to_index(id, index)` | 保持不变 ✅ |
| `collection.remove_from_index(id, index)` | `collection.remove_from_index(id, index)` | 保持不变 ✅ |

---

## 常见问题

### Q1: 为什么要统一为 UnifiedCollection？

**A**: 之前有 6 个冗余的 Collection 类（BaseMemoryCollection, VDBMemoryCollection 等），代码重复率超过 80%。统一后：
- 代码减少 6,000 行（-70%）
- 维护成本降低 80%
- API 更清晰一致

### Q2: 旧代码会立即失效吗？

**A**: 不会。v0.2.x 版本已添加 DeprecationWarning，你可以逐步迁移。但 v0.3.0.0 将完全移除旧类。

### Q3: Service 层代码需要修改吗？

**A**: **不需要**！所有 Service 已使用 `UnifiedCollection`，无需修改。

### Q4: 如何迁移现有数据？

**A**:
1. **测试环境**: 修改代码并测试
2. **生产环境**: 使用新代码重新插入数据，或通过持久化文件迁移

### Q5: Paper Features 还支持吗？

**A**: **完全支持**！通过 Mixin 模式继承：
```python
class MyCollection(UnifiedCollection, TripleStorageMixin):
    pass
```

### Q6: 多索引融合（RRF）还支持吗？

**A**: 支持，但移至 Service 层处理。Collection 只负责单索引查询，融合逻辑由 Service 处理（更合理的分层）。

### Q7: 如何选择存储后端？

**A**:
- **开发测试**: 使用 `memory`（默认）
- **分布式/持久化**: 使用 `redis`
- **大规模向量**: 使用 `sagedb`

### Q8: 索引名称有规范吗？

**A**: 建议使用语义化命名：
- `vector_faiss` 或 `vec` - 向量索引
- `bm25_text` 或 `bm25` - 文本索引
- `graph_main` 或 `graph` - 图索引
- `fifo_recent` 或 `fifo` - FIFO 队列

---

## 检查清单

迁移完成后，确保：

- [ ] 所有 `VDBMemoryCollection` 替换为 `UnifiedCollection`
- [ ] 所有 `GraphMemoryCollection` 替换为 `UnifiedCollection`
- [ ] 所有 `KVMemoryCollection` 替换为 `UnifiedCollection`
- [ ] 所有 `HybridCollection` 替换为 `UnifiedCollection`
- [ ] 更新 `create_index()` 为 `add_index()`
- [ ] 更新 `retrieve()` 为 `query()`
- [ ] 多索引融合移至 Service 层
- [ ] 测试所有功能正常
- [ ] 更新文档和示例

---

## 获取帮助

- 📖 完整方案: `docs/dev-note/REFACTOR_PLAN_V2.md`
- 📋 实施指南: `docs/dev-note/IMPLEMENTATION_BRIEF.md`
- 🔍 架构对比: `docs/dev-note/ARCHITECTURE_COMPARISON.txt`
- 💬 问题反馈: GitHub Issues

---

**最后更新**: 2026-01-08
