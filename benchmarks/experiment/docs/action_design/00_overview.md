# Memory Pipeline Actions 设计维度总览

## 四个阶段的定位

| 阶段 | 时机 | 核心职责 | 输入 | 输出 |
|------|------|---------|------|------|
| **Pre-Insert** | 数据插入前 | 数据预处理、特征提取 | 原始文本/数据 | 结构化数据 + 元数据 |
| **Pre-Retrieval** | 检索执行前 | 查询优化、向量化 | 用户查询 | 优化查询 + 向量 |
| **Post-Insert** | 数据插入后 | 记忆维护、优化 | 已存储数据 | 维护操作决策 |
| **Post-Retrieval** | 检索执行后 | 结果优化、排序 | 检索结果集 | 优化后的结果 |

> **💡 透传操作（Passthrough）**: 在整个设计中，`embedding` 和 `none` 是两种特殊的透传操作：
> - **`embedding`**: 向量化透传（Pre-Retrieval阶段）- 仅做基础向量化，不进行复杂优化
> - **`none`**: 无操作透传（所有阶段）- 直接传递数据，不做任何处理

---

## 维度设计对比

### Pre-Insert（4个维度）
| 维度 | 功能 | Action数量 | 代表系统 |
|------|------|-----------|---------|
| **None (透传)** | 无操作 | 1 | HippoRAG2, SCM |
| **Extract** | 信息提取 | 6 | 所有系统 |
| **Score** | 重要性评分 | 2 | MemoryOS, MemoryBank |
| **Transform** | 格式转换 | 2 | HippoRAG, A-Mem |

### Pre-Retrieval（5个维度）
| 维度 | 功能 | Action数量 | 代表系统 |
|------|------|-----------|---------|
| **Embedding (透传)** | 向量化 | 1 | 所有向量检索系统 |
| **None (透传)** | 无操作 | 1 | 纯文本检索系统 |
| **Enhancement** | 查询增强 | 3 | HippoRAG, Multi-Query |
| **Optimize** | 查询优化 | 3 | 所有系统 |
| **Validate** | 合法性检查 | 1 | 所有系统 |

### Post-Insert（5个策略维度）
| 维度（策略） | 功能 | Action数量 | 代表系统 |
|-------------|------|-----------|---------|
| **None (透传)** | 无操作 | 1 | HippoRAG2, SCM |
| **Conflict Resolution** | 冲突解决 | 2 | Mem0, MemGPT, TiM |
| **Decay Eviction** | 衰减驱逐 | 2 | MemoryBank, LD-Agent |
| **Structure Enrichment** | 结构增强 | 2 | A-Mem, HippoRAG |
| **Tier Migration** | 层级迁移 | 1 | MemoryOS |

### Post-Retrieval（5个维度）
| 维度 | 功能 | Action数量 | 代表系统 |
|------|------|-----------|---------|
| **None (透传)** | 无操作 | 1 | 简单检索系统 |
| **Filter** | 结果过滤 | 3 | 所有系统 |
| **Rerank** | 重排序 | 4 | PPR, 时间加权 |
| **Merge** | 结果合并 | 4 | Multi-Query, SCM |
| **Augment** | 结果增强 | 1 | Reinforce |

---

## 设计原则总结

### 1. 维度正交性
- 各维度功能独立，可组合使用
- 例：Pre-Insert可同时使用Extract + Score + Transform

### 2. 接口统一性
所有Action遵循统一基类：
```python
class BaseXxxAction(ABC):
    def _init_action(self) -> None: ...
    def execute(self, input_data, service, llm) -> Output: ...
```

### 3. 可配置性
通过YAML配置选择Action组合：
```yaml
pre_insert:
  - extract.entity
  - score.importance
post_insert:
  - conflict_resolution.llm_crud
```

### 4. 分类演进

| 分类方式 | 适用阶段 | 优势 |
|---------|---------|------|
| **按功能分类** | Pre-Insert, Pre-Retrieval, Post-Retrieval | 直观易懂 |
| **按策略分类** | Post-Insert | 反映设计意图，便于论文对齐 |

---

## 典型组合模式

### 模式1: 长文档存储 + 检索
```yaml
pre_insert:
  - extract.multi_summary
  - transform.chunking
  - score.importance

pre_retrieval:
  - enhancement.decompose
  - optimize.rewrite
  - embedding.base

post_retrieval:
  - rerank.semantic
  - filter.top_k
```

### 模式2: 对话记忆系统
```yaml
pre_insert:
  - extract.entity
  - score.heat

post_insert:
  - conflict_resolution.llm_crud
  - tier_migration.heat_migration

pre_retrieval:
  - optimize.keyword_extract
  - embedding.base

post_retrieval:
  - rerank.time_weighted
  - filter.token_budget
```

### 模式3: 知识图谱 + RAG
```yaml
pre_insert:
  - extract.triple
  - extract.entity

post_insert:
  - structure_enrichment.graph_construction
  - structure_enrichment.link_evolution

pre_retrieval:
  - enhancement.route  # 路由到图检索/向量检索
  - embedding.base

post_retrieval:
  - merge.multi_query
  - rerank.ppr  # PageRank重排
```
