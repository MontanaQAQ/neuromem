# 记忆数据结构选择理由

> **文档版本**: v1.0  
> **创建时间**: 2026-01-09  
> **适用范围**: NeuroMem Benchmark 实验设计

---

## 📋 目录

- [1. 底层分类体系](#1-底层分类体系)
- [2. 选择策略](#2-选择策略)
- [3. 五大代表性数据结构](#3-五大代表性数据结构)
- [4. 对比矩阵](#4-对比矩阵)
- [5. 实验价值分析](#5-实验价值分析)

---

## 1. 底层分类体系

NeuroMem 底层将记忆数据结构分为**两大类**，基于数据组织方式和索引策略的根本差异：

### 1.1 Partitional（分区型）

**核心特征**：
- **扁平化存储**：数据在同一层级，无层级关系
- **索引组合驱动**：通过多种索引类型组合实现检索能力
- **静态结构**：不涉及数据迁移、层级演化

**设计原则**：
```
Collection = 一份数据 + N 个索引
数据只存一份，索引可动态增删
```

**已实现服务**（共 8 个）：

| 服务名称 | 索引组合 | 检索能力 |
|---------|---------|---------|
| `fifo_queue` | FIFO | 时序检索 |
| `lsh_hash` | LSH | 近似向量检索 |
| `segment` | Segment | 分段管理 |
| `inverted_vectorstore_combination` | BM25 + FAISS | 文本+语义（2索引） |
| `feature_queue_vectorstore_combination` | BM25 + FIFO + FAISS | 文本+时序+语义（3索引） |
| `feature_queue_segment_combination` | BM25 + FIFO + Segment | 文本+时序+分段（3索引） |
| `feature_queue_summary_combination` | BM25 + FIFO + Summary | 文本+时序+摘要（3索引） |
| `feature_summary_vectorstore_combination` | BM25 + Summary + FAISS | 文本+摘要+语义（3索引） |

**代码路径**：
```python
sage/neuromem/services/partitional/
├── fifo_queue_service.py
├── lsh_hash_service.py
├── segment_service.py
├── inverted_vectorstore_combination.py
├── feature_queue_vectorstore_combination.py
├── feature_queue_segment_combination.py
├── feature_queue_summary_combination.py
└── feature_summary_vectorstore_combination.py
```

### 1.2 Hierarchical（层次型）

**核心特征**：
- **结构关系**：数据之间有明确的关系（链接、三元组、层级）
- **动态演化**：支持数据迁移、链接演化、拓扑变化
- **复杂拓扑**：通常需要 Graph 索引或多层次架构

**设计原则**：
```
Collection = 数据 + 关系 + 演化规则
数据不仅是存储单元，更是网络节点
```

**已实现服务**（共 3 个）：

| 服务名称 | 结构类型 | 核心能力 |
|---------|---------|---------|
| `linknote_graph` | 无向图（双向链接） | 笔记链接、反向链接、图遍历 |
| `property_graph` | 属性图（RDF风格） | 实体-关系-属性三元组 |
| `semantic_inverted_knowledge_graph` | 语义+倒排+知识图谱 | 三层检索：语义→倒排→图谱 |

**代码路径**：
```python
sage/neuromem/services/hierarchical/
├── linknote_graph_service.py
├── property_graph_service.py
└── semantic_inverted_knowledge_graph.py
```

---

## 2. 选择策略

### 2.1 选择原则

基于**类内代表性**和**实验价值**，从 11 个服务中选出 5 个：

1. **覆盖底层分类**：Partitional 和 Hierarchical 都要有代表
2. **覆盖复杂度梯度**：从简单到复杂，便于对比实验
3. **覆盖索引数量维度**：单索引 → 多索引融合
4. **覆盖论文算法映射**：每个结构对应明确的论文
5. **平衡类内多样性**：Partitional（8个实现）选3个，Hierarchical（3个实现）选2个

### 2.2 分配逻辑

**Partitional 类（选 3/8）**：
- **单索引代表** × 2：覆盖时序（FIFO）和语义（LSH）两种范式
- **多索引融合代表** × 1：选择最复杂的三索引组合

**Hierarchical 类（选 2/3）**：
- **简单图代表** × 1：双向链接的基础图结构
- **复杂图代表** × 1：多层语义图谱

### 2.3 排除理由

**Partitional 排除的 5 个**：
- `segment`：与 FIFO 同属时序管理，功能重叠
- `inverted_vectorstore_combination`：2索引组合，实验价值低于3索引
- `feature_queue_segment_combination`：与 `feature_queue_vectorstore_combination` 功能相似
- `feature_queue_summary_combination`：同上
- `feature_summary_vectorstore_combination`：同上

**Hierarchical 排除的 1 个**：
- `property_graph`：与 `linknote_graph` 都是图结构，但后者更简单，适合做基线

---

## 3. 五大代表性数据结构

### 3.1 FIFO Queue（Partitional - 单索引时序）

**选择指数**: ⭐⭐⭐⭐⭐

**注册名称**: `partitional.fifo_queue`

**代表性理由**：
1. **最简单的基线**：无向量计算，纯时序管理，O(1)复杂度
2. **对照组价值**：用于评估"语义检索是否必要"
3. **实际应用广泛**：短期记忆（STM）、滑动窗口、对话上下文
4. **架构典型性**：体现单一索引（FIFO Index）的极简设计
5. **论文映射**：SCM（Short-term Conversational Memory）

**典型配置**：
```yaml
services:
  services_type: "partitional.fifo_queue"
  fifo_queue:
    max_size: 100
```

**核心方法**：
```python
# 插入自动淘汰最旧数据
service.insert("对话内容")

# 返回最近 N 条（按时间倒序）
results = service.retrieve("", top_k=10)
```

---

### 3.2 LSH Hash（Partitional - 单索引语义）

**选择指数**: ⭐⭐⭐⭐⭐

**注册名称**: `partitional.lsh_hash`

**代表性理由**：
1. **高维向量索引代表**：O(1) 近似检索，适合百万级数据
2. **性能对比价值**：与 FAISS 对比"精度 vs 速度"权衡
3. **论文算法映射**：TiM（Time-aware Integrated Memory）
4. **可扩展性强**：通过 `num_tables`/`hash_size` 调优精度
5. **架构典型性**：体现单一向量索引的设计范式

**典型配置**：
```yaml
services:
  services_type: "partitional.lsh_hash"
  lsh_hash:
    embedding_dim: 768
    num_tables: 10      # 哈希表数量（越多越精确）
    hash_size: 128      # 哈希位数
```

**核心方法**：
```python
# 插入需要提供向量
service.insert("文本内容", vector=embedding)

# 检索基于向量相似度
results = service.retrieve("查询", vector=query_embedding, top_k=10)
```

---

### 3.3 Feature-Queue-Vector Combination（Partitional - 三索引融合）

**选择指数**: ⭐⭐⭐⭐⭐

**注册名称**: `partitional.feature_queue_vectorstore_combination`

**代表性理由**：
1. **混合检索代表**：BM25（文本） + FIFO（时序） + FAISS（语义）
2. **多索引融合典范**：体现 "Collection = 一份数据 + 多种索引" 的设计精髓
3. **实验探索价值**：可对比不同融合策略（RRF vs Linear，权重分配）
4. **论文算法映射**：MemGPT、MemoryOS 的混合检索机制
5. **实际应用强**：FAQ、文档检索、智能客服等场景

**典型配置**：
```yaml
services:
  services_type: "partitional.feature_queue_vectorstore_combination"
  feature_queue_vectorstore_combination:
    vector_dim: 768
    fifo_max_size: 100
    combination_strategy: "weighted"
    weights:
      feature_index: 0.3    # BM25权重
      fifo_index: 0.3       # 时序权重
      vector_index: 0.4     # 语义权重
    fusion_method: "rrf"    # RRF或Linear
    rrf_k: 60
```

**核心方法**：
```python
# 插入到三个索引
service.insert("文本内容", vector=embedding)

# 三路检索融合
results = service.retrieve(
    "查询文本",
    vector=query_embedding,
    top_k=10
)
```

**实验维度**：
- 融合策略：RRF vs Linear
- 权重分配：(0.33, 0.33, 0.34) vs (0.2, 0.3, 0.5) vs ...
- 索引启用：单索引 vs 双索引 vs 三索引

---

### 3.4 Linknote Graph（Hierarchical - 简单图）

**选择指数**: ⭐⭐⭐⭐⭐

**注册名称**: `hierarchical.linknote_graph`

**代表性理由**：
1. **图结构代表**：双向链接 + BFS/DFS 遍历
2. **知识管理典范**：Obsidian/Notion 风格的知识网络
3. **论文算法映射**：A-Mem（链接演化记忆）
4. **复杂检索探索**：支持多跳推理、关联扩展
5. **架构典型性**：Graph Index + Vector Index 双索引组合

**典型配置**：
```yaml
services:
  services_type: "hierarchical.linknote_graph"
  linknote_graph:
    embedding_dim: 1024
    index_type: "flat"
operators:
  post_retrieval:
    action: "merge.link_expand"  # 链接扩展
```

**核心方法**：
```python
# 插入笔记并建立链接
note_id = service.insert(
    "笔记内容",
    vector=embedding,
    metadata={"title": "主题"},
    insert_params={"links": ["note_1", "note_2"]}
)

# 获取反向链接
backlinks = service.get_backlinks(note_id)

# 图遍历检索
neighbors = service.get_neighbors(note_id, depth=2)
```

**实验维度**：
- 链接策略：手动链接 vs 自动提取
- 遍历算法：BFS vs DFS
- 链接扩展：直接邻居 vs 多跳推理

---

### 3.5 Semantic Inverted Knowledge Graph（Hierarchical - 复杂图）

**选择指数**: ⭐⭐⭐⭐

**注册名称**: `hierarchical.semantic_inverted_knowledge_graph`

**代表性理由**：
1. **语义图谱代表**：倒排索引 + 知识图谱的深度融合
2. **三元组结构**：(Subject, Predicate, Object) 的结构化知识
3. **论文算法映射**：HippoRAG2（Personalized PageRank）
4. **实验探索价值**：对比"扁平向量" vs "结构化知识"的检索效果
5. **架构前沿性**：体现 Graph Index 与 Vector Index 的协同增强

**典型配置**：
```yaml
services:
  services_type: "hierarchical.semantic_inverted_knowledge_graph"
  semantic_inverted_knowledge_graph:
    embedding_dim: 1024
operators:
  pre_insert:
    action: "extract.triple"  # 三元组提取
  post_retrieval:
    action: "rerank.ppr"      # PPR重排
```

**核心方法**：
```python
# 插入并提取三元组
service.insert(
    "Python是一门编程语言",
    vector=embedding,
    metadata={"source": "knowledge_base"}
)

# 三层检索：语义 → 倒排 → 图谱
results = service.retrieve(
    "什么是Python",
    vector=query_embedding,
    top_k=10
)
```

**实验维度**：
- 三元组提取质量
- PPR 参数调优（阻尼因子、迭代次数）
- 三层检索策略（级联 vs 并行）

---

## 4. 对比矩阵

### 4.1 技术特性对比

| 数据结构 | 类别 | 索引组合 | 时间复杂度 | 适用数据规模 | 向量需求 |
|---------|------|---------|-----------|-------------|---------|
| FIFO Queue | Partitional | FIFO | O(1) | 小（<1K） | ❌ 不需要 |
| LSH Hash | Partitional | LSH | O(1) 近似 | 大（1M+） | ✅ 必需 |
| Feature-Queue-Vector | Partitional | BM25+FIFO+FAISS | O(log N) | 中（10K-100K） | ✅ 必需 |
| Linknote Graph | Hierarchical | Graph+Vector | O(N+E) | 中（10K） | ✅ 可选 |
| Semantic Inverted KG | Hierarchical | Graph+Inverted+Vector | O(log N) | 大（100K+） | ✅ 必需 |

### 4.2 论文算法映射

| 数据结构 | 对应论文 | 核心特性 | Benchmark 数据集 |
|---------|---------|---------|----------------|
| FIFO Queue | SCM | 时序窗口 | LoCoMo |
| LSH Hash | TiM | 时间感知向量检索 | LoCoMo |
| Feature-Queue-Vector | MemGPT/Mem0 | 混合检索+时序管理 | LoCoMo |
| Linknote Graph | A-Mem | 链接演化 | Conflict Resolution |
| Semantic Inverted KG | HippoRAG | 知识图谱+PPR | LongMemEval |

### 4.3 实验价值维度

| 数据结构 | Baseline价值 | 性能对比价值 | 融合策略价值 | 论文复现价值 | 生产应用价值 |
|---------|-------------|-------------|-------------|-------------|-------------|
| FIFO Queue | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| LSH Hash | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Feature-Queue-Vector | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Linknote Graph | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Semantic Inverted KG | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## 5. 实验价值分析

### 5.1 实验设计策略

基于前期分析和实验效率考虑，采用**最小代表集 + 控制变量法**：

#### 第一步：选定 3 个代表性数据结构（D1）

从 11 个服务中选择 **TiM、Mem0ᵍ、MemoryOS** 作为代表：

| 数据结构 | D1 Service | 选择理由 |
|---------|-----------|---------|
| **TiM** | `lsh_hash` | Partitional 类代表，LSH 向量索引，快速近似检索 |
| **Mem0ᵍ** | `semantic_inverted_knowledge_graph` | Hierarchical 类代表，三层语义图谱 |
| **MemoryOS** | `feature_queue_segment_combination` | Partitional 类代表，三索引融合（BM25+FIFO+Segment） |

**覆盖维度**：
- ✅ 底层分类：Partitional（2个）+ Hierarchical（1个）
- ✅ 索引复杂度：单索引（LSH）→ 三索引融合（FQS）→ 三层图谱（SIKG）
- ✅ 论文代表性：TiM（近似检索）、Mem0ᵍ（图记忆）、MemoryOS（分段管理）

#### 第二步：从每个 Operator 维度选出代表性策略

为避免组合爆炸，从每个维度的所有可用策略中，选出**最具代表性的 3-4 个**：

##### D2 (PreInsert) - 可用策略总览与筛选

**所有可用策略**（共 14 个）：
- 基础：`none`
- 转换：`transform.chunking`, `transform.summarize`, `transform.segment`, `transform.segment_denoise`, `transform.continuity_check`
- 提取：`extract.keyword`, `extract.entity`, `extract.noun`, `extract.triple`, `extract.multi_summary`
- 评分：`score.importance`, `score.heat`

**✅ 选出代表性策略**（4 个）：
1. **`none`** - 基线，透传原始对话
2. **`extract.triple`** - 结构化提取（TiM/Mem0ᵍ 使用）
3. **`transform.summarize`** - 摘要生成（MemoryBank 风格）
4. **`score.importance`** - 重要性评分（MemoryOS 风格）

**排除理由**：
- `extract.entity/noun/keyword`：与 `triple` 功能重叠，后者更完整
- `transform.segment/chunking`：特定场景，代表性不足
- `score.heat`：与 `importance` 相似，PostInsert 阶段处理更合理

---

##### D3 (PostInsert) - 可用策略总览与筛选

**所有可用策略**（共 7 个）：
- 基础：`none`
- 优化：`distillation`, `crud`, `link_evolution`, `migrate`, `migrate.time_based`, `forgetting`
- 增强：`enhance.profile_extraction`

**✅ 选出代表性策略**（4 个）：
1. **`none`** - 基线，无后处理
2. **`distillation`** - 知识蒸馏/合并（TiM 使用）
3. **`crud`** - LLM 决策式操作（Mem0ᵍ 使用）
4. **`migrate`** - 热度迁移（MemoryOS 使用）

**排除理由**：
- `link_evolution`：图结构专用，通用性不足
- `forgetting`：与 `distillation` 部分重叠
- `migrate.time_based`：是 `migrate` 的特化版本
- `enhance.profile_extraction`：是 `migrate` 的子功能

---

##### D4 (PreRetrieval) - 可用策略总览与筛选

**所有可用策略**（共 9 个）：
- 基础：`none`, `embedding`, `validate`
- 优化：`optimize.keyword_extract`, `optimize.expand`, `optimize.rewrite`
- 增强：`enhancement.decompose`, `enhancement.route`, `enhancement.multi_embed`

**✅ 选出代表性策略**（4 个）：
1. **`embedding`** - 标准向量化（TiM/Mem0ᵍ 使用）
2. **`validate`** - 查询验证（质量保证）
3. **`keyword_extract`** - 关键词提取（MemoryOS 使用）
4. **`decompose`** - 查询分解（复杂推理场景）

**排除理由**：
- `none`：PreRetrieval 至少需要基础处理，无操作意义不大
- `optimize.expand`：容易造成查询冗余，影响检索精度
- `optimize.rewrite`：功能被 `keyword_extract` 覆盖
- `enhancement.route/multi_embed`：过于特异化，适用场景有限

---

##### D5 (PostRetrieval) - 可用策略总览与筛选

**所有可用策略**（共 14 个）：
- 基础：`none`
- 重排序：`rerank.semantic`, `rerank.time_weighted`, `rerank.ppr`, `rerank.weighted`
- 过滤：`filter.token_budget`, `filter.threshold`, `filter.top_k`
- 合并：`merge.link_expand`, `merge.multi_query`, `merge.multi_tier`, `scm_three_way`
- 增强：`augment`, `augment.reinforce`

**✅ 选出代表性策略**（4 个）：
1. **`none`** - 基线，基础格式化
2. **`rerank.weighted`** - 多因子重排（通用性强）
3. **`filter.token_budget`** - Token 控制（实用性强）
4. **`merge.multi_query`** - 多查询合并（MemoryOS 使用）

**排除理由**：
- `rerank.semantic/time_weighted/ppr`：是 `weighted` 的特化版本
- `filter.threshold/top_k`：与 `token_budget` 功能重叠
- `merge.link_expand/multi_tier`：特定场景，代表性不足
- `scm_three_way`：SCM 专用
- `augment/augment.reinforce`：实验性功能，成熟度不足

---

#### 第三步：实验设计方案

**方案 A：论文复现实验**（最小化，3个实验）
- 每个数据结构保持论文原配置不变
- 用于验证 Pipeline 正确性

| 实验ID | D1 | D2 | D3 | D4 | D5 |
|-------|----|----|----|----|-----|
| E1-TiM | `lsh_hash` | `extract.triple` | `distillation` | `embedding` | `none` |
| E2-Mem0g | `semantic_inverted_knowledge_graph` | `extract.triple` | `crud` | `embedding` | `none` |
| E3-MemoryOS | `feature_queue_segment_combination` | `none` | `migrate` | `keyword_extract` | `merge.multi_query` |

---

**方案 B：单维度探索实验**（推荐，48个实验）
- 固定其他维度为论文配置
- 每次只变化一个维度的代表性策略

##### B1: 固定 D3/D4/D5，探索 D2

| 实验组 | D1 | D2 变化 | D3 固定 | D4 固定 | D5 固定 | 实验数 |
|-------|----|---------|---------|---------|---------| ------|
| TiM-D2 | `lsh_hash` | 4种 | `distillation` | `embedding` | `none` | 4 |
| Mem0g-D2 | `semantic_inverted_knowledge_graph` | 4种 | `crud` | `embedding` | `none` | 4 |
| MemoryOS-D2 | `feature_queue_segment_combination` | 4种 | `migrate` | `keyword_extract` | `merge.multi_query` | 4 |

D2 的 4 种策略：`none`, `extract.triple`, `transform.summarize`, `score.importance`

##### B2: 固定 D2/D4/D5，探索 D3

| 实验组 | D1 | D2 固定 | D3 变化 | D4 固定 | D5 固定 | 实验数 |
|-------|----|---------|---------|---------|---------| ------|
| TiM-D3 | `lsh_hash` | `extract.triple` | 4种 | `embedding` | `none` | 4 |
| Mem0g-D3 | `semantic_inverted_knowledge_graph` | `extract.triple` | 4种 | `embedding` | `none` | 4 |
| MemoryOS-D3 | `feature_queue_segment_combination` | `none` | 4种 | `keyword_extract` | `merge.multi_query` | 4 |

D3 的 4 种策略：`none`, `distillation`, `crud`, `migrate`

##### B3: 固定 D2/D3/D5，探索 D4

| 实验组 | D1 | D2 固定 | D3 固定 | D4 变化 | D5 固定 | 实验数 |
|-------|----|---------|---------|---------|---------| ------|
| TiM-D4 | `lsh_hash` | `extract.triple` | `distillation` | 4种 | `none` | 4 |
| Mem0g-D4 | `semantic_inverted_knowledge_graph` | `extract.triple` | `crud` | 4种 | `none` | 4 |
| MemoryOS-D4 | `feature_queue_segment_combination` | `none` | `migrate` | 4种 | `merge.multi_query` | 4 |

D4 的 4 种策略：`embedding`, `validate`, `keyword_extract`, `decompose`

##### B4: 固定 D2/D3/D4，探索 D5

| 实验组 | D1 | D2 固定 | D3 固定 | D4 固定 | D5 变化 | 实验数 |
|-------|----|---------|---------|---------|---------| ------|
| TiM-D5 | `lsh_hash` | `extract.triple` | `distillation` | `embedding` | 4种 | 4 |
| Mem0g-D5 | `semantic_inverted_knowledge_graph` | `extract.triple` | `crud` | `embedding` | 4种 | 4 |
| MemoryOS-D5 | `feature_queue_segment_combination` | `none` | `migrate` | `keyword_extract` | 4种 | 4 |

D5 的 4 种策略：`none`, `rerank.weighted`, `filter.token_budget`, `merge.multi_query`
---

**方案 C：全维度正交实验**（完整探索，不推荐，256个实验）
- 所有维度的代表性策略全排列
- 组合爆炸：4^4 × 3 = 768，筛选后约 256 个有效组合
- 时间成本过高，不推荐

---

### 5.2 推荐实验方案对比

| 方案 | 实验数 | 时间成本 | 适用场景 | 优缺点 |
|------|-------|---------|---------|--------|
| **方案 A** | 3 | 低（~150h） | 论文复现验证 | ✅ 快速验证<br>❌ 无探索价值 |
| **方案 B** | 48 | 中（~2400h） | 单维度深度探索 | ✅ 控制变量清晰<br>✅ 可并行执行<br>✅ 结论可解释 |
| **方案 C** | 256 | 高（~12800h） | 完整参数空间搜索 | ✅ 覆盖全面<br>❌ 时间成本过高<br>❌ 结论难解释 |

**推荐选择**：**方案 B**（单维度探索实验）

### 5.3 方案 B 实验矩阵详情

#### 实验命名规范

```
<数据结构>_<维度>_<策略>
例如：TiM_D2_triple, Mem0g_D5_rerank, MemoryOS_D3_migrate
```

#### B1 组：探索 D2 (PreInsert) - 12 个实验

| ID | 数据结构 | D2 (变化) | D3 (固定) | D4 (固定) | D5 (固定) |
|----|---------|----------|----------|----------|----------|
| B1-1 | TiM | `none` | `distillation` | `embedding` | `none` |
| B1-2 | TiM | `extract.triple` ✅论文 | `distillation` | `embedding` | `none` |
| B1-3 | TiM | `transform.summarize` | `distillation` | `embedding` | `none` |
| B1-4 | TiM | `score.importance` | `distillation` | `embedding` | `none` |
| B1-5 | Mem0ᵍ | `none` | `crud` | `embedding` | `none` |
| B1-6 | Mem0ᵍ | `extract.triple` ✅论文 | `crud` | `embedding` | `none` |
| B1-7 | Mem0ᵍ | `transform.summarize` | `crud` | `embedding` | `none` |
| B1-8 | Mem0ᵍ | `score.importance` | `crud` | `embedding` | `none` |
| B1-9 | MemoryOS | `none` ✅论文 | `migrate` | `keyword_extract` | `merge.multi_query` |
| B1-10 | MemoryOS | `extract.triple` | `migrate` | `keyword_extract` | `merge.multi_query` |
| B1-11 | MemoryOS | `transform.summarize` | `migrate` | `keyword_extract` | `merge.multi_query` |
| B1-12 | MemoryOS | `score.importance` | `migrate` | `keyword_extract` | `merge.multi_query` |

#### B2 组：探索 D3 (PostInsert) - 12 个实验

| ID | 数据结构 | D2 (固定) | D3 (变化) | D4 (固定) | D5 (固定) |
|----|---------|----------|----------|----------|----------|
| B2-1 | TiM | `extract.triple` | `none` | `embedding` | `none` |
| B2-2 | TiM | `extract.triple` | `distillation` ✅论文 | `embedding` | `none` |
| B2-3 | TiM | `extract.triple` | `crud` | `embedding` | `none` |
| B2-4 | TiM | `extract.triple` | `migrate` | `embedding` | `none` |
| B2-5 | Mem0ᵍ | `extract.triple` | `none` | `embedding` | `none` |
| B2-6 | Mem0ᵍ | `extract.triple` | `distillation` | `embedding` | `none` |
| B2-7 | Mem0ᵍ | `extract.triple` | `crud` ✅论文 | `embedding` | `none` |
| B2-8 | Mem0ᵍ | `extract.triple` | `migrate` | `embedding` | `none` |
| B2-9 | MemoryOS | `none` | `none` | `keyword_extract` | `merge.multi_query` |
| B2-10 | MemoryOS | `none` | `distillation` | `keyword_extract` | `merge.multi_query` |
| B2-11 | MemoryOS | `none` | `crud` | `keyword_extract` | `merge.multi_query` |
| B2-12 | MemoryOS | `none` | `migrate` ✅论文 | `keyword_extract` | `merge.multi_query` |

#### B3 组：探索 D4 (PreRetrieval) - 12 个实验

| ID | 数据结构 | D2 (固定) | D3 (固定) | D4 (变化) | D5 (固定) |
|----|---------|----------|----------|----------|----------|
| B3-1 | TiM | `extract.triple` | `distillation` | `embedding` ✅论文 | `none` |
| B3-2 | TiM | `extract.triple` | `distillation` | `validate` | `none` |
| B3-3 | TiM | `extract.triple` | `distillation` | `keyword_extract` | `none` |
| B3-4 | TiM | `extract.triple` | `distillation` | `decompose` | `none` |
| B3-5 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` ✅论文 | `none` |
| B3-6 | Mem0ᵍ | `extract.triple` | `crud` | `validate` | `none` |
| B3-7 | Mem0ᵍ | `extract.triple` | `crud` | `keyword_extract` | `none` |
| B3-8 | Mem0ᵍ | `extract.triple` | `crud` | `decompose` | `none` |
| B3-9 | MemoryOS | `none` | `migrate` | `embedding` | `merge.multi_query` |
| B3-10 | MemoryOS | `none` | `migrate` | `validate` | `merge.multi_query` |
| B3-11 | MemoryOS | `none` | `migrate` | `keyword_extract` ✅论文 | `merge.multi_query` |
| B3-12 | MemoryOS | `none` | `migrate` | `decompose` | `merge.multi_query` |

#### B4 组：探索 D5 (PostRetrieval) - 12 个实验

| ID | 数据结构 | D2 (固定) | D3 (固定) | D4 (固定) | D5 (变化) |
|----|---------|----------|----------|----------|----------|
| B4-1 | TiM | `extract.triple` | `distillation` | `embedding` | `none` ✅论文 |
| B4-2 | TiM | `extract.triple` | `distillation` | `embedding` | `rerank.weighted` |
| B4-3 | TiM | `extract.triple` | `distillation` | `embedding` | `filter.token_budget` |
| B4-4 | TiM | `extract.triple` | `distillation` | `embedding` | `merge.multi_query` |
| B4-5 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` | `none` ✅论文 |
| B4-6 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` | `rerank.weighted` |
| B4-7 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` | `filter.token_budget` |
| B4-8 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` | `merge.multi_query` |
| B4-9 | MemoryOS | `none` | `migrate` | `keyword_extract` | `none` |
| B4-10 | MemoryOS | `none` | `migrate` | `keyword_extract` | `rerank.weighted` |
| B4-11 | MemoryOS | `none` | `migrate` | `keyword_extract` | `filter.token_budget` |
| B4-12 | MemoryOS | `none` | `migrate` | `keyword_extract` | `merge.multi_query` ✅论文 |

### 5.4 实验规模估算

**方案 B 总实验数**：
```
B1 (12) + B2 (12) + B3 (12) + B4 (12) = 48
```

**方案 B 总时间估算**：
```
48 实验 × 50 任务 × 3 小时 ≈ 7200 小时（300 天单线程）
并行执行（10 台机器）：约 30 天
```

### 5.5 实验价值分析

#### 核心研究问题（按实验组）

**B1 组（D2 PreInsert 探索）**：
1. 预处理策略对数据质量的影响
   - 原始对话 vs 结构化提取（三元组）vs 摘要压缩
   - 重要性评分是否能提升后续检索效果
2. 不同数据结构对预处理的敏感度
   - LSH 索引是否需要结构化输入
   - 图谱索引是否必须三元组提取

**B2 组（D3 PostInsert 探索）**：
1. 后处理策略对记忆质量的影响
   - 无后处理 vs 蒸馏合并 vs CRUD 决策 vs 热度迁移
   - 哪种策略更适合长期记忆管理
2. 不同数据结构对后处理的适配性
   - LSH 快速索引是否适合频繁 CRUD
   - 图谱结构是否更适合迁移操作

**B3 组（D4 PreRetrieval 探索）**：
1. 查询优化策略对检索精度的影响
   - 无优化 vs 向量化 vs 关键词提取 vs 查询分解
   - 复杂查询是否需要分解
2. 不同数据结构对查询优化的需求
   - LSH 近似检索是否受益于关键词
   - 三索引融合如何平衡不同查询策略

**B4 组（D5 PostRetrieval 探索）**：
1. 后检索优化对最终效果的影响
   - 无后处理 vs 重排序 vs 过滤 vs 合并
   - Token 控制对长上下文任务的重要性
2. 不同数据结构对后检索优化的响应
   - LSH 近似结果是否需要重排序
   - 多索引融合与多查询合并的协同效应

#### 横向对比价值

**同一维度，不同数据结构**（例如 B4 组）：
- TiM (LSH) + `rerank.weighted`：近似索引能否通过重排提升精度？
- Mem0ᵍ (SIKG) + `rerank.weighted`：图谱检索是否需要重排？
- MemoryOS (FQS) + `rerank.weighted`：三索引融合后重排的边际收益？

**同一数据结构，不同维度**（例如 TiM 的 B1-B4）：
- 哪个维度对 TiM 效果影响最大？
- 是否存在"瓶颈维度"（改进该维度收益最高）？
**每个实验**（以 LoCoMo 数据集为例）：
- 任务数：50+ 个会话
- 每个任务：300-2000 轮对话
- 测试分段：10 次
- 估计时间：2-4 小时/任务

**总时间估算**：
```
20 实验 × 50 任务 × 3 小时 = 3000 小时
（可并行执行，实际时间取决于计算资源）
```

### 5.4 实验价值分析

#### 核心研究问题

1. **PostRetrieval 策略对检索效果的影响**
   - 不同重排序算法的精度差异
   - 过滤策略对上下文质量的影响
   - 合并策略对多源检索的优化效果

2. **数据结构与 PostRetrieval 策略的适配性**
   - LSH（近似）vs 精确索引在重排后的效果
   - 图结构是否能从 `merge.link_expand` 中获益
   - 三索引融合与多层级合并的协同效应

3. **控制变量实验的对比意义**
   - 同一数据结构下，不同 D5 策略的横向对比
   - 不同数据结构下，相同 D5 策略的纵向对比
   - 论文原配置（Baseline）vs 优化配置的改进幅度

### 5.5 实际应用场景映射

| 数据结构 | 典型场景 | 数据规模 | 性能要求 |
|---------|---------|---------|---------|
| TiM (LSH Hash) | 大规模文档检索、快速去重 | 100万+ | 高吞吐量，O(1)近似 |
| Mem0ᵍ (SIKG) | 企业知识库、实体关系推理 | 10万+ | 高精度检索，图遍历 |
| MemoryOS (FQS) | 对话系统、上下文管理 | 1万-10万 | 平衡延迟与精度 |

### 5.6 选择合理性总结

**为什么选择 TiM、Mem0ᵍ、MemoryOS 这 3 个？**

1. **覆盖底层分类**：
   - Partitional（扁平化+索引组合）→ 2个（TiM、MemoryOS）
   - Hierarchical（结构关系+演化）→ 1个（Mem0ᵍ）

2. **覆盖索引复杂度**：
   - 单索引（TiM: LSH）→ 1个
   - 三索引融合（MemoryOS: BM25+FIFO+Segment）→ 1个
   - 三层图谱（Mem0ᵍ: Semantic+Inverted+KG）→ 1个

3. **覆盖论文代表性**：
   - TiM：近似检索范式
   - Mem0ᵍ：图记忆范式
   - MemoryOS：分段管理范式

4. **实验效率优化**：
   - 从 11 个服务缩减到 3 个
   - 从 540 种全排列缩减到 20 种控制变量实验
   - 聚焦 PostRetrieval 策略优化（最接近应用层）

**实验设计原则**：
- ✅ **最小代表集**：3个结构覆盖核心能力
- ✅ **控制变量法**：固定 D2-D4，只变化 D5
- ✅ **最优实验效率**：20 个实验 vs 原 540 个（节省 96% 时间）
- ✅ **论文复现**：保持论文原配置，确保对比公平

---

## 附录

### A. 完整服务列表

**Partitional Services (8个)**:
1. `fifo_queue` ✅ 已选
2. `lsh_hash` ✅ 已选
3. `segment`
4. `inverted_vectorstore_combination`
5. `feature_queue_vectorstore_combination` ✅ 已选
6. `feature_queue_segment_combination`
7. `feature_queue_summary_combination`
8. `feature_summary_vectorstore_combination`

**Hierarchical Services (3个)**:
1. `linknote_graph` ✅ 已选
2. `property_graph`
3. `semantic_inverted_knowledge_graph` ✅ 已选

### B. 相关文档

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Benchmark架构总览
- [Memory_Pipeline_Dev_Archive.md](./Memory_Pipeline_Dev_Archive.md) - Pipeline设计细节
- [Memory_Systems_Comparison.md](./Memory_Systems_Comparison.md) - 论文记忆体对比
- [API_REFERENCE.md](../../../docs/services/API_REFERENCE.md) - Service API文档

---

**文档维护**: 如修改选择策略或新增服务，请同步更新本文档。
