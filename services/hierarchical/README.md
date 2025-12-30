# Hierarchical Services

层次化记忆服务，提供基于图结构的知识组织和检索能力。

## 概述

Hierarchical Services 包含两种核心服务：

1. **LinknoteGraphService** - 笔记链接图服务
   - 无向图设计，支持双向链接
   - Obsidian 风格的笔记关系管理
   - BFS/DFS 图遍历检索

2. **PropertyGraphService** - 属性图服务
   - 有向图设计，支持实体关系建模
   - 知识图谱 (Entity-Relation-Entity) 模式
   - 双向关系查询和属性过滤

## 快速开始

### 安装

```bash
pip install isage-middleware
```

### Linknote 笔记链接示例

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry

# 创建服务
collection = UnifiedCollection("my_notes")
service = MemoryServiceRegistry.create("linknote_graph", collection)

# 插入笔记
python_note = service.insert(
    "Python 编程语言",
    metadata={"topic": "programming", "difficulty": "medium"}
)

oop_note = service.insert(
    "面向对象编程",
    links=[python_note],  # 链接到 Python 笔记
    metadata={"topic": "programming", "difficulty": "advanced"}
)

# 查询反向链接
backlinks = service.get_backlinks(python_note)
print(f"引用 Python 的笔记: {backlinks}")

# 图遍历检索
related_notes = service.retrieve(python_note, max_hops=2, method="bfs")
```

### PropertyGraph 知识图谱示例

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry

# 创建服务
collection = UnifiedCollection("knowledge_graph")
service = MemoryServiceRegistry.create("property_graph", collection)

# 插入实体和关系
python = service.insert(
    "Python",
    metadata={"entity_type": "Language", "year": 1991}
)

guido = service.insert(
    "Guido van Rossum",
    metadata={"entity_type": "Person"},
    relationships=[
        (python, "CREATED", {"year": 1991})
    ]
)

# 添加更多关系
django = service.insert("Django", metadata={"entity_type": "Framework"})
service.add_relationship(django, python, "WRITTEN_IN")

# 查询相关实体
# 默认 direction="both" 查询双向关系
related = service.get_related_entities(python)
for entity in related:
    print(f"相关实体: {entity['text']} ({entity['metadata']['entity_type']})")

# 只查询出边关系
outgoing = service.get_related_entities(python, direction="outgoing")

# 只查询入边关系
incoming = service.get_related_entities(python, direction="incoming")
```

## 核心功能

### LinknoteGraphService

#### 初始化

```python
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import LinknoteGraphService

service = LinknoteGraphService(collection)
# 或通过注册表
service = MemoryServiceRegistry.create("linknote_graph", collection)
```

#### 插入笔记

```python
note_id = service.insert(
    text="笔记内容",
    links=["other_note_id"],  # 可选：链接到其他笔记
    metadata={"tag": "AI", "date": "2025-01-01"}  # 可选：元数据
)
```

#### 查询反向链接

```python
# 获取所有引用该笔记的其他笔记
backlinks = service.get_backlinks(note_id)
```

#### 获取邻居节点

```python
# 1-hop 邻居
neighbors = service.get_neighbors(note_id, max_hops=1)

# 2-hop 邻居
neighbors = service.get_neighbors(note_id, max_hops=2)
```

#### 图遍历检索

```python
# BFS 遍历
results = service.retrieve(
    note_id,
    max_hops=2,
    method="bfs",  # 广度优先搜索
    include_start=True
)

# DFS 遍历
results = service.retrieve(
    note_id,
    max_hops=2,
    method="dfs",  # 深度优先搜索
    include_start=False
)
```

### PropertyGraphService

#### 初始化

```python
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import PropertyGraphService

service = PropertyGraphService(collection)
# 或通过注册表
service = MemoryServiceRegistry.create("property_graph", collection)
```

#### 插入实体

```python
# 简单实体
entity_id = service.insert("实体名称")

# 带元数据
entity_id = service.insert(
    "实体名称",
    metadata={
        "entity_type": "Person",
        "age": 30,
        "occupation": "Engineer"
    }
)

# 同时创建关系
entity_id = service.insert(
    "实体名称",
    metadata={"entity_type": "Person"},
    relationships=[
        (target_id, "WORKS_AT", {"since": 2020}),
        (another_id, "KNOWS", {})
    ]
)
```

#### 添加关系

```python
# 简单关系
service.add_relationship(source_id, target_id, "RELATES_TO")

# 带属性的关系
service.add_relationship(
    person_id,
    company_id,
    "WORKS_AT",
    properties={"position": "Engineer", "start_year": 2020}
)
```

#### 查询相关实体

```python
# 双向查询（默认）
related = service.get_related_entities(entity_id)

# 只查询出边（A → B）
outgoing = service.get_related_entities(entity_id, direction="outgoing")

# 只查询入边（B → A）
incoming = service.get_related_entities(entity_id, direction="incoming")

# 按关系类型过滤（未来支持）
# related = service.get_related_entities(entity_id, relation_type="WORKS_AT")
```

#### 检索实体

```python
# 按实体类型
persons = service.retrieve(
    query="",
    entity_type="Person"
)

# 按属性过滤 (注意: 属性需在 metadata 中)
engineers = service.retrieve(
    query="",
    entity_type="Person",
    property_filters={"occupation": "Engineer"}
)

# 按 ID 检索
entity = service.retrieve(entity_id)
```

