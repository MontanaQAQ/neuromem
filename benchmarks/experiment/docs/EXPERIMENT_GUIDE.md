# NeuroMem Benchmark 实验指南

> **版本**: v2.0  
> **更新**: 2026-01-13  
> **目标**: 基于五维排列组合的记忆体实验设计与执行指南

---

## 📋 目录

1. [核心架构](#核心架构)
2. [五维实验框架](#五维实验框架)
3. [数据结构分类](#数据结构分类)
4. [实验配置](#实验配置)
5. [快速开始](#快速开始)

---

## 核心架构

### 记忆操作流程

```
Query → PreRetrieval → Retrieve → PostRetrieval → Response
Data → PreInsert → Insert → PostInsert → Storage
```

### 五个维度（D1-D5）

| 维度 | 名称 | 职责 | 难度 |
|------|------|------|------|
| D1 | MemoryService | 底层数据结构与索引 | ★★★★★ |
| D2 | PreInsert | 插入前内容转换 | ★★★☆☆ |
| D3 | PostInsert | 插入后维护策略 | ★★★★☆ |
| D4 | PreRetrieval | 查询前优化 | ★☆☆☆☆ |
| D5 | PostRetrieval | 检索后加工 | ★★☆☆☆ |

---

## 五维实验框架

### D1: MemoryService（数据结构）

**分类体系**：

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

**论文映射**：

| 服务 | 论文 | 核心特性 |
|------|------|---------|
| `fifo_queue` | SCM | FIFO滑动窗口 |
| `lsh_hash` | TiM | LSH近似检索 |
| `feature_queue_vectorstore_combination` | MemGPT | 混合检索+RRF融合 |
| `feature_queue_segment_combination` | MemoryOS | 热度分段 |
| `feature_queue_summary_combination` | LDAgent | 话题重叠检索 |
| `feature_summary_vectorstore_combination` | MemoryBank | 遗忘曲线 |
| `inverted_vectorstore_combination` | Mem0 | 文本+语义双检索 |
| `linknote_graph` | A-Mem | 链接演化 |
| `property_graph` | Mem0ᵍ | 三元组知识图谱 |
| `semantic_inverted_knowledge_graph` | HippoRAG | PPR图检索 |

---

### D2: PreInsert（插入前处理）

**注册名称**: `pre_insert.action`

| Action | 功能 | 论文 |
|--------|------|------|
| `none` | 原样插入 | - |
| `transform.summarize` | 事件摘要生成 | MemoryBank |
| `transform.chunking` | 文本分块 | - |
| `extract.triple` | 三元组提取 | TiM, Mem0ᵍ |
| `extract.entity` | 实体识别 | - |
| `score.importance` | 重要度打分 | - |
| `score.heat` | 热度计算 | MemoryOS |

**配置示例**：

```yaml
operators:
  pre_insert:
    action: "extract.triple"
    extraction_method: "llm"
    max_triplets: 10
    keep_original: false
```

---

### D3: PostInsert（插入后维护）

**策略分类**：

```
post_insert/
├── conflict_resolution/     # 冲突解决
│   ├── llm_crud            # Mem0: LLM驱动的CRUD决策
│   └── semantic_consolidation  # TiM: 语义整理(矛盾删除+合并)
│
├── decay_eviction/          # 衰减淘汰
│   ├── forgetting_curve    # MemoryBank: Ebbinghaus曲线
│   └── time_decay          # LDAgent: 超时删除
│
├── structure_enrichment/    # 结构增强
│   ├── link_evolution      # A-Mem: 语义链接生成
│   └── graph_construction  # HippoRAG: 同义词边构建
│
└── tier_migration/          # 层级迁移
    └── heat_migration      # MemoryOS: 热度驱动迁移
```

**注册名称**: `post_insert.action`

| Action | 策略类型 | 论文 |
|--------|---------|------|
| `none` | 无操作 | - |
| `conflict_resolution.llm_crud` | 冲突解决 | Mem0 |
| `conflict_resolution.semantic_consolidation` | 冲突解决 | TiM |
| `decay_eviction.forgetting_curve` | 衰减淘汰 | MemoryBank |
| `decay_eviction.time_decay` | 衰减淘汰 | LDAgent |
| `structure_enrichment.link_evolution` | 结构增强 | A-Mem |
| `structure_enrichment.graph_construction` | 结构增强 | HippoRAG |
| `structure_enrichment.heat_migration` | 层级迁移 | MemoryOS |

**配置示例**：

```yaml
operators:
  post_insert:
    action: "decay_eviction.forgetting_curve"
    decay_rate: 0.01
    min_strength: 0.1
    only_on_session_end: true
```

---

### D4: PreRetrieval（查询前优化）

**注册名称**: `pre_retrieval.action`

| Action | 功能 | 论文 |
|--------|------|------|
| `none` | 直接检索 | - |
| `embedding` | 查询向量化 | 标准RAG |
| `validate` | 查询质量验证 | - |
| `keyword_extract` | 关键词提取 | MemoryOS |
| `optimize.rewrite` | 查询改写 | - |
| `optimize.expand` | 关键词扩展 | - |
| `enhancement.decompose` | 复杂查询分解 | - |
| `enhancement.multi_embed` | 多视角向量化 | - |
| `enhancement.route` | 查询路由 | - |

**配置示例**：

```yaml
operators:
  pre_retrieval:
    action: "keyword_extract"
    max_keywords: 5
```

---

### D5: PostRetrieval（检索后加工）

**注册名称**: `post_retrieval.action`

| Action | 功能 | 论文 |
|--------|------|------|
| `none` | 直通 | - |
| `rerank.time_weighted` | 时间加权重排 | MemoryBank |
| `rerank.recency` | 近期优先 | - |
| `rerank.llm` | LLM重排序 | - |
| `filter.threshold` | 阈值过滤 | Mem0 |
| `merge.simple` | 简单合并 | - |
| `merge.multi_query` | 多层检索合并 | MemoryOS |
| `merge.link_expand` | 链接扩展 | A-Mem |

**配置示例**：

```yaml
operators:
  post_retrieval:
    action: "rerank.time_weighted"
    decay_rate: 0.05
    enable_reinforcement: true
```

---

## 数据结构分类

### 代表性数据结构（5选）

基于类内代表性和实验价值，从11个服务中选出5个：

| 选择 | 服务 | 类别 | 索引 | 论文 | 理由 |
|------|------|------|------|------|------|
| ✅ | `fifo_queue` | Partitional | FIFO | SCM | 最简基线，纯时序 |
| ✅ | `lsh_hash` | Partitional | LSH | TiM | 向量索引代表 |
| ✅ | `feature_queue_vectorstore_combination` | Partitional | BM25+FIFO+FAISS | MemGPT | 三索引融合 |
| ✅ | `linknote_graph` | Hierarchical | Graph+Vector | A-Mem | 简单图基线 |
| ✅ | `semantic_inverted_knowledge_graph` | Hierarchical | Graph+Inverted+Vector | HippoRAG | 复杂语义图谱 |

### 技术对比矩阵

| 数据结构 | 类别 | 索引组合 | 时间复杂度 | 适用规模 | 向量需求 |
|---------|------|---------|-----------|---------|---------|
| FIFO Queue | Partitional | FIFO | O(1) | <1K | ❌ |
| LSH Hash | Partitional | LSH | O(1)近似 | 1M+ | ✅ |
| Feature-Queue-Vector | Partitional | BM25+FIFO+FAISS | O(log N) | 10K-100K | ✅ |
| Linknote Graph | Hierarchical | Graph+Vector | O(N+E) | 10K | 可选 |
| Semantic Inverted KG | Hierarchical | Graph+Inverted+Vector | O(log N) | 100K+ | ✅ |

---

## 实验配置

### 分阶段实验设计

**原则**：从最简单维度开始，逐步增加复杂度

```
Phase A: PreRetrieval 扫描（难度★☆☆☆☆）
├── 固定: D2=none, D3=none, D5=none, D1=fifo_queue
└── 变化: D4 ∈ {none, embedding, validate, keyword_extract, decompose}

Phase B: PostRetrieval 引入（难度★★☆☆☆）
├── 固定: D4=<A优胜>, D2=none, D3=none, D1=fifo_queue
└── 变化: D5 ∈ {none, rerank.time_weighted, filter.threshold}

Phase C: PreInsert 引入（难度★★★☆☆）
├── 固定: D4=<A优胜>, D5=<B优胜>, D3=none, D1=fifo_queue
└── 变化: D2 ∈ {none, transform.summarize, extract.triple}

Phase D: PostInsert 引入（难度★★★★☆）
├── 固定: D4=<A优胜>, D5=<B优胜>, D2=<C优胜>, D1=fifo_queue
└── 变化: D3 ∈ {none, decay_eviction.forgetting_curve, conflict_resolution.llm_crud}

Phase E: MemoryService 替换（难度★★★★★）
├── 固定: D4/D5/D2/D3使用A-D优胜组合
└── 变化: D1 ∈ {fifo_queue, lsh_hash, feature_queue_vectorstore_combination, linknote_graph, semantic_inverted_knowledge_graph}
```

### 配置文件命名

**格式**：`{System}_{Dataset}_{Dimension}_pipeline.yaml`

**示例**：
- `TiM_locomo_embedding_pre_retrieval_pipeline.yaml`
- `Mem0g_locomo_validate_pre_retrieval_pipeline.yaml`
- `MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml`

**目录结构**：

```
benchmarks/experiment/config/
├── primitive_memory_model/           # 论文原始配置（13个）
│   ├── locomo_scm_pipeline.yaml
│   ├── locomo_tim_pipeline.yaml
│   ├── locomo_mem0_pipeline.yaml
│   ├── locomo_mem0g_pipeline.yaml
│   ├── locomo_memgpt_pipeline.yaml
│   ├── locomo_memorybank_pipeline.yaml
│   ├── locomo_memoryos_pipeline.yaml
│   ├── locomo_ldagent_pipeline.yaml
│   ├── locomo_secom_pipeline.yaml
│   ├── locomo_amem_pipeline.yaml
│   ├── locomo_hipporag_pipeline.yaml
│   └── locomo_hipporag2_pipeline.yaml
│
├── query_formulation_strategy/       # D4实验（12个）
│   ├── TiM_locomo_embedding_pre_retrieval_pipeline.yaml
│   ├── TiM_locomo_validate_pre_retrieval_pipeline.yaml
│   ├── Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml
│   └── ...
│
├── result_optimization_strategy/     # D5实验
├── normalization_strategy/           # D2实验
├── consolidation_policy/             # D3实验
└── memory_data_structure/            # D1实验
```

---

## 快速开始

### 1. 运行单个实验

```bash
# 使用配置文件
python benchmarks/experiment/memory_test_pipeline.py \
  --config config/primitive_memory_model/locomo_tim_pipeline.yaml \
  --task_id conv-26

# 使用脚本
bash benchmarks/experiment/script/query_formulation_strategy/run_tim_locomo_embedding.sh
```

### 2. 批量运行

```bash
# Phase A: PreRetrieval扫描
for strategy in embedding validate keyword_extract decompose; do
  python memory_test_pipeline.py \
    --config config/query_formulation_strategy/TiM_locomo_${strategy}_pre_retrieval_pipeline.yaml \
    --task_id conv-26
done
```

### 3. 配置文件模板

```yaml
runtime:
  dataset: "locomo"
  memory_name: "TiM-embedding"
  embedding_base_url: "http://localhost:8091/v1"
  embedding_model: "BAAI/bge-m3"

services:
  services_type: "partitional.lsh_hash"
  lsh_hash:
    embedding_dim: 1024
    num_tables: 10
    hash_size: 128
  memory_retrieval_adapter: "none"

operators:
  pre_insert:
    action: "extract.triple"
    extraction_method: "llm"

  post_insert:
    action: "conflict_resolution.semantic_consolidation"

  pre_retrieval:
    action: "embedding"

  post_retrieval:
    action: "none"
```

### 4. 查看结果

```bash
# 日志路径
.sage/output/benchmarks/benchmark_memory/{dataset}/{date}/{memory_name}/

# 分析工具
python benchmarks/experiment/tools/analyze_results.py \
  --memory_name TiM-embedding \
  --dataset locomo
```

---

## 附录

### A. 完整Action注册表

**PostInsert**:
```python
# 查看所有已注册action
from benchmarks.experiment.libs.post_insert.registry import PostInsertActionRegistry
print(PostInsertActionRegistry.list_actions())
# ['none', 'conflict_resolution.llm_crud', 'conflict_resolution.semantic_consolidation',
#  'decay_eviction.forgetting_curve', 'decay_eviction.time_decay',
#  'structure_enrichment.link_evolution', 'structure_enrichment.graph_construction',
#  'structure_enrichment.heat_migration']
```

**PreRetrieval**:
```python
from benchmarks.experiment.libs.pre_retrieval.registry import PreRetrievalActionRegistry
print(PreRetrievalActionRegistry.list_actions())
# ['none', 'embedding', 'validate', 'keyword_extract', 'optimize.rewrite',
#  'optimize.expand', 'enhancement.decompose', 'enhancement.multi_embed',
#  'enhancement.route']
```

### B. 数据集说明

| 数据集 | 对话数 | 平均轮次 | 问题数 | 特点 |
|--------|--------|---------|--------|------|
| Locomo | 100 | 20-30 | 500 | 长对话，多任务 |
| LongMemEval | - | - | - | 待补充 |

### C. 评估指标

- **准确率**: 答案正确性
- **延迟**: 检索+生成时间
- **存储效率**: 存储空间占用
- **可扩展性**: 性能随数据量变化

---

**更新日志**：
- 2026-01-13: 基于当前代码实现创建v2.0版本
- 移除过时的配置和命名
- 整合五维实验框架
- 添加完整的Action注册表
