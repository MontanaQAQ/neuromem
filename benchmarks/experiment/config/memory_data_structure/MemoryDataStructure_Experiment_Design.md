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

### 完整数据结构列表（11个）

| 序号 | 服务                                     | 类别         | 索引组合               | 论文来源  | 说明                 |
| ---- | ---------------------------------------- | ------------ | ---------------------- | --------- | -------------------- |
| 1    | `fifo_queue`                             | Partitional  | FIFO                   | SCM       | 最简基线，纯时序     |
| 2    | `lsh_hash`                               | Partitional  | LSH                    | TiM       | 向量索引代表         |
| 3    | `segment`                                | Partitional  | Segment                | -         | 时间窗口分段         |
| 4    | `inverted_vectorstore_combination`       | Partitional  | BM25+FAISS             | Mem0      | 双索引混合检索       |
| 5    | `feature_queue_vectorstore_combination`  | Partitional  | BM25+FIFO+FAISS        | MemGPT    | 三索引融合           |
| 6    | `feature_queue_segment_combination`      | Partitional  | BM25+FIFO+Segment      | -         | 三索引+分段          |
| 7    | `feature_queue_summary_combination`      | Partitional  | BM25+FIFO+Summary      | LDAgent   | 三索引+摘要          |
| 8    | `feature_summary_vectorstore_combination`| Partitional  | BM25+Summary+FAISS     | MemoryBank| 三索引+摘要+向量     |
| 9    | `linknote_graph`                         | Hierarchical | Graph+Vector           | A-Mem     | 简单图基线           |
| 10   | `property_graph`                         | Hierarchical | Property Graph         | Mem0ᵍ     | RDF属性图            |
| 11   | `semantic_inverted_knowledge_graph`      | Hierarchical | Graph+Inverted+Vector  | HippoRAG  | 复杂语义图谱         |

### 技术对比矩阵

| 数据结构                              | 类别         | 索引组合               | 时间复杂度  | 适用规模  | 向量需求 |
| ------------------------------------- | ------------ | ---------------------- | ----------- | --------- | -------- |
| FIFO Queue                            | Partitional  | FIFO                   | O(1)        | <1K       | ❌       |
| LSH Hash                              | Partitional  | LSH                    | O(1)近似    | 1M+       | ✅       |
| Segment                               | Partitional  | Segment                | O(N/S)      | 10K       | 可选     |
| Inverted-Vector                       | Partitional  | BM25+FAISS             | O(log N)    | 10K-100K  | ✅       |
| Feature-Queue-Vector                  | Partitional  | BM25+FIFO+FAISS        | O(log N)    | 10K-100K  | ✅       |
| Feature-Queue-Segment                 | Partitional  | BM25+FIFO+Segment      | O(log N)    | 10K-50K   | 可选     |
| Feature-Queue-Summary                 | Partitional  | BM25+FIFO+Summary      | O(log N)    | 10K-50K   | 可选     |
| Feature-Summary-Vector                | Partitional  | BM25+Summary+FAISS     | O(log N)    | 10K-100K  | ✅       |
| Linknote Graph                        | Hierarchical | Graph+Vector           | O(N+E)      | 10K       | 可选     |
| Property Graph                        | Hierarchical | Property Graph         | O(N+E)      | 10K       | ❌       |
| Semantic Inverted KG                  | Hierarchical | Graph+Inverted+Vector  | O(log N)    | 100K+     | ✅       |

______________________________________________________________________

## 1. 统一记忆操作配置

为确保对比公平性，所有数据结构实验使用**最简单的通用 Operator 配置**：

```yaml
operators:
  # D2 PreInsert: 无预处理，原始数据直接存储
  pre_insert:
    action: "none"

  # D3 PostInsert: 无后处理，不做记忆维护
  post_insert:
    action: "none"

  # D4 PreRetrieval: 统一使用 embedding（向量后端必需）
  pre_retrieval:
    action: "embedding"

  # D5 PostRetrieval: 无后处理，直接返回检索结果
  post_retrieval:
    action: "none"
```

