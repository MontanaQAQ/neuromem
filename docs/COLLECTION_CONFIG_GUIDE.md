# CollectionConfig 使用指南

CollectionConfig 是 UnifiedCollection 的统一配置类，支持从代码、字典和 YAML 文件创建集合配置。

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [从代码创建](#从代码创建)
4. [从字典创建](#从字典创建)
5. [从 YAML 创建](#从-yaml-创建)
6. [索引配置](#索引配置)
7. [存储配置](#存储配置)
8. [迁移指南](#迁移指南)
9. [完整示例](#完整示例)

---

## 快速开始

### 最简单的用法

```python
from sage.neuromem.config import CollectionConfig

# 创建配置
config = CollectionConfig(name="my_collection")

# 使用配置创建集合
collection = config.create_collection()

# 插入数据
collection.insert("data1", {"text": "Hello, world!"})

# 检索数据
results = collection.retrieve(query="hello", top_k=5)
```

### 从 YAML 文件创建

```python
from sage.neuromem.config import CollectionConfig

# 加载 YAML 配置
config = CollectionConfig.from_yaml("path/to/config.yaml")

# 创建集合
collection = config.create_collection()
```

---

## 核心概念

### CollectionConfig 类

统一的集合配置类，包含以下属性：

- **name** (str): Collection 名称
- **storage_backend** (str): 存储后端类型（`"memory"`, `"redis"`, `"sagedb"`）
- **storage_config** (dict): 存储后端配置
- **indexes** (list[IndexConfig]): 索引配置列表
- **metadata** (dict): 额外的元数据

### IndexConfig 类

索引配置数据类：

- **name** (str): 索引名称
- **index_type** (str): 索引类型（`"faiss"`, `"bm25"`, `"graph"` 等）
- **config** (dict): 索引特定配置

---

## 从代码创建

### 基础配置

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

config = CollectionConfig(
    name="basic_collection",
    storage_backend="memory",
)

collection = config.create_collection()
```

### 带索引的配置

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

config = CollectionConfig(
    name="vector_collection",
    storage_backend="memory",
    indexes=[
        IndexConfig(
            name="primary_index",
            index_type="faiss",
            config={"dim": 768, "metric": "cosine"}
        )
    ]
)

collection = config.create_collection()
```

### 多索引配置

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

config = CollectionConfig(
    name="hybrid_collection",
    indexes=[
        IndexConfig(
            name="semantic_index",
            index_type="faiss",
            config={"dim": 1536, "metric": "cosine"}
        ),
        IndexConfig(
            name="keyword_index",
            index_type="bm25",
            config={"k1": 1.5, "b": 0.75}
        )
    ]
)

collection = config.create_collection()
```

---

## 从字典创建

### 基本格式

```python
from sage.neuromem.config import CollectionConfig

data = {
    "name": "my_collection",
    "storage_backend": "memory",
    "indexes": [
        {
            "name": "main_index",
            "type": "faiss",
            "config": {"dim": 768, "metric": "cosine"}
        }
    ]
}

config = CollectionConfig.from_dict(data)
collection = config.create_collection()
```

### 兼容旧格式

CollectionConfig 支持多种历史格式：

#### 格式 1: storage 对象格式

```python
data = {
    "name": "my_collection",
    "storage": {
        "type": "memory",  # 或 "simple"（自动映射到 "memory"）
        "config": {"persist_dir": "~/.local/share/data"}
    },
    "indexes": [...]
}

config = CollectionConfig.from_dict(data)
```

#### 格式 2: 扁平格式

```python
data = {
    "name": "my_collection",
    "storage_backend": "memory",
    "storage_config": {"persist_dir": "~/.local/share/data"},
    "indexes": [...]
}

config = CollectionConfig.from_dict(data)
```

---

## 从 YAML 创建

### YAML 文件格式

#### 推荐格式（嵌套式）

```yaml
# config/my_collection.yaml
version: "2.0"
service:
  name: "my_service"
  type: "hierarchical.property_graph"
  description: "My custom service"

collection:
  name: "my_collection_memory"
  storage_backend: "memory"
  storage_config:
    persist_dir: "~/.local/share/sage/memory/my_collection"
  indexes:
    - name: "primary_index"
      type: "faiss"
      config:
        dim: 768
        metric: "cosine"
    - name: "keyword_index"
      type: "bm25"
      config:
        k1: 1.5
        b: 0.75
```

#### 兼容格式（顶层 indexes）

```yaml
# config/legacy_collection.yaml
version: "2.0"
service:
  name: "legacy_service"
  type: "partitional.fifo_queue"

collection:
  name: "legacy_collection"
  storage:
    type: "simple"  # 自动映射到 "memory"
    config:
      persist_dir: "~/.local/share/sage/memory/legacy"

indexes:  # 顶层 indexes（自动合并到 collection）
  - name: "main_index"
    type: "faiss"
    config:
      dimension: 768  # 自动转换为 "dim"
      metric: "cosine"
```

### 从 YAML 创建集合

```python
from sage.neuromem.config import CollectionConfig

# 方法 1: 直接加载并创建
config = CollectionConfig.from_yaml("config/my_collection.yaml")
collection = config.create_collection()

# 方法 2: 加载后修改配置
config = CollectionConfig.from_yaml("config/my_collection.yaml")
config.storage_backend = "sagedb"  # 修改存储后端
collection = config.create_collection()

# 方法 3: 使用 MemoryManager 管理
from sage.neuromem import MemoryManager

manager = MemoryManager()
config = CollectionConfig.from_yaml("config/my_collection.yaml")
collection = manager.create_collection(
    name=config.name,
    storage_backend=config.storage_backend,
    storage_config=config.storage_config
)

# 添加索引
for idx_config in config.indexes:
    collection.add_index(
        index_name=idx_config.name,
        index_type=idx_config.index_type,
        config=idx_config.config
    )
```

---

## 索引配置

### 支持的索引类型

#### 1. FAISS 索引（向量检索）

```python
IndexConfig(
    name="faiss_index",
    index_type="faiss",
    config={
        "dim": 768,              # 向量维度（必需）
        "metric": "cosine",      # 距离度量: "cosine", "l2", "ip"
        "index_type": "Flat",    # FAISS 索引类型（可选）
        "normalize": True        # 是否归一化向量（可选）
    }
)
```

#### 2. BM25 索引（关键词检索）

```python
IndexConfig(
    name="bm25_index",
    index_type="bm25",
    config={
        "k1": 1.5,      # 词频饱和参数
        "b": 0.75,      # 长度归一化参数
        "language": "english"  # 语言（可选）
    }
)
```

#### 3. Graph 索引（图结构）

```python
IndexConfig(
    name="graph_index",
    index_type="graph",
    config={
        "directed": False,    # 是否有向图
        "weighted": True      # 是否加权图
    }
)
```

#### 4. FIFO 队列索引

```python
IndexConfig(
    name="fifo_index",
    index_type="fifo",
    config={
        "max_size": 1000,    # 最大容量
        "eviction_policy": "fifo"  # 淘汰策略
    }
)
```

#### 5. Segment 索引（分段索引）

```python
IndexConfig(
    name="segment_index",
    index_type="segment",
    config={
        "max_segment_size": 100,   # 每段最大大小
        "merge_threshold": 0.8     # 合并阈值
    }
)
```

### 参数兼容性

CollectionConfig 自动处理以下参数兼容性：

- **dimension** ↔ **dim**: FAISS 索引维度参数
- **type** ↔ **index_type**: 索引类型字段名
- **simple** → **memory**: 旧的存储类型名称

---

## 存储配置

### Memory 存储（默认）

```python
config = CollectionConfig(
    name="memory_collection",
    storage_backend="memory",
    storage_config={}  # 无需配置
)
```

### Redis 存储

```python
config = CollectionConfig(
    name="redis_collection",
    storage_backend="redis",
    storage_config={
        "host": "localhost",
        "port": 6379,
        "db": 0,
        "prefix": "neuromem:"
    }
)
```

### SageDB 存储

```python
config = CollectionConfig(
    name="sagedb_collection",
    storage_backend="sagedb",
    storage_config={
        "collection_name": "my_vectors",
        "persist_dir": "/path/to/sagedb/data"
    }
)
```

---

## 迁移指南

### 从旧的 Collection 类迁移

**之前（legacy_collection.py）：**

```python
from sage.neuromem.memory_collection import Collection

collection = Collection(
    name="my_data",
    collection_type="vectordb",
    storage_backend="memory"
)

collection.create_index(
    index_name="main",
    index_type="faiss",
    config={"dim": 768}
)
```

**之后（使用 CollectionConfig）：**

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

config = CollectionConfig(
    name="my_data",
    storage_backend="memory",
    indexes=[
        IndexConfig(
            name="main",
            index_type="faiss",
            config={"dim": 768}
        )
    ]
)

collection = config.create_collection()
```

### 从 YAML 文件迁移

无需修改现有 YAML 文件！CollectionConfig 自动兼容以下格式：

- `storage.type: "simple"` → 自动映射到 `storage_backend: "memory"`
- `dimension: 768` → 自动转换为 `dim: 768`
- 顶层 `indexes` → 自动合并到 `collection.indexes`

---

## 完整示例

### 示例 1: 语义搜索集合

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

# 创建配置
config = CollectionConfig(
    name="semantic_search",
    storage_backend="memory",
    indexes=[
        IndexConfig(
            name="embeddings",
            index_type="faiss",
            config={
                "dim": 1536,
                "metric": "cosine",
                "normalize": True
            }
        )
    ],
    metadata={
        "description": "Semantic search collection",
        "version": "1.0"
    }
)

# 创建集合
collection = config.create_collection()

# 插入数据（需要提供向量）
import numpy as np
collection.insert(
    "doc1",
    {
        "text": "NeuroMem is a memory engine",
        "vector": np.random.rand(1536)
    }
)

# 检索
results = collection.retrieve(
    query="memory",
    query_vector=np.random.rand(1536),
    top_k=5,
    index_name="embeddings"
)
```

### 示例 2: 混合检索集合

```python
from sage.neuromem.config import CollectionConfig, IndexConfig

config = CollectionConfig(
    name="hybrid_search",
    indexes=[
        # 语义索引
        IndexConfig(
            name="semantic",
            index_type="faiss",
            config={"dim": 768, "metric": "cosine"}
        ),
        # 关键词索引
        IndexConfig(
            name="keyword",
            index_type="bm25",
            config={"k1": 1.5, "b": 0.75}
        )
    ]
)

collection = config.create_collection()

# 语义检索
semantic_results = collection.retrieve(
    query="machine learning",
    query_vector=get_embedding("machine learning"),
    index_name="semantic",
    top_k=10
)

# 关键词检索
keyword_results = collection.retrieve(
    query="machine learning",
    index_name="keyword",
    top_k=10
)
```

### 示例 3: 从 YAML 批量创建

```python
from sage.neuromem.config import CollectionConfig
from sage.neuromem import MemoryManager
from pathlib import Path

# 扫描配置目录
config_dir = Path("config")
yaml_files = list(config_dir.glob("*.yaml"))

# 批量创建集合
manager = MemoryManager()
collections = {}

for yaml_file in yaml_files:
    config = CollectionConfig.from_yaml(yaml_file)
    collection = manager.create_collection(
        name=config.name,
        storage_backend=config.storage_backend,
        storage_config=config.storage_config
    )

    # 添加索引
    for idx_config in config.indexes:
        collection.add_index(
            index_name=idx_config.name,
            index_type=idx_config.index_type,
            config=idx_config.config
        )

    collections[config.name] = collection
    print(f"✓ Created {config.name} with {len(config.indexes)} indexes")

# 使用集合
my_collection = collections["my_collection"]
my_collection.insert("data1", {"text": "Hello"})
```

### 示例 4: 配置序列化和持久化

```python
from sage.neuromem.config import CollectionConfig, IndexConfig
from pathlib import Path
import yaml

# 创建配置
config = CollectionConfig(
    name="my_collection",
    storage_backend="memory",
    indexes=[
        IndexConfig(
            name="main",
            index_type="faiss",
            config={"dim": 768, "metric": "cosine"}
        )
    ]
)

# 保存为 YAML
yaml_data = config.to_yaml()
output_path = Path("config/generated_config.yaml")
output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w") as f:
    yaml.safe_dump(yaml_data, f, default_flow_style=False)

print(f"Config saved to {output_path}")

# 重新加载
loaded_config = CollectionConfig.from_yaml(output_path)
assert loaded_config.name == config.name
assert len(loaded_config.indexes) == len(config.indexes)
```

---

## API 参考

### CollectionConfig

#### 构造函数

```python
CollectionConfig(
    name: str,
    storage_backend: str = "memory",
    storage_config: dict[str, Any] = {},
    indexes: list[IndexConfig] = [],
    metadata: dict[str, Any] = {}
)
```

#### 类方法

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> CollectionConfig
```

从字典创建配置。支持多种格式兼容。

```python
@classmethod
def from_yaml(cls, yaml_path: str | Path) -> CollectionConfig
```

从 YAML 文件创建配置。

#### 实例方法

```python
def to_dict(self) -> dict[str, Any]
```

转换为字典格式。

```python
def to_yaml(self) -> dict[str, Any]
```

转换为 YAML 兼容格式。

```python
def create_collection(self) -> UnifiedCollection
```

使用此配置创建 UnifiedCollection 实例。

### IndexConfig

#### 构造函数

```python
@dataclass
class IndexConfig:
    name: str
    index_type: str
    config: dict[str, Any] = field(default_factory=dict)
```

#### 类方法

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> IndexConfig
```

从字典创建索引配置。自动处理 `dimension` → `dim` 转换。

#### 实例方法

```python
def to_dict(self) -> dict[str, Any]
```

转换为字典格式。

---

## 最佳实践

1. **使用 YAML 配置文件**: 便于版本控制和环境配置
2. **参数验证**: 使用 `from_yaml()` 加载后检查配置正确性
3. **索引命名**: 使用描述性名称（如 `"semantic"`, `"keyword"`）
4. **存储选择**: 开发用 `"memory"`，生产用 `"redis"` 或 `"sagedb"`
5. **配置重用**: 将常用配置保存为 YAML 模板

---

## 常见问题

### Q: 如何选择存储后端？

- **memory**: 快速原型开发，小规模数据
- **redis**: 分布式环境，需要持久化
- **sagedb**: 大规模向量数据，高性能检索

### Q: 可以动态添加索引吗？

可以。即使 CollectionConfig 中没有索引，也可以在运行时添加：

```python
config = CollectionConfig(name="my_collection")
collection = config.create_collection()

# 运行时添加索引
collection.add_index(
    index_name="dynamic_index",
    index_type="faiss",
    config={"dim": 768}
)
```

### Q: YAML 文件中的 `dimension` 和 `dim` 有什么区别？

没有区别。CollectionConfig 会自动将 `dimension` 转换为 `dim`，保持向后兼容。

### Q: 如何迁移现有的 YAML 配置？

无需修改！现有 YAML 文件自动兼容。只需使用 `CollectionConfig.from_yaml()` 加载即可。

---

## 参考资源

- [MemoryManager 文档](../sage/neuromem/memory_manager.py)
- [UnifiedCollection API](../sage/neuromem/memory_collection/unified_collection.py)
- [Memory Services API](../sage/neuromem/services/API_REFERENCE.md)
- [示例配置文件](../sage/neuromem/config/)
