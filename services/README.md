# MemoryService 层 - 使用指南

**neuromem Services** 提供了基于 UnifiedCollection 的高级记忆服务抽象，通过 Service Registry 模式统一管理不同类型的记忆服务。

---

## 核心概念

### 1. BaseMemoryService

所有记忆服务的抽象基类，定义统一接口：

```python
# 抽象接口定义（实际使用时需要导入具体实现类）
class BaseMemoryService:
    def insert(self, text: str, **kwargs) -> str:
        """插入数据，返回 data_id"""

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> list[dict]:
        """检索数据，返回匹配结果"""

    def delete(self, data_id: str) -> bool:
        """删除数据"""
```

### 2. MemoryServiceRegistry

服务工厂注册表，负责创建和管理服务实例：

```python
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 创建服务
service = MemoryServiceRegistry.create(
    service_type="fifo_queue",
    collection=my_collection,
    config={"max_size": 100}
)

# 列出已注册服务
services = MemoryServiceRegistry.list_registered()
# ['fifo_queue', 'lsh_hash', 'segment', 'linknote_graph', 'property_graph', ...]
```

---

## 已注册的服务

### Partitional Services (简单分区型)

#### 1. FIFOQueueService (`fifo_queue`)

**用途**: 短期对话历史、实时日志、滑动窗口缓存

**特性**:
- 固定容量，先进先出 (FIFO)
- 自动淘汰最老数据
- 按时间顺序返回最近数据

**使用示例**:
```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 创建 Collection
collection = UnifiedCollection("conversation_history")

# 创建 FIFO 服务
service = MemoryServiceRegistry.create(
    "fifo_queue",
    collection,
    config={"max_size": 20}  # 保留最近 20 条
)

# 插入对话
service.insert("User: Hello, how are you?", metadata={"speaker": "user"})
service.insert("Assistant: I'm fine, thanks!", metadata={"speaker": "assistant"})

# 检索最近的对话
recent = service.retrieve(query="", top_k=5)
# [
#   {"id": "...", "text": "Assistant: I'm fine, thanks!", "metadata": {...}, "score": 1.0},
#   {"id": "...", "text": "User: Hello, how are you?", "metadata": {...}, "score": 1.0}
# ]
```

**配置参数**:
- `max_size` (int): 队列最大容量，默认 10

---

#### 2. LSHHashService (`lsh_hash`)

**用途**: 大规模数据去重、快速近似相似度搜索、高维向量检索

**特性**:
- LSH (Locality-Sensitive Hashing) 算法
- O(1) 近似查询，适合海量数据
- 牺牲少量精度换取极高速度

**使用示例**:
```python
collection = UnifiedCollection("document_dedup")

service = MemoryServiceRegistry.create(
    "lsh_hash",
    collection,
    config={
        "embedding_dim": 768,
        "num_tables": 10,
        "hash_size": 8
    }
)

# 插入文档（需要提供 embedding）
import numpy as np
vector = np.random.randn(768).astype(np.float32)
service.insert("Document content", vector=vector)

# 查询相似文档
query_vector = np.random.randn(768).astype(np.float32)
results = service.retrieve(query="", vector=query_vector, top_k=10)
```

**配置参数**:
- `embedding_dim` (int): 向量维度，必填
- `num_tables` (int): LSH 表数量，默认 10
- `hash_size` (int): 哈希位数，默认 8

---

#### 3. SegmentService (`segment`)

**用途**: 长文本分段存储、章节管理、段落检索

**特性**:
- 自动或手动分段
- 保留段落上下文
- 支持段落级检索

**使用示例**:
```python
collection = UnifiedCollection("document_segments")

service = MemoryServiceRegistry.create(
    "segment",
    collection,
    config={
        "max_segment_length": 500,
        "overlap": 50
    }
)

# 插入长文本（自动分段）
long_text = "..." * 1000  # 长文本
service.insert(long_text, metadata={"doc_id": "article_1"})

# 检索相关段落
results = service.retrieve(query="specific topic", top_k=5)
```