**设计理由**：
- **公平性**: 所有后端在相同条件下比较，性能差异直接反映数据结构本身特性
- **可解释性**: 不引入 D2-D5 的干扰因素，专注于 D1 (Memory Service) 的对比
- **通用性**: 所有后端都能支持这些操作（embedding 是向量后端的基本需求）
- **符合 Phase E 设计**: 实验指南中 Phase E 明确要求比较"fundamental architectural approaches"

______________________________________________________________________

## 2. 实验配置矩阵

### 2.1 完整数据结构实验（11个）

| 配置ID | 配置文件                                      | 内存名称                | 数据结构服务                                      | 类别         |
| ------ | --------------------------------------------- | ----------------------- | ------------------------------------------------- | ------------ |
| **D01** | `locomo_fifo_queue_pipeline.yaml`            | `DS_fifo_queue`         | `partitional.fifo_queue`                          | Partitional  |
| **D02** | `locomo_lsh_hash_pipeline.yaml`              | `DS_lsh_hash`           | `partitional.lsh_hash`                            | Partitional  |
| **D03** | `locomo_segment_pipeline.yaml`               | `DS_segment`            | `partitional.segment`                             | Partitional  |
| **D04** | `locomo_inverted_vectorstore_pipeline.yaml`  | `DS_inverted_vectorstore`| `partitional.inverted_vectorstore_combination`   | Partitional  |
| **D05** | `locomo_feature_queue_vector_pipeline.yaml`  | `DS_fqv_combination`    | `partitional.feature_queue_vectorstore_combination`| Partitional  |
| **D06** | `locomo_feature_queue_segment_pipeline.yaml` | `DS_fqs_combination`    | `partitional.feature_queue_segment_combination`   | Partitional  |
| **D07** | `locomo_feature_queue_summary_pipeline.yaml` | `DS_fqsum_combination`  | `partitional.feature_queue_summary_combination`   | Partitional  |
| **D08** | `locomo_feature_summary_vector_pipeline.yaml`| `DS_fsv_combination`    | `partitional.feature_summary_vectorstore_combination`| Partitional  |
| **D09** | `locomo_linknote_graph_pipeline.yaml`        | `DS_linknote_graph`     | `hierarchical.linknote_graph`                     | Hierarchical |
| **D10** | `locomo_property_graph_pipeline.yaml`        | `DS_property_graph`     | `hierarchical.property_graph`                     | Hierarchical |
| **D11** | `locomo_semantic_kg_pipeline.yaml`           | `DS_semantic_kg`        | `hierarchical.semantic_inverted_knowledge_graph`  | Hierarchical |

**实验总数**: 11 个配置（11 个数据结构 × 1 套统一操作）

______________________________________________________________________

## 3. 配置文件详情

### 3.1 统一 Operator 配置（所有服务共用）

```yaml
operators:
  pre_insert:
    action: "none"

  post_insert:
    action: "none"

  pre_retrieval:
    action: "embedding"

  post_retrieval:
    action: "none"
```

### 3.2 Partitional 类服务配置

#### D01: FIFO Queue（最简基线）
```yaml
services:
  services_type: "partitional.fifo_queue"
  fifo_queue:
    max_size: 1000
    eviction_policy: "fifo"
```

#### D02: LSH Hash（向量索引代表）
```yaml
services:
  services_type: "partitional.lsh_hash"
  lsh_hash:
    vector_dim: 1024
    lsh_nbits: 128
    lsh_rotate_data: true
    retrieval_top_k: 10
```

#### D03: Segment（分段管理）
```yaml
services:
  services_type: "partitional.segment"
  segment:
    segment_strategy: "time"
    time_window: 3600
    max_segment_size: 100
```

