# MemoryDataStructure 数据结构实验设计

> 基于已复现的代表性工作，固定一套通用记忆操作，对不同数据结构进行排列组合测试
>
> 目标：评估不同记忆数据结构在相同操作配置下的性能差异
>
> 实验范围：MemoryService 层（难度★★★★★），固定所有 Operator 为统一配置

______________________________________________________________________

## 📋 数据结构分类体系

### 完整分类

```
NeuroMem Services
├── Partitional（分区型）- 扁平存储 + 多索引组合
│   ├── fifo_queue                           # FIFO时序队列
│   ├── lsh_hash                             # LSH近似向量检索
│   ├── segment                              # 分段管理
│   ├── inverted_vectorstore_combination     # BM25 + FAISS
│   ├── feature_queue_vectorstore_combination # BM25 + FIFO + FAISS
│   ├── feature_queue_segment_combination    # BM25 + FIFO + Segment
│   ├── feature_queue_summary_combination    # BM25 + FIFO + Summary
│   └── feature_summary_vectorstore_combination # BM25 + Summary + FAISS
│
└── Hierarchical（层次型）- 结构关系 + 动态演化
    ├── linknote_graph                       # 双向链接图
    ├── property_graph                       # RDF风格属性图
    └── semantic_inverted_knowledge_graph    # 三层检索：语义→倒排→图谱
```

### 代表性数据结构选取（5选）

基于类内代表性和实验价值，从 11 个服务中选出 5 个：

| 选择 | 服务                                     | 类别         | 索引组合             | 论文      | 选择理由             |
| ---- | ---------------------------------------- | ------------ | -------------------- | --------- | -------------------- |
| ✅   | `fifo_queue`                             | Partitional  | FIFO                 | SCM       | 最简基线，纯时序     |
| ✅   | `lsh_hash`                               | Partitional  | LSH                  | TiM       | 向量索引代表         |
| ✅   | `feature_queue_vectorstore_combination`  | Partitional  | BM25+FIFO+FAISS      | MemGPT    | 三索引融合，混合检索 |
| ✅   | `linknote_graph`                         | Hierarchical | Graph+Vector         | A-Mem     | 简单图基线           |
| ✅   | `semantic_inverted_knowledge_graph`      | Hierarchical | Graph+Inverted+Vector| HippoRAG  | 复杂语义图谱         |

### 技术对比矩阵

| 数据结构                              | 类别         | 索引组合               | 时间复杂度  | 适用规模  | 向量需求 |
| ------------------------------------- | ------------ | ---------------------- | ----------- | --------- | -------- |
| FIFO Queue                            | Partitional  | FIFO                   | O(1)        | <1K       | ❌       |
| LSH Hash                              | Partitional  | LSH                    | O(1)近似    | 1M+       | ✅       |
| Feature-Queue-Vector                  | Partitional  | BM25+FIFO+FAISS        | O(log N)    | 10K-100K  | ✅       |
| Linknote Graph                        | Hierarchical | Graph+Vector           | O(N+E)      | 10K       | 可选     |
| Semantic Inverted KG                  | Hierarchical | Graph+Inverted+Vector  | O(log N)    | 100K+     | ✅       |

______________________________________________________________________

## 1. 统一记忆操作配置

为确保对比公平性，所有数据结构实验使用相同的 Operator 配置：

