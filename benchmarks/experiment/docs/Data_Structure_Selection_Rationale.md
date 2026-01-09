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

### 5.1 完整性覆盖

**底层分类维度**：
- ✅ Partitional：3/8（37.5%）- 覆盖单索引×2 + 多索引融合×1
- ✅ Hierarchical：2/3（66.7%）- 覆盖简单图 + 复杂图

**复杂度梯度**：
1. **极简**：FIFO（无向量，O(1)）
2. **简单**：LSH（单向量，O(1)近似）
3. **中等**：Feature-Queue-Vector（三索引，O(log N)）
4. **复杂**：Linknote（图+向量，O(N+E)）
5. **最复杂**：Semantic Inverted KG（三层检索，O(log N)）

**论文算法映射**：
- ✅ 5/12 主流论文算法（SCM、TiM、MemGPT、A-Mem、HippoRAG）
- ✅ 覆盖时序、语义、混合、图谱四大范式

### 5.2 实验组合潜力

基于这 5 个数据结构，可以设计以下实验矩阵：

**D1: 数据结构探索**（5 种）
- FIFO vs LSH → 评估"语义检索的必要性"
- LSH vs FAISS → 评估"精确检索 vs 近似检索"
- Feature-Queue-Vector → 评估"融合策略的最优权重"
- Linknote vs Semantic KG → 评估"简单图 vs 复杂图"

**D2: PreInsert 策略**（4 种）
- `none`：透传原始对话
- `extract.entity`：实体提取
- `extract.triple`：三元组提取
- `transform.summarize`：摘要生成

**D3: PostInsert 策略**（3 种）
- `none`：无后处理
- `link_evolution`：链接演化（图结构专用）
- `distillation`：知识蒸馏

**D4: PreRetrieval 策略**（3 种）
- `embedding`：基础向量化
- `optimize.keyword_extract`：关键词提取
- `enhancement.decompose`：查询分解

**D5: PostRetrieval 策略**（3 种）
- `none`：透传检索结果
- `rerank.ppr`：PageRank重排
- `merge.link_expand`：链接扩展

**总组合数**：
```
5 × 4 × 3 × 3 × 3 = 540 种组合
```

通过**控制变量法**，可以从 540 种组合中筛选出最优配置。

### 5.3 实际应用场景映射

| 数据结构 | 典型场景 | 数据规模 | 性能要求 |
|---------|---------|---------|---------|
| FIFO Queue | 客服对话历史、短期上下文 | 10-100条 | 极低延迟（<1ms） |
| LSH Hash | 大规模文档检索、去重 | 100万+ | 高吞吐量 |
| Feature-Queue-Vector | FAQ系统、智能问答 | 1万-10万 | 平衡延迟与精度 |
| Linknote Graph | 知识管理、笔记系统 | 1万-10万 | 关联推荐 |
| Semantic Inverted KG | 企业知识库、复杂推理 | 10万+ | 高精度检索 |

### 5.4 选择合理性总结

**为什么是这 5 个？**

1. **覆盖底层分类**：
   - Partitional（扁平化+索引组合）→ 3个
   - Hierarchical（结构关系+演化）→ 2个

2. **覆盖索引数量维度**：
   - 单索引（FIFO、LSH）→ 2个
   - 多索引（Feature-Queue-Vector）→ 1个
   - 图索引（Linknote、Semantic KG）→ 2个

3. **覆盖复杂度梯度**：
   - 从 O(1) 到 O(N+E)，便于性能对比

4. **覆盖论文算法**：
   - 每个结构都对应明确的论文，实验可复现

5. **实际应用价值**：
   - 都有明确的生产场景，非纯理论构造

**实验设计原则**：
- ✅ 最小代表集：5个结构覆盖11个服务的核心能力
- ✅ 最大对比度：每个结构都有独特的设计特点
- ✅ 最优实验效率：540种组合可通过控制变量法优化

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