#### D04: Inverted-Vectorstore（双索引）
```yaml
services:
  services_type: "partitional.inverted_vectorstore_combination"
  inverted_vectorstore_combination:
    vector_dim: 1024
    fusion_strategy: "rrf"
    rrf_k: 60
```

#### D05: Feature-Queue-Vectorstore（三索引）
```yaml
services:
  services_type: "partitional.feature_queue_vectorstore_combination"
  feature_queue_vectorstore_combination:
    vector_dim: 1024
    faiss_index_type: "IndexFlatIP"
    bm25_k1: 1.5
    bm25_b: 0.75
    fifo_max_size: 500
    fusion_method: "rrf"
    rrf_k: 60
```

#### D06: Feature-Queue-Segment（三索引+分段）
```yaml
services:
  services_type: "partitional.feature_queue_segment_combination"
  feature_queue_segment_combination:
    fifo_max_size: 100
    segment_strategy: "time"
    segment_threshold: 3600
    enable_feature_extraction: true
    combination_strategy: "weighted"
```

#### D07: Feature-Queue-Summary（三索引+摘要）
```yaml
services:
  services_type: "partitional.feature_queue_summary_combination"
  feature_queue_summary_combination:
    fifo_max_size: 100
    summary_max_size: 20
    summary_min_length: 10
    enable_feature_extraction: true
    enable_summary_generation: true
```

#### D08: Feature-Summary-Vectorstore（三索引）
```yaml
services:
  services_type: "partitional.feature_summary_vectorstore_combination"
  feature_summary_vectorstore_combination:
    vector_dim: 1024
    summary_max_size: 50
    combination_strategy: "weighted"
    enable_feature_extraction: true
    enable_summary_generation: true
```

### 3.3 Hierarchical 类服务配置

#### D09: Linknote Graph（简单图基线）
```yaml
services:
  services_type: "hierarchical.linknote_graph"
  linknote_graph:
    vector_dim: 1024
    enable_bidirectional_links: true
    max_links_per_node: 10
    link_similarity_threshold: 0.7
```

#### D10: Property Graph（属性图）
```yaml
services:
  services_type: "hierarchical.property_graph"
  property_graph:
    directed: true
```

#### D11: Semantic Inverted Knowledge Graph（复杂语义图谱）
```yaml
services:
  services_type: "hierarchical.semantic_inverted_knowledge_graph"
  semantic_inverted_knowledge_graph:
    vector_dim: 1024
    semantic_index_type: "faiss"
    semantic_top_k: 50
    inverted_index_type: "bm25"
    inverted_top_k: 30
    hierarchy_levels: 3
    routing_strategy: "parallel"
    enable_cross_layer_query: true
    max_hops: 3
```

______________________________________________________________________

## 4. 实验执行计划

### 4.1 实验顺序

