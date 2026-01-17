# Memory Pipeline Actions 配置手册

> 本目录的文档以 `benchmarks/experiment/libs/**` 的 Registry/Operator 实现为准（即“代码即真相”）。

## 文档导航

- `01_pre_insert.md`：Pre-Insert Actions（插入前预处理）
- `02_pre_retrieval.md`：Pre-Retrieval Actions（检索前查询处理）
- `03_post_insert.md`：Post-Insert Actions（插入后维护/优化）
- `04_post_retrieval.md`：Post-Retrieval Actions（检索后处理/拼接上下文）
- `05_memory_data_structure.md`：Memory Data Structure（跨阶段数据结构与底层映射）

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

> **第五个维度（跨阶段）**：`05_memory_data_structure.md` 解释数据在 Benchmark Pipeline 的字段形态（如 `memory_entries / insert_stats / memory_data / history_text`），以及与 NeuroMem 底层 `UnifiedCollection/Storage/Index` 的映射关系。

---

## 可用 Actions 配置列表

> 本手册使用“Action Key”描述可选动作，Action Key 与 Registry 中注册名一致。
>
> Benchmark 配置文件采用如下结构（示例摘自 `benchmarks/experiment/config/**/*.yaml`）：
>
> - `operators.<stage>.action: <action_key>`
> - 其余字段为该 action 的参数（可选）
>
> 说明：Operator 同时兼容两种写法：
> 1) **推荐**：直接写全量 key（如 `extract.triple`、`rerank.semantic`）
> 2) 兼容：写 `action: extract` + `extract_type: triple`（同理 `transform_type`、`optimize_type` 等）

### 1. Pre-Insert Actions（7个 + 1个废弃别名）

#### 1.1 透传类（1个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `none` | 无操作透传 |

#### 1.2 Transform 类（2个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `transform.segment_denoise` | 分段去噪 |
| `transform.summarize` | 文本摘要 |

#### 1.3 Extract 类（4个）
| Action配置名 | 功能说明 |
|-------------|---------|
| `extract.keyword` | 关键词提取 |
| `extract.entity` | 实体提取 |
| `extract.triple` | 三元组提取 |
| `extract.fact` | 事实提取 |

#### 1.4 已废弃别名（向后兼容）
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

### 3. Post-Insert Actions（8个，按策略分类）

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

#### 3.4 Structure Enrichment 策略（3个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `structure_enrichment.link_evolution` | 链接演化 | A-Mem |
| `structure_enrichment.graph_construction` | 图构建 | HippoRAG |
| `structure_enrichment.heat_migration` | 基于热度的层级迁移 | MemoryOS |

---

### 4. Post-Retrieval Actions（14个）

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

> 注意：`scm_three_way` 在语义上属于 Merge，但其 Action Key **不带** `merge.` 前缀（与 `PostRetrieval` Operator 的 action_key 拼接逻辑兼容）。

#### 4.5 Augment 类（2个）
| Action配置名 | 功能说明 | 代表系统 |
|-------------|---------|---------|
| `augment` | 结果增强（添加 persona/traits/summary） | 所有系统 |
| `augment.reinforce` | 记忆强化（更新记忆强度） | MemoryBank |

---

## 配置示例（Benchmark YAML）

### 最小化配置（仅透传）
```yaml
operators:
  pre_insert:
    action: none
  pre_retrieval:
    action: embedding
  post_insert:
    action: none
  post_retrieval:
    action: none
```

### 典型向量检索配置
```yaml
operators:
  pre_insert:
    action: extract.keyword
  pre_retrieval:
    action: optimize.keyword_extract
  post_retrieval:
    action: filter.top_k
```

### 高级图谱 + RAG 配置
```yaml
operators:
  pre_insert:
    action: extract.triple
  post_insert:
    action: structure_enrichment.graph_construction
  pre_retrieval:
    action: enhancement.route
  post_retrieval:
    action: rerank.ppr
```
