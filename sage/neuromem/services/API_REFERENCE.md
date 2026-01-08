# Memory Services API 参考

完整的 API 签名、参数说明和返回值文档。

> **注意**: 本文档专注于 Memory Services API。关于 CollectionConfig 和 YAML 配置的详细信息，请参阅 [CollectionConfig 使用指南](../../../docs/COLLECTION_CONFIG_GUIDE.md)。

---

## 目录

1. [配置管理](#配置管理)
2. [基类 API](#基类-api)
3. [Service Registry API](#service-registry-api)
4. [Partitional Services API](#partitional-services-api)
5. [Hierarchical Services API](#hierarchical-services-api)
6. [异常处理](#异常处理)

---

## 配置管理

NeuroMem 使用 `CollectionConfig` 类统一管理集合配置。详细信息请参阅：

- **[CollectionConfig 使用指南](../../../docs/COLLECTION_CONFIG_GUIDE.md)** - 完整的配置文档
  - 从代码、字典、YAML 创建配置
  - 索引配置详解
  - 存储后端选择
  - 迁移指南和最佳实践

**快速示例**:

```python
from sage.neuromem.config import CollectionConfig

# 从 YAML 创建配置
config = CollectionConfig.from_yaml("config/my_collection.yaml")
collection = config.create_collection()

# 或者从代码创建
config = CollectionConfig(
    name="my_collection",
    indexes=[{"name": "main", "type": "faiss", "config": {"dim": 768}}]
)
collection = config.create_collection()
```

---

## 基类 API

### BaseMemoryService

所有 Memory Service 的抽象基类。

#### 构造函数

```python
BaseMemoryService(collection: UnifiedCollection, config: dict | None = None)
```

**参数**:
- `collection` (UnifiedCollection): 底层存储集合
- `config` (dict, optional): 服务配置字典

**示例**:
```python
service = ConcreteService(collection, config={"max_size": 100})
```

#### 核心方法

##### `insert(text: str, **kwargs) -> str`

插入数据到服务。

**参数**:
- `text` (str): 文本内容
- `vector` (np.ndarray, optional): 向量表示（某些服务需要）
- `metadata` (dict, optional): 元数据字典
- `**kwargs`: 服务特定参数

**返回**:
- `str`: 数据 ID

**异常**:
- `ValueError`: 参数验证失败
- `RuntimeError`: 插入操作失败

**示例**:
```python
data_id = service.insert(
    "Hello, world!",
    metadata={"source": "user"},
    vector=np.array([0.1, 0.2, 0.3])
)
```

##### `retrieve(query: str, top_k: int = 5, **kwargs) -> list[dict]`

检索相关数据。

**参数**:
- `query` (str): 查询文本
- `top_k` (int): 返回结果数量（默认 5）
- `vector` (np.ndarray, optional): 查询向量
- `filters` (dict, optional): 元数据过滤条件
- `**kwargs`: 服务特定参数

**返回**:
- `list[dict]`: 结果列表，每个元素包含:
  - `id` (str): 数据 ID
  - `text` (str): 文本内容
  - `metadata` (dict): 元数据
  - `score` (float): 相似度/相关性分数

**异常**:
- `ValueError`: 参数验证失败
- `RuntimeError`: 检索操作失败

**示例**:
```python
results = service.retrieve(
    query="hello",
    top_k=10,
    filters={"source": "user"}
)

for result in results:
    print(f"[{result['score']:.2f}] {result['text']}")
```

##### `delete(data_id: str) -> bool`

删除指定数据。

**参数**:
- `data_id` (str): 数据 ID

**返回**:
- `bool`: 是否成功删除

**异常**:
- `ValueError`: data_id 为空或格式错误
- `KeyError`: 数据不存在

**示例**:
```python
success = service.delete("data_001")
if success:
    print("删除成功")
```

##### `setup() -> None`

初始化服务（如加载索引、预热缓存）。

**返回**: None

**异常**:
- `RuntimeError`: 初始化失败

**示例**:
```python
service.setup()  # 服务就绪
```

##### `teardown() -> None`

清理服务资源（如保存索引、释放内存）。

**返回**: None

**示例**:
```python
service.teardown()  # 释放资源
```

---

## Service Registry API

### MemoryServiceRegistry

服务注册和创建工厂。

#### 类方法

##### `register(service_type: str) -> Callable`

注册服务类的装饰器。

**参数**:
- `service_type` (str): 服务类型标识符

**返回**:
- `Callable`: 装饰器函数

**示例**:
```python
@MemoryServiceRegistry.register("my_service")
class MyService(BaseMemoryService):
    ...
```

##### `create(service_type: str, collection: UnifiedCollection, config: dict | None = None, **kwargs) -> BaseMemoryService`

创建服务实例。

**参数**:
- `service_type` (str): 服务类型（如 "fifo_queue"）
- `collection` (UnifiedCollection): 底层集合
- `config` (dict, optional): 配置字典
- `**kwargs`: 额外参数

**返回**:
- `BaseMemoryService`: 服务实例

**异常**:
- `ValueError`: 未知的 service_type

**示例**:
```python
service = MemoryServiceRegistry.create(
    "fifo_queue",
    collection,
    config={"max_size": 100}
)
```

##### `list_services() -> list[str]`

列出所有已注册的服务类型。

**返回**:
- `list[str]`: 服务类型列表

**示例**:
```python
services = MemoryServiceRegistry.list_services()
print(services)  # ["fifo_queue", "lsh_hash", "segment", ...]
```

---

## Partitional Services API

### FIFOQueueService

FIFO 队列服务。

#### 构造函数

```python
FIFOQueueService(collection: UnifiedCollection, config: dict | None = None)
```

**配置参数**:
```python
config = {
    "max_size": 10  # 队列最大容量（必填）
}
```

#### 特有方法

##### `get_recent(limit: int = 10) -> list[dict]`

获取最近 N 条数据（便捷方法）。

**参数**:
- `limit` (int): 返回数量（默认 10）

**返回**:
- `list[dict]`: 结果列表

**示例**:
```python
recent = service.get_recent(limit=5)
```

---

### LSHHashService

LSH 哈希索引服务。

#### 构造函数

```python
LSHHashService(collection: UnifiedCollection, config: dict | None = None)
```

**配置参数**:
```python
config = {
    "embedding_dim": 768,   # 向量维度（必填）
    "num_tables": 10,       # LSH 表数量（默认 10）
    "hash_size": 8          # 哈希位数（默认 8）
}
```

#### 方法重载

##### `insert(text: str, vector: np.ndarray, **kwargs) -> str`

插入文档和向量。

**参数**:
- `text` (str): 文本内容
- `vector` (np.ndarray): **归一化后的向量**（必填，float32）
- `metadata` (dict, optional): 元数据

**返回**:
- `str`: 数据 ID

**注意**: 向量必须归一化！

**示例**:
```python
vector = np.random.randn(768).astype(np.float32)
vector = vector / (np.linalg.norm(vector) + 1e-10)  # 归一化

data_id = service.insert("Document", vector=vector)
```

##### `retrieve(query: str, vector: np.ndarray, top_k: int = 5, **kwargs) -> list[dict]`

查询相似向量。

**参数**:
- `query` (str): 查询文本（可选）
- `vector` (np.ndarray): **查询向量**（必填）
- `top_k` (int): 返回数量

**返回**:
- `list[dict]`: 结果列表

**示例**:
```python
query_vector = np.random.randn(768).astype(np.float32)
query_vector = query_vector / (np.linalg.norm(query_vector) + 1e-10)

results = service.retrieve(query="", vector=query_vector, top_k=10)
```

---

### SegmentService

文本分段服务。

#### 构造函数

```python
SegmentService(collection: UnifiedCollection, config: dict | None = None)
```

**配置参数**:
```python
config = {
    "max_segment_length": 500,  # 最大段落长度（默认 500）
    "overlap": 50               # 段落重叠字符数（默认 50）
}
```

#### 方法说明

##### `insert(text: str, **kwargs) -> str`

插入文本（自动分段）。

**参数**:
- `text` (str): 文本内容（会自动分段）
- `metadata` (dict, optional): 元数据（继承到每个段落）

**返回**:
- `str`: 主文档 ID

**自动分段逻辑**:
1. 按 `max_segment_length` 切分文本
2. 相邻段落保留 `overlap` 字符重叠
3. 每个段落添加 `segment_id` 元数据

**示例**:
```python
long_text = "..." * 10000  # 长文本
doc_id = service.insert(long_text, metadata={"doc_id": "article_001"})
```

##### `retrieve(query: str, top_k: int = 5, **kwargs) -> list[dict]`

检索相关段落。

**参数**:
- `query` (str): 查询文本
- `top_k` (int): 返回段落数量

**返回**:
- `list[dict]`: 段落结果列表，每个段落包含:
  - `id` (str): 段落 ID
  - `text` (str): 段落文本
  - `metadata` (dict): 包含 `segment_id` 字段
  - `score` (float): 相关性分数

**示例**:
```python
results = service.retrieve(query="深度学习", top_k=5)
for result in results:
    print(f"段落 {result['metadata']['segment_id']}: {result['text'][:100]}")
```

---

## Hierarchical Services API

### LinknoteGraphService (`linknote_graph`)

双向链接笔记图服务。

#### 构造函数

```python
LinknoteGraphService(collection: UnifiedCollection, config: dict | None = None)
```

**配置参数**:
```python
config = {
    "bidirectional": True  # 是否双向链接（默认 True）
}
```

#### 特有方法

##### `add_link(from_id: str, to_id: str, link_type: str = "default") -> bool`

添加链接关系。

**参数**:
- `from_id` (str): 源节点 ID
- `to_id` (str): 目标节点 ID
- `link_type` (str): 链接类型（默认 "default"）

**返回**:
- `bool`: 是否成功

**示例**:
```python
service.add_link("note_001", "note_002", link_type="reference")
```

##### `get_linked(node_id: str, direction: str = "both") -> list[dict]`

获取链接的节点。

**参数**:
- `node_id` (str): 节点 ID
- `direction` (str): 方向 ("in" | "out" | "both")

**返回**:
- `list[dict]`: 链接节点列表

**示例**:
```python
linked = service.get_linked("note_001", direction="out")
```

##### `traverse(start_id: str, max_depth: int = 2) -> dict`

遍历链接图。

**参数**:
- `start_id` (str): 起始节点 ID
- `max_depth` (int): 最大遍历深度（默认 2）

**返回**:
- `dict`: 遍历结果树

**示例**:
```python
tree = service.traverse("note_001", max_depth=3)
```

---

### PropertyGraphService (`property_graph`)

属性图服务。

#### 构造函数

```python
PropertyGraphService(collection: UnifiedCollection, config: dict | None = None)
```

**配置参数**:
```python
config = {
    "enable_validation": True  # 是否启用属性验证（默认 True）
}
```

#### 特有方法

##### `add_node(node_id: str, properties: dict) -> bool`

添加节点。

**参数**:
- `node_id` (str): 节点 ID
- `properties` (dict): 节点属性字典

**返回**:
- `bool`: 是否成功

**示例**:
```python
service.add_node("person_001", {"name": "Alice", "age": 30})
```

##### `add_edge(from_id: str, to_id: str, relation: str, properties: dict | None = None) -> bool`

添加边。

**参数**:
- `from_id` (str): 源节点 ID
- `to_id` (str): 目标节点 ID
- `relation` (str): 关系类型
- `properties` (dict, optional): 边属性

**返回**:
- `bool`: 是否成功

**示例**:
```python
service.add_edge("person_001", "person_002", "FRIEND", {"since": 2020})
```

##### `query_subgraph(node_id: str, max_hops: int = 1) -> dict`

查询子图。

**参数**:
- `node_id` (str): 中心节点 ID
- `max_hops` (int): 最大跳数（默认 1）

**返回**:
- `dict`: 子图结构 `{"nodes": [...], "edges": [...]}`

**示例**:
```python
subgraph = service.query_subgraph("person_001", max_hops=2)
print(f"节点数: {len(subgraph['nodes'])}")
print(f"边数: {len(subgraph['edges'])}")
```

##### `find_paths(from_id: str, to_id: str, max_depth: int = 3) -> list[list[str]]`

查找路径。

**参数**:
- `from_id` (str): 起始节点 ID
- `to_id` (str): 目标节点 ID
- `max_depth` (int): 最大深度（默认 3）

**返回**:
- `list[list[str]]`: 路径列表，每个路径是节点 ID 列表

**示例**:
```python
paths = service.find_paths("person_001", "person_003", max_depth=3)
for path in paths:
    print(" -> ".join(path))
```

---

## 异常处理

### 常见异常

#### `ValueError`

参数验证失败。

**常见情况**:
- 服务类型未注册
- 必填参数缺失
- 参数类型错误

**示例**:
```python
try:
    service = MemoryServiceRegistry.create("invalid_type", collection)
except ValueError as e:
    print(f"错误: {e}")
```

#### `RuntimeError`

运行时操作失败。

**常见情况**:
- 索引构建失败
- 数据插入失败
- 检索超时

**示例**:
```python
try:
    service.insert("data")
except RuntimeError as e:
    print(f"插入失败: {e}")
```

#### `KeyError`

数据不存在。

**常见情况**:
- 删除不存在的数据
- 查询不存在的节点

**示例**:
```python
try:
    service.delete("nonexistent_id")
except KeyError as e:
    print(f"数据不存在: {e}")
```

---

## 类型定义

### 通用类型

```python
from typing import TypedDict

class RetrievalResult(TypedDict):
    id: str              # 数据 ID
    text: str            # 文本内容
    metadata: dict       # 元数据
    score: float         # 相似度/相关性分数

class GraphNode(TypedDict):
    id: str              # 节点 ID
    properties: dict     # 节点属性

class GraphEdge(TypedDict):
    from_id: str         # 源节点 ID
    to_id: str           # 目标节点 ID
    relation: str        # 关系类型
    properties: dict     # 边属性
```

---

## 最佳实践

### 1. 错误处理

```python
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

try:
    service = MemoryServiceRegistry.create(
        "fifo_queue",
        collection,
        config={"max_size": 100}
    )
    service.setup()

    data_id = service.insert("data", metadata={"key": "value"})
    results = service.retrieve(query="query", top_k=5)

except ValueError as e:
    print(f"配置错误: {e}")
except RuntimeError as e:
    print(f"运行时错误: {e}")
finally:
    service.teardown()
```

### 2. 生命周期管理

```python
# 推荐：使用上下文管理器（如果实现了 __enter__/__exit__）
with MemoryServiceRegistry.create("fifo_queue", collection) as service:
    service.insert("data")
    results = service.retrieve(query="", top_k=5)
# 自动调用 teardown()
```

### 3. 向量归一化

```python
import numpy as np

# 正确：归一化向量
vector = np.random.randn(768).astype(np.float32)
vector = vector / (np.linalg.norm(vector) + 1e-10)  # 避免除零

service.insert("text", vector=vector)

# 错误：未归一化
# service.insert("text", vector=np.random.randn(768))  # 可能导致精度问题
```

---

## 参考资料

- **使用指南**: [README.md](README.md)
- **性能基准**: [BENCHMARKS.md](BENCHMARKS.md)
- **Partitional Services**: [partitional/README.md](partitional/README.md)
- **Hierarchical Services**: [hierarchical/README.md](hierarchical/README.md)

---

**最后更新**: 2025-01-26  
**版本**: v1.0.0 (T4.4a)
