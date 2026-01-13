# Memory Pipeline Actions 配置手册

## 四个阶段的定位

| 阶段 | 时机 | 核心职责 | 输入 | 输出 |
|------|------|---------|------|------|
| **Pre-Insert** | 数据插入前 | 数据预处理、特征提取 | 原始文本/数据 | 结构化数据 + 元数据 |
| **Pre-Retrieval** | 检索执行前 | 查询优化、向量化 | 用户查询 | 优化查询 + 向量 |
| **Post-Insert** | 数据插入后 | 记忆维护、优化 | 已存储数据 | 维护操作决策 |
| **Post-Retrieval** | 检索执行后 | 结果优化、排序 | 检索结果集 | 优化后的结果 |

> **💡 透传操作（Passthrough）**: `embedding` 和 `none` 是两种特殊的透传操作：
> - **`embedding`**: 向量化透传（Pre-Retrieval阶段）- 仅做基础向量化，不进行复杂优化
> - **`none`**: 无操作透传（所有阶段）- 直接传递数据，不做任何处理

---

## 可用 Actions 配置列表

### 1. Pre-Insert Actions（14个）

#### 1.1 透传类（1个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `none` | 无操作透传 |

#### 1.2 Transform 类（5个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `transform.chunking` | 文本分块 |
| `transform.summarize` | 文本摘要 |
| `transform.segment` | 主题分段 |
| `transform.segment_denoise` | 分段去噪 |
| `transform.continuity_check` | 连续性检查 |

#### 1.3 Extract 类（5个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `extract.keyword` | 关键词提取 |
| `extract.entity` | 实体提取 |
| `extract.noun` | 名词提取 |
| `extract.triple` | 三元组提取 |
| `extract.multi_summary` | 多级摘要提取 |

#### 1.4 Score 类（2个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `score.importance` | 重要性评分 |
| `score.heat` | 热度评分 |

#### 1.5 已废弃别名
| Action配置名 | 功能说明 | 替代方案 |
|-------------|---------|---------|
| `tri_embed` | 三元组提取（已废弃） | 使用 `extract.triple` |

---

### 2. Pre-Retrieval Actions（9个）

#### 2.1 基础类（3个）
| Action配置名 | 功能说明 | 典型用例 |
|-------------|---------|---------|
| `none` | 无操作透传 | 不做任何预处理，直接使用原始查询 |
| `embedding` | 查询向量化 | 将查询文本转换为向量表示 |
| `validate` | 查询验证 | 验证查询是否需要检索或是否有效 |

#### 2.2 Optimize 类（3个）
| Action配置名 | 功能说明 | 典型用例 |
|-------------|---------|---------|
| `optimize.keyword_extract` | 关键词提取 | "Tell me about Python programming" → ["Python", "programming"] |
| `optimize.expand` | 查询扩展 | "Python" → "Python programming language features syntax" |
| `optimize.rewrite` | 查询改写 | "How to use it?" → "How to use Python?" (消歧义) |

#### 2.3 Enhancement 类（3个）
| Action配置名 | 功能说明 | 典型用例 |
|-------------|---------|---------|
| `enhancement.decompose` | 复杂查询分解 | "早餐吃了什么和天气如何?" → ["早餐吃了什么?", "天气如何?"] |
| `enhancement.route` | 检索路由 | 根据查询类型路由到不同的检索目标（知识库/长期记忆） |
| `enhancement.multi_embed` | 多维向量化 | 从多个维度（语义/情感/实体）生成查询向量 |

---

### 3. Post-Insert Actions（9个，按策略分类）

#### 3.1 透传类（1个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `none` | 无操作透传 |

#### 3.2 Conflict Resolution 策略（2个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `conflict_resolution.llm_crud` | LLM驱动的CRUD操作 | Mem0, MemGPT, TiM |
| `conflict_resolution.semantic_consolidation` | 语义合并 | Mem0ᵍ |

#### 3.3 Decay Eviction 策略（2个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `decay_eviction.forgetting_curve` | 遗忘曲线驱逐 | MemoryBank |
| `decay_eviction.time_decay` | 时间衰减驱逐 | LD-Agent |

#### 3.4 Structure Enrichment 策略（2个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `structure_enrichment.link_evolution` | 链接演化 | A-Mem |
| `structure_enrichment.graph_construction` | 图构建 | HippoRAG |

#### 3.5 Tier Migration 策略（1个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `structure_enrichment.heat_migration` | 基于热度的层级迁移 | MemoryOS |

---

### 4. Post-Retrieval Actions（16个）

#### 4.1 透传类（1个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `none` | 无操作透传 |

#### 4.2 Rerank 类（4个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `rerank.semantic` | 语义重排序 | 所有系统 |
| `rerank.time_weighted` | 时间加权重排序 | 对话系统 |
| `rerank.ppr` | PageRank重排序 | HippoRAG |
| `rerank.weighted` | 多因子加权重排序 | 综合系统 |

#### 4.3 Filter 类（3个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `filter.token_budget` | Token预算过滤 |
| `filter.threshold` | 阈值过滤 |
| `filter.top_k` | Top-K过滤 |

#### 4.4 Merge 类（4个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `merge.link_expand` | 链接扩展合并 | A-Mem |
| `merge.multi_query` | 多查询合并 | Multi-Query系统 |
| `merge.multi_tier` | 多层融合 | MemGPT |
| `scm_three_way` | SCM三路合并 | SCM |

#### 4.5 Augment 类（2个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `augment` | 结果增强（添加 persona/traits/summary） | 所有系统 |
| `augment.reinforce` | 记忆强化（更新记忆强度） | MemoryBank |

---

## 配置示例

### 最小化配置（仅透传）
```yaml
pre_insert:
  - none

pre_retrieval:
  - embedding

post_insert:
  - none

post_retrieval:
  - none
```

### 典型向量检索配置
```yaml
pre_insert:
  - transform.chunking
  - extract.keyword

pre_retrieval:
  - optimize.keyword_extract
  - embedding

post_retrieval:
  - filter.top_k
```

### 高级图谱 + RAG 配置
```yaml
pre_insert:
  - extract.triple
  - extract.entity
  - score.importance

post_insert:
  - structure_enrichment.graph_construction
  - structure_enrichment.link_evolution

pre_retrieval:
  - enhancement.route
  - embedding

post_retrieval:
  - merge.multi_query
  - rerank.ppr
  - filter.token_budget
```