**配置参数**:
- `max_segment_length` (int): 最大段落长度，默认 500
- `overlap` (int): 段落重叠字符数，默认 50

---

### Hierarchical Services (层次型)

#### 1. LinknoteGraphService (`linknote_graph`)

**用途**: 双向链笔记、知识图谱、关联记忆

**特性**:
- 双向链接 (Backlinks)
- 图遍历 (BFS/DFS)
- 邻居查询

**使用示例**:
```python
collection = UnifiedCollection("knowledge_notes")

service = MemoryServiceRegistry.create("linknote_graph", collection)

# 插入笔记（带链接）
python_id = service.insert("Python Programming")
oop_id = service.insert("Object-Oriented Programming", links=[python_id])
decorators_id = service.insert("Python Decorators", links=[python_id, oop_id])

# 查询反向链接
backlinks = service.get_backlinks(python_id)
# [oop_id, decorators_id]

# 图遍历
related = service.retrieve(python_id, max_hops=2, method="bfs")
# 返回所有 2 跳内的相关笔记

# 邻居查询
neighbors = service.get_neighbors(oop_id, max_hops=1)
```

**详细文档**: [services/hierarchical/README.md](hierarchical/README.md)

---

#### 2. PropertyGraphService (`property_graph`)

**用途**: 结构化知识图谱、实体关系建模、语义查询

**特性**:
- 类型化实体 (Entity Types)
- 类型化关系 (Relation Types)
- 属性存储 (Properties)
- 语义查询

**使用示例**:
```python
collection = UnifiedCollection("entity_graph")

service = MemoryServiceRegistry.create("property_graph", collection)

# 插入实体
python_id = service.insert(
    "Python",
    entity_type="Language",
    properties={"year": 1991, "paradigm": "multi-paradigm"}
)

guido_id = service.insert(
    "Guido van Rossum",
    entity_type="Person",
    properties={"role": "creator"}
)

# 添加关系
service.add_relation(
    guido_id, python_id,
    relation_type="created",
    properties={"year": 1991}
)

# 查询实体
languages = service.retrieve(
    query="",
    entity_type="Language",
    top_k=10
)

# 查询关系
creators = service.get_related_entities(
    python_id,
    relation_type="created",
    direction="incoming"
)
```

**详细文档**: [services/hierarchical/README.md](hierarchical/README.md)

---

## 最佳实践

### 高级用法

#### 1. 共享 Collection

多个服务可以共享同一个 Collection：

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 共享 Collection
shared_collection = UnifiedCollection("shared_memory")

# 创建多个服务
notes = MemoryServiceRegistry.create("linknote_graph", shared_collection)
entities = MemoryServiceRegistry.create("property_graph", shared_collection)

# 两个服务共享底层数据
note_id = notes.insert("Python is a programming language")
entity_id = entities.insert(
    "Python",
    entity_type="Language",
    properties={"paradigm": "multi-paradigm"}
)

# Collection 包含所有数据
assert shared_collection.size() == 2
```

#### 2. 服务生命周期

```python
# 创建服务
collection = UnifiedCollection("my_data")
service = MemoryServiceRegistry.create(
    "fifo_queue",
    collection,
    config={"max_size": 10}
)

# 使用服务
for i in range(20):
    service.insert(f"Message {i}")

# 删除服务（Collection 数据保留）
del service

# 重新创建服务（数据恢复）
service2 = MemoryServiceRegistry.create(
    "fifo_queue",
    collection,
    config={"max_size": 10}
)

# 数据仍然存在
results = service2.retrieve(query="", top_k=10)
assert len(results) == 10  # FIFO Index 只保留最近 10 条
```

#### 3. 自定义服务

注册自定义服务：

```python
from sage.middleware.components.sage_mem.neuromem.services import (
    BaseMemoryService,
    MemoryServiceRegistry
)

