"""
Hierarchical Services - 层次型内存服务

包含三个 Service:
- LinknoteGraphService: 链接笔记图服务 (双向链接 + 图遍历)
- PropertyGraphService: 属性图服务 (节点属性 + 关系属性)
- SemanticInvertedKnowledgeGraphService: 语义+倒排+知识图谱三层服务

文档:
- README: neuromem/services/hierarchical/README.md
- 示例: examples/services/
  - linknote_example.py - Linknote 完整示例
  - property_graph_example.py - PropertyGraph 完整示例
  - hybrid_knowledge_base.py - 混合知识库示例

快速开始:
```python
from neuromem.memory_collection import UnifiedCollection
from neuromem.services import MemoryServiceRegistry

# Linknote 笔记链接
collection = UnifiedCollection("my_notes")
notes = MemoryServiceRegistry.create("linknote_graph", collection)
note_id = notes.insert("笔记内容", links=["other_note_id"])
backlinks = notes.get_backlinks(note_id)

# PropertyGraph 知识图谱
collection = UnifiedCollection("knowledge_graph")
kg = MemoryServiceRegistry.create("property_graph", collection)
entity_id = kg.insert("实体名称", metadata={"entity_type": "Person"})
kg.add_relationship(entity_id, target_id, "RELATES_TO")
related = kg.get_related_entities(entity_id)

# Semantic+Inverted+KG 三层服务
collection = UnifiedCollection("complex_kb")
service = MemoryServiceRegistry.create(
    "hierarchical.semantic_inverted_knowledge_graph",
    collection,
    config={"routing_strategy": "cascade"}
)
service.insert("文档内容", entities=["实体1", "实体2"])
results = service.retrieve("查询", top_k=5, strategy="cascade")
```
"""

from .linknote_graph_service import LinknoteGraphService
from .property_graph_service import PropertyGraphService
from .semantic_inverted_knowledge_graph import SemanticInvertedKnowledgeGraphService

__all__ = [
    "LinknoteGraphService",
    "PropertyGraphService",
    "SemanticInvertedKnowledgeGraphService",
]