## 高级用法

### 混合知识库

同时使用笔记链接和知识图谱：

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry

# 共享底层存储
shared_collection = UnifiedCollection("hybrid_kb")

# 创建两种服务
notes = MemoryServiceRegistry.create("linknote_graph", shared_collection)
entities = MemoryServiceRegistry.create("property_graph", shared_collection)

# 笔记层
note_id = notes.insert("关于 Python 的研究笔记", metadata={"type": "note"})

# 知识图谱层
python_id = entities.insert("Python", metadata={"type": "entity", "entity_type": "Language"})

# 两者共享同一个 Collection
print(f"总数据量: {shared_collection.size()}")  # 2
```

### 复杂关系遍历

```python
# 构建多层关系网络
company = service.insert("TechCorp", metadata={"entity_type": "Company"})
product = service.insert("Product X", metadata={"entity_type": "Product"})
tech = service.insert("AI Technology", metadata={"entity_type": "Technology"})

service.add_relationship(product, company, "MANUFACTURED_BY")
service.add_relationship(product, tech, "USES")

# 多跳查询
# 从公司出发，找到所有相关的技术
# Company → Product → Technology
related = service.get_related_entities(company, direction="incoming")  # 找到产品
for prod in related:
    techs = service.get_related_entities(prod["id"], direction="outgoing")  # 找到技术
    print(f"技术: {techs}")
```

### 删除操作

```python
# 删除笔记（同时删除相关链接）
notes.delete(note_id)

# 删除实体（同时删除相关关系）
entities.delete(entity_id)
```

### 列出所有索引

```python
indexes = service.list_indexes()
print(f"当前索引: {indexes}")  # ['note_graph'] 或 ['property_graph']
```

## 性能考虑

### 大规模图

```python
# 批量插入优化
entity_ids = []
for i in range(1000):
    entity_id = service.insert(
        f"Entity {i}",
        metadata={"index": i}
    )
    entity_ids.append(entity_id)

# 批量创建关系
import random
for _ in range(500):
    source = random.choice(entity_ids)
    target = random.choice(entity_ids)
    if source != target:
        service.add_relationship(source, target, "RELATES_TO")
```

### 深度遍历

```python
# 控制遍历深度避免性能问题
neighbors = service.get_neighbors(note_id, max_hops=3)  # 最多3跳

# 对于深度图，使用 BFS 通常比 DFS 更高效
results = service.retrieve(note_id, max_hops=2, method="bfs")
```

## 数据持久化

```python
# UnifiedCollection 支持持久化
from pathlib import Path

# 保存
collection.save(Path("./data"))

# 加载
collection = UnifiedCollection.load("my_notes", Path("./data"))
service = MemoryServiceRegistry.create("linknote_graph", collection)
```

## 边界情况处理

### 循环引用

```python
# Linknote 允许循环引用
note_a = service.insert("Note A")
note_b = service.insert("Note B", links=[note_a])
note_c = service.insert("Note C", links=[note_b])

# 手动创建循环: A → B → C → A
# 遍历算法会正确处理，不会死循环
neighbors = service.get_neighbors(note_a, max_hops=10)
```

### 自环

```python
# PropertyGraph 会自动过滤自环
entity = service.insert("Self-ref Entity")
service.add_relationship(entity, entity, "SELF")

# 查询时自动过滤掉自己
related = service.get_related_entities(entity)
print(len(related))  # 0
```

### 空图操作

```python
# 安全处理不存在的节点
backlinks = service.get_backlinks("nonexistent_id")  # 返回 []
related = service.get_related_entities("nonexistent_id")  # 返回 []
```

## API 参考

### LinknoteGraphService

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `insert()` | text, links=None, metadata=None | str | 插入笔记 |
| `retrieve()` | query, max_hops=1, method="bfs" | list[dict] | 图遍历检索 |
| `get_backlinks()` | note_id | list[str] | 获取反向链接 |
| `get_neighbors()` | note_id, max_hops=1 | list[str] | 获取邻居节点 |
| `delete()` | note_id | bool | 删除笔记 |
| `list_indexes()` | - | list[str] | 列出索引 |

### PropertyGraphService

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `insert()` | text, metadata=None, relationships=None | str | 插入实体 |
| `add_relationship()` | source, target, relation_type, properties=None | bool | 添加关系 |
| `get_related_entities()` | entity_id, relation_type=None, direction="both" | list[dict] | 查询相关实体 |
| `retrieve()` | query | list[dict] | 检索实体 |
| `delete()` | entity_id | bool | 删除实体 |
| `list_indexes()` | - | list[str] | 列出索引 |

## 测试

运行测试套件：

```bash
# 单元测试
pytest packages/sage-middleware/tests/unit/components/sage_mem/neuromem/services/test_linknote_graph.py -v
pytest packages/sage-middleware/tests/unit/components/sage_mem/neuromem/services/test_property_graph.py -v

# 集成测试
pytest packages/sage-middleware/tests/integration/services/test_hierarchical_services_integration.py -v
```

## 示例代码

完整示例见：
- `examples/services/linknote_example.py` - Linknote 完整示例
- `examples/services/property_graph_example.py` - PropertyGraph 完整示例
- `examples/services/hybrid_knowledge_base.py` - 混合知识库示例

## 贡献指南

参见项目根目录的 `CONTRIBUTING.md`。

## 许可证

MIT License