@MemoryServiceRegistry.register("my_custom_service")
class MyCustomService(BaseMemoryService):
    def _setup_indexes(self):
        # 设置需要的索引
        self.collection.add_index("my_index", "faiss", {"dim": 768})

    def insert(self, text: str, **kwargs) -> str:
        # 自定义插入逻辑
        vector = kwargs.get("vector")
        data_id = self.collection.insert(text, metadata=kwargs.get("metadata"))
        if vector is not None:
            self.collection.insert_to_index(data_id, "my_index")
        return data_id

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> list[dict]:
        # 自定义检索逻辑
        vector = kwargs.get("vector")
        if vector is not None:
            data_ids = self.collection.query_by_index(
                "my_index", vector, top_k=top_k
            )
            return [self.collection.get(id_) for id_ in data_ids]
        return []

# 使用自定义服务
service = MemoryServiceRegistry.create("my_custom_service", collection)
```

---

## 性能考虑

### 1. FIFO Queue

- **插入吞吐量**: > 1000 ops/s
- **检索吞吐量**: > 100 queries/s
- **内存占用**: 约 50MB (10K 数据)
- **适用场景**: 对话历史 (< 1000 条)

### 2. LSH Hash

- **插入吞吐量**: > 500 ops/s
- **检索吞吐量**: > 50 queries/s (近似)
- **内存占用**: 约 200MB (100K 向量, 768维)
- **适用场景**: 大规模去重 (> 100K 文档)

### 3. Property Graph

- **插入吞吐量**: > 200 ops/s
- **遍历性能**: 1-2 跳 < 100ms
- **内存占用**: 约 100MB (1K 实体, 2K 关系)
- **适用场景**: 知识图谱 (< 10K 实体)

**详细基准**: [BENCHMARKS.md](BENCHMARKS.md)

---

## 测试

### E2E 测试

```bash
# 运行所有 E2E 测试
pytest packages/sage-middleware/tests/e2e/ -v

# 运行特定工作流测试
pytest packages/sage-middleware/tests/e2e/test_complete_workflows.py::TestFIFOQueueWorkflow -v
```

### 性能测试

```bash
# 运行性能基准测试
pytest packages/sage-middleware/tests/performance/ -v

# 运行特定性能测试
pytest packages/sage-middleware/tests/performance/test_benchmarks.py::TestInsertionPerformance -v
```

---

## 故障排查

### 问题 1: Service 未注册

**症状**:
```
ValueError: Service type 'my_service' not registered
```

**原因**: 服务类未导入，装饰器未执行

**解决**:
```python
# 确保导入服务类
from sage.middleware.components.sage_mem.neuromem.services.partitional import (
    FIFOQueueService  # 触发装饰器
)

# 检查已注册服务
print(MemoryServiceRegistry.list_registered())
```

### 问题 2: 参数错误

**症状**:
```
TypeError: create() got an unexpected keyword argument 'maxlen'
```

**原因**: 使用了错误的参数名

**解决**:
```python
# ❌ 错误
service = MemoryServiceRegistry.create("fifo_queue", collection, maxlen=10)

# ✅ 正确
service = MemoryServiceRegistry.create(
    "fifo_queue", collection, config={"max_size": 10}
)
```

### 问题 3: Collection vs Index 大小

**症状**: Collection 大小与预期不符

**原因**: Collection 保留所有数据，Index 根据配置限制大小

**说明**:
```python
service = MemoryServiceRegistry.create(
    "fifo_queue", collection, config={"max_size": 5}
)

# 插入 10 条数据
for i in range(10):
    service.insert(f"Message {i}")

# Collection 保留所有 10 条
assert collection.size() == 10

# FIFO Index 只保留最近 5 条
results = service.retrieve(query="", top_k=10)
assert len(results) == 5
```

---

## 参考资料

- **Hierarchical Services**: [hierarchical/README.md](hierarchical/README.md)
- **快速开始**: [hierarchical/QUICKSTART.md](hierarchical/QUICKSTART.md)
- **性能基准**: [BENCHMARKS.md](BENCHMARKS.md)
- **Partitional Services**: [partitional/README.md](partitional/README.md)
- **API 参考**: [API_REFERENCE.md](API_REFERENCE.md)

---

**最后更新**: 2025-01-26  
**版本**: v1.0.0 (T4.4a)