```yaml
operators:
  # PreInsert: 统一使用三元组提取
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true           # 保留原始文本

  # PreRetrieval: 统一使用 embedding
  pre_retrieval:
    action: embedding

  # PostInsert: 统一使用语义合并
  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  # PostRetrieval: 统一使用时间加权重排序
  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

**选择理由**：
- `extract.triple` + `semantic_consolidation`: 验证结构化信息对不同索引的影响
- `embedding` + `rerank.time_weighted`: 标准的向量检索 + 时间感知重排序

______________________________________________________________________

## 2. 实验配置矩阵

### 2.1 五个数据结构实验

| 配置ID | 配置文件                                     | 内存名称              | 数据结构服务                             | 类别         |
| ------ | -------------------------------------------- | --------------------- | ---------------------------------------- | ------------ |
| **D1** | `locomo_fifo_queue_pipeline.yaml`            | `DS-fifo_queue`       | `partitional.fifo_queue`                 | Partitional  |
| **D2** | `locomo_lsh_hash_pipeline.yaml`              | `DS-lsh_hash`         | `partitional.lsh_hash`                   | Partitional  |
| **D3** | `locomo_feature_queue_vector_pipeline.yaml`  | `DS-fqv_combination`  | `partitional.feature_queue_vectorstore`  | Partitional  |
| **D4** | `locomo_linknote_graph_pipeline.yaml`        | `DS-linknote_graph`   | `hierarchical.linknote_graph`            | Hierarchical |
| **D5** | `locomo_semantic_kg_pipeline.yaml`           | `DS-semantic_kg`      | `hierarchical.semantic_inverted_kg`      | Hierarchical |

**实验总数**: 5 个配置（5 个数据结构 × 1 套统一操作）

______________________________________________________________________

## 3. 配置文件详情

### 3.1 FIFO Queue（最简基线）

```yaml
# locomo_fifo_queue_pipeline.yaml
runtime:
  dataset: locomo
  memory_name: DS-fifo_queue
  memory_insert_verbose: false
  memory_test_verbose: true
  test_segments: 10
  service_timeout: 600.0

  # LLM 配置
  api_key: "iloveshuhao"
  base_url: "http://172.17.0.1:1040/v1"
  model_name: "pangu_embedded_1b"
  max_tokens: 256
  temperature: 0
  seed: 42

  # Embedding 配置
  embedding_base_url: http://localhost:8091/v1
  embedding_model: BAAI/bge-m3

services:
  services_type: "partitional.fifo_queue"
  fifo_queue:
    max_size: 1000               # 队列最大容量
    eviction_policy: "fifo"      # 先进先出淘汰

operators:
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

### 3.2 LSH Hash（向量索引代表）

```yaml
# locomo_lsh_hash_pipeline.yaml
runtime:
  dataset: locomo
  memory_name: DS-lsh_hash
  # ... 其他 runtime 配置同上

services:
  services_type: "partitional.lsh_hash"
  lsh_hash:
    vector_dim: 1024
    lsh_nbits: 128
    lsh_rotate_data: true
    retrieval_top_k: 10

operators:
  # 统一 Operator 配置
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

### 3.3 Feature-Queue-Vectorstore Combination（三索引融合）

```yaml
# locomo_feature_queue_vector_pipeline.yaml
runtime:
  dataset: locomo
  memory_name: DS-fqv_combination
  # ... 其他 runtime 配置同上

services:
  services_type: "partitional.feature_queue_vectorstore_combination"
  feature_queue_vectorstore_combination:
    # FAISS 向量索引配置
    vector_dim: 1024
    faiss_index_type: "IndexFlatIP"

    # BM25 文本索引配置
    bm25_k1: 1.5
    bm25_b: 0.75

    # FIFO 队列配置
    fifo_max_size: 500

    # 融合策略
    fusion_method: "rrf"         # Reciprocal Rank Fusion
    rrf_k: 60

operators:
  # 统一 Operator 配置（同上）
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

### 3.4 Linknote Graph（简单图基线）

```yaml
# locomo_linknote_graph_pipeline.yaml
runtime:
  dataset: locomo
  memory_name: DS-linknote_graph
  # ... 其他 runtime 配置同上

services:
  services_type: "hierarchical.linknote_graph"
  linknote_graph:
    vector_dim: 1024
    enable_bidirectional_links: true
    max_links_per_node: 10
    link_similarity_threshold: 0.7

operators:
  # 统一 Operator 配置（同上）
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

### 3.5 Semantic Inverted Knowledge Graph（复杂语义图谱）

```yaml
# locomo_semantic_kg_pipeline.yaml
runtime:
  dataset: locomo
  memory_name: DS-semantic_kg
  # ... 其他 runtime 配置同上