```
Phase 1: Partitional 基线（8个）
├── D01: fifo_queue (最简基线)
├── D02: lsh_hash (向量索引)
├── D03: segment (分段管理)
├── D04: inverted_vectorstore (双索引)
├── D05: feature_queue_vectorstore (三索引)
├── D06: feature_queue_segment (三索引+分段)
├── D07: feature_queue_summary (三索引+摘要)
└── D08: feature_summary_vectorstore (三索引+摘要+向量)

Phase 2: Hierarchical 对比（3个）
├── D09: linknote_graph (简单图)
├── D10: property_graph (属性图)
└── D11: semantic_inverted_kg (复杂图谱)
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

| 对比维度         | 对比组合                                              | 预期假设                           |
| ---------------- | ----------------------------------------------------- | ---------------------------------- |
| 简单 vs 复杂     | D01 (FIFO) vs D11 (Semantic KG)                       | 复杂结构在复杂查询上表现更好       |
| 单索引 vs 双索引 | D02 (LSH) vs D04 (Inverted-Vector)                    | 双索引在多样化查询上更鲁棒         |
| 双索引 vs 三索引 | D04 (Inverted-Vector) vs D05 (FQV)                    | 三索引融合有更好召回率             |
| 扁平 vs 图结构   | D05 (FQV) vs D09 (Linknote)                           | 图结构在关系推理上有优势           |
| 简单图 vs 属性图 | D09 (Linknote) vs D10 (Property)                      | 属性图在复杂属性查询上更灵活       |
| 简单图 vs 复杂图 | D09 (Linknote) vs D11 (Semantic KG)                   | 复杂图谱在多跳推理上表现更好       |
| 分段 vs 摘要     | D06 (FQ-Segment) vs D07 (FQ-Summary)                  | 摘要更适合长文本压缩场景           |

______________________________________________________________________

## 5. 脚本文件

```
benchmarks/experiment/script/memory_data_structure/
├── run_all_data_structure.sh                          # 批量运行所有实验
├── run_DataStructure_fifo_queue.sh                    # D01
├── run_DataStructure_lsh_hash.sh                      # D02
├── run_DataStructure_segment.sh                       # D03
├── run_DataStructure_inverted_vectorstore.sh          # D04
├── run_DataStructure_feature_queue_vectorstore.sh     # D05
├── run_DataStructure_feature_queue_segment.sh         # D06
├── run_DataStructure_feature_queue_summary.sh         # D07
├── run_DataStructure_feature_summary_vectorstore.sh   # D08
├── run_DataStructure_linknote_graph.sh                # D09
├── run_DataStructure_property_graph.sh                # D10
└── run_DataStructure_semantic_inverted_kg.sh          # D11
```

______________________________________________________________________

## 6. 预期结果假设

### 6.1 性能假设

| 数据结构              | Accuracy | Latency  | 适用场景                   |
| --------------------- | -------- | -------- | -------------------------- |
| FIFO Queue            | ★★☆☆☆   | ★★★★★   | 短期记忆，实时系统         |
| LSH Hash              | ★★★☆☆   | ★★★★☆   | 大规模向量检索             |
| Segment               | ★★★☆☆   | ★★★★☆   | 对话历史按时间窗口检索     |
| Inverted-Vector       | ★★★★☆   | ★★★☆☆   | 混合检索（精确+语义）      |
| Feature-Queue-Vector  | ★★★★☆   | ★★★☆☆   | 多样化检索需求             |
| Feature-Queue-Segment | ★★★☆☆   | ★★★☆☆   | 分段+时序检索              |
| Feature-Queue-Summary | ★★★☆☆   | ★★★☆☆   | 长对话压缩                 |
| Feature-Summary-Vector| ★★★★☆   | ★★☆☆☆   | 摘要+语义混合检索          |
| Linknote Graph        | ★★★☆☆   | ★★★☆☆   | 简单关系推理               |
| Property Graph        | ★★★★☆   | ★★★☆☆   | 属性查询、知识图谱         |
| Semantic KG           | ★★★★★   | ★★☆☆☆   | 复杂知识推理、多跳检索     |

### 6.2 Trade-off 分析

- **准确率 vs 延迟**：复杂结构准确率高但延迟大
- **灵活性 vs 复杂度**：混合索引更灵活但维护成本高
- **可扩展性 vs 功能**：简单结构更易扩展但功能受限
- **存储 vs 性能**：摘要减少存储但可能丢失细节

---

**更新日志**：
- 2026-01-17: 扩展为完整的 11 个数据结构实验
  - 添加 Segment, Inverted-Vector, FQ-Segment, FQ-Summary, FS-Vector, Property Graph
  - 简化统一 Operator 配置为 D2=none, D3=none, D4=embedding, D5=none
  - 目的：专注于 D1 (Memory Service) 的公平对比
- 2026-01-13: 创建数据结构实验设计文档
  - 选取 5 个代表性数据结构
  - 设计统一的 Operator 配置用于公平对比
