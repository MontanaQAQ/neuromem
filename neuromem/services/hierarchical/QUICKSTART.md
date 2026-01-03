# Hierarchical Services 快速开始

5分钟快速上手 Linknote 和 PropertyGraph 服务。

## 安装

```bash
pip install isage-middleware
```

## 场景 1: 笔记链接（Linknote）

适用于：Obsidian 风格笔记、文档管理、知识网络

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry
# 导入服务类以触发装饰器注册
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import LinknoteGraphService

# 1. 创建服务
collection = UnifiedCollection("my_notes")
notes = MemoryServiceRegistry.create("linknote_graph", collection)

# 2. 插入笔记
python_note = notes.insert("Python 编程语言")
oop_note = notes.insert("面向对象编程", links=[python_note])

# 3. 查询反向链接
backlinks = notes.get_backlinks(python_note)
print(f"引用 Python 笔记的数量: {len(backlinks)}")

# 4. 图遍历
related = notes.retrieve(python_note, max_hops=2, method="bfs")
```

## 场景 2: 知识图谱（PropertyGraph）

适用于：实体关系、知识图谱、业务建模

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry
# 导入服务类以触发装饰器注册
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import PropertyGraphService

# 1. 创建服务
collection = UnifiedCollection("knowledge_graph")
kg = MemoryServiceRegistry.create("property_graph", collection)

# 2. 插入实体
python = kg.insert("Python", metadata={"entity_type": "Language"})
guido = kg.insert("Guido van Rossum", metadata={"entity_type": "Person"})

# 3. 添加关系
kg.add_relationship(guido, python, "CREATED", properties={"year": 1991})

# 4. 查询相关实体（双向）
related = kg.get_related_entities(python)
for entity in related:
    print(f"{entity['text']} ({entity['metadata']['entity_type']})")
```

## 场景 3: 混合知识库

同时使用笔记和知识图谱：

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import UnifiedCollection
from sage.middleware.components.sage_mem.neuromem.services import MemoryServiceRegistry
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import (
    LinknoteGraphService,
    PropertyGraphService,
)

# 共享底层存储
collection = UnifiedCollection("hybrid_kb")
notes = MemoryServiceRegistry.create("linknote_graph", collection)
entities = MemoryServiceRegistry.create("property_graph", collection)

# 笔记层
note_id = notes.insert("Python 学习笔记", metadata={"type": "note"})

# 知识图谱层
entity_id = entities.insert("Python", metadata={"type": "entity", "entity_type": "Language"})

print(f"总数据量: {collection.size()}")  # 2
```

## 核心 API 速查

### Linknote

| 操作 | 代码 |
|------|------|
| 插入笔记 | `notes.insert(text, links=[], metadata={})` |
| 反向链接 | `notes.get_backlinks(note_id)` |
| 邻居节点 | `notes.get_neighbors(note_id, max_hops=1)` |
| 图遍历 | `notes.retrieve(note_id, max_hops=2, method="bfs")` |
| 删除笔记 | `notes.delete(note_id)` |

### PropertyGraph

| 操作 | 代码 |
|------|------|
| 插入实体 | `kg.insert(text, metadata={}, relationships=[])` |
| 添加关系 | `kg.add_relationship(source, target, relation, properties={})` |
| 查询相关 | `kg.get_related_entities(entity_id, direction="both")` |
| 检索实体 | `kg.retrieve(query={"entity_type": "Person"})` |
| 删除实体 | `kg.delete(entity_id)` |

## 关系查询方向

PropertyGraph 的 `get_related_entities()` 支持三种方向：

```python
# both (默认) - 双向查询：A → B 和 B → A
related = kg.get_related_entities(entity_id, direction="both")

# outgoing - 只查询出边：A → B
outgoing = kg.get_related_entities(entity_id, direction="outgoing")

# incoming - 只查询入边：B → A
incoming = kg.get_related_entities(entity_id, direction="incoming")
```

## 完整示例

查看 `examples/services/` 目录：

- `linknote_example.py` - Linknote 完整示例（7个场景）
- `property_graph_example.py` - PropertyGraph 完整示例（9个场景）
- `hybrid_knowledge_base.py` - 混合知识库（3个工作流）

运行示例：

```bash
python examples/services/linknote_example.py
python examples/services/property_graph_example.py
python examples/services/hybrid_knowledge_base.py
```

## 下一步

- 阅读完整文档：[README.md](README.md)
- 运行测试：`pytest packages/sage-middleware/tests/unit/components/sage_mem/neuromem/services/ -v`
- 查看源码：`linknote_graph_service.py` 和 `property_graph_service.py`

## 常见问题

**Q: 服务未注册错误？**

A: 确保导入了服务类：
```python
from sage.middleware.components.sage_mem.neuromem.services.hierarchical import (
    LinknoteGraphService,
    PropertyGraphService,
)
```

**Q: Linknote 和 PropertyGraph 的区别？**

A:
- Linknote: 无向图，双向链接，适合笔记网络
- PropertyGraph: 有向图，实体关系，适合知识图谱

**Q: 如何持久化数据？**

A:
```python
from pathlib import Path
collection.save(Path("./data"))
collection = UnifiedCollection.load("my_notes", Path("./data"))
```