services:
  services_type: "hierarchical.semantic_inverted_knowledge_graph"
  semantic_inverted_knowledge_graph:
    # 三层检索配置
    vector_dim: 1024

    # 语义层
    semantic_index_type: "faiss"
    semantic_top_k: 50

    # 倒排层
    inverted_index_type: "bm25"
    inverted_top_k: 30

    # 图谱层
    graph_traversal_depth: 2
    ppr_damping: 0.85
    ppr_iterations: 100

operators:
  # 统一 Operator 配置（同上）
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: true

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05
    time_weight: 0.3
    score_weight: 0.7
```

______________________________________________________________________

## 4. 实验执行计划

### 4.1 实验顺序

```
Phase 1: Partitional 基线
├── DS-fifo_queue (最简基线)
├── DS-lsh_hash (向量索引)
└── DS-fqv_combination (三索引融合)

Phase 2: Hierarchical 对比
├── DS-linknote_graph (简单图)
└── DS-semantic_kg (复杂图谱)
```

### 4.2 评估指标

| 指标类别   | 指标名称           | 说明                               |
| ---------- | ------------------ | ---------------------------------- |
| 质量指标   | Accuracy           | 基于检索记忆的回答准确率           |
| 质量指标   | Recall@K           | Top-K 检索的召回率                 |
| 质量指标   | Precision@K        | Top-K 检索的精确率                 |
| 效率指标   | Insert Latency     | 平均插入延迟                       |
| 效率指标   | Retrieve Latency   | 平均检索延迟                       |
| 效率指标   | Memory Usage       | 内存占用                           |
| 可扩展性   | Scale Factor       | 性能随数据量的变化曲线             |

### 4.3 对比维度

| 对比维度       | 对比组合                                     | 预期假设                           |
| -------------- | -------------------------------------------- | ---------------------------------- |
| 简单 vs 复杂   | D1 (FIFO) vs D5 (Semantic KG)                | 复杂结构在复杂查询上表现更好       |
| 向量 vs 混合   | D2 (LSH) vs D3 (FQV)                         | 混合检索在多样化查询上更鲁棒       |
| 扁平 vs 图结构 | D3 (FQV) vs D4 (Linknote)                    | 图结构在关系推理上有优势           |
| 简单图 vs 复杂图 | D4 (Linknote) vs D5 (Semantic KG)          | 复杂图谱在多跳推理上表现更好       |

______________________________________________________________________

## 5. 脚本文件

```
benchmarks/experiment/script/memory_data_structure/
├── run_locomo_fifo_queue.sh
├── run_locomo_lsh_hash.sh
├── run_locomo_feature_queue_vector.sh
├── run_locomo_linknote_graph.sh
└── run_locomo_semantic_kg.sh
```

______________________________________________________________________

## 6. 预期结果假设

### 6.1 性能假设

| 数据结构       | Accuracy | Latency  | 适用场景             |
| -------------- | -------- | -------- | -------------------- |
| FIFO Queue     | ★★☆☆☆   | ★★★★★   | 短期记忆，实时系统   |
| LSH Hash       | ★★★☆☆   | ★★★★☆   | 大规模向量检索       |
| FQV Combination| ★★★★☆   | ★★★☆☆   | 多样化检索需求       |
| Linknote Graph | ★★★☆☆   | ★★★☆☆   | 简单关系推理         |
| Semantic KG    | ★★★★★   | ★★☆☆☆   | 复杂知识推理         |

### 6.2 Trade-off 分析

- **准确率 vs 延迟**：复杂结构准确率高但延迟大
- **灵活性 vs 复杂度**：混合索引更灵活但维护成本高
- **可扩展性 vs 功能**：简单结构更易扩展但功能受限

---

**更新日志**：
- 2026-01-13: 创建数据结构实验设计文档
- 选取 5 个代表性数据结构
- 设计统一的 Operator 配置用于公平对比
