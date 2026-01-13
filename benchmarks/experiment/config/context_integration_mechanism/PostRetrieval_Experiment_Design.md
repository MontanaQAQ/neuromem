# PostRetrieval 结果优化策略实验设计

> 基于已复现的代表性工作，针对三个记忆体结构设计 PostRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估结果优化策略对最终输出质量的影响
>
> 实验范围：PostRetrieval 阶段（难度★★☆☆☆），固定其他阶段为对应系统的 baseline 配置

______________________________________________________________________

## 📋 PostRetrieval 策略分类体系

本实验采用以下统一的策略分类标准，按功能类型分类：

| 类别                      | 策略名称               | 功能定位                                  | 代表系统                  |
| ------------------------- | ---------------------- | ----------------------------------------- | ------------------------- |
| **1. 透传 (None)**        | `none`                 | 原样透传检索结果，不做任何处理            | Baseline                  |
| **2. 重排序 (Rerank)**    | `rerank.semantic`      | 使用 embedding 重新计算语义相似度         | 通用                      |
|                           | `rerank.time_weighted` | 结合时间衰减因子调整分数                  | MemoryBank, 对话系统      |
|                           | `rerank.ppr`           | 基于图结构的 PageRank 重排序              | HippoRAG                  |
|                           | `rerank.weighted`      | 多因子综合加权（相似度+时间+重要性）      | LD-Agent, 综合系统        |
| **3. 过滤 (Filter)**      | `filter.threshold`     | 按相似度阈值过滤低质量结果                | Mem0                      |
|                           | `filter.token_budget`  | 按 token 预算限制返回数量                 | SCM                       |
|                           | `filter.top_k`         | 保留 Top-K 结果                           | 通用                      |
| **4. 合并 (Merge)**       | `merge.link_expand`    | 扩展图节点的邻居节点                      | A-Mem                     |
|                           | `merge.multi_query`    | 融合多个查询的检索结果                    | MemoryOS                  |
|                           | `merge.multi_tier`     | 融合多层记忆                              | MemGPT                    |
|                           | `scm_three_way`        | 三路合并（User+Task+Conversation）        | SCM                       |
| **5. 增强 (Augment)**     | `augment`              | 添加 persona/traits/summary 等上下文      | MemoryBank, MemoryOS      |
|                           | `augment.reinforce`    | 更新被检索记忆的强度                      | MemoryBank                |

**典型策略选取原则（每类1个）**：

| 策略类别       | 选取的典型策略         | 选取理由                           |
| -------------- | ---------------------- | ---------------------------------- |
| 透传           | `none`                 | 唯一选项，作为基线                 |
| 重排序         | `rerank.time_weighted` | 时间因素在对话记忆中普遍重要       |
| 过滤           | `filter.threshold`     | 最通用的过滤策略                   |
| 合并           | `merge.link_expand`    | 图结构增强，适合验证结构化效果     |
| 增强           | `augment`              | 通用增强策略                       |

______________________________________________________________________

## ⚠️ 重要架构约束

### PostRetrieval 策略与服务的兼容性

| Action              | 依赖的服务类型                    | 约束说明                                                 |
| ------------------- | --------------------------------- | -------------------------------------------------------- |
| `merge.multi_tier`  | `hierarchical_memory`             | ❌ 必须有分层服务（Core/Archival/Recall 或 STM/MTM/LTM） |
| `merge.link_expand` | `graph_memory` 或 `hybrid_memory` | ❌ 必须有图结构，才能扩展邻居节点                        |
| `rerank.ppr`        | `graph_memory` 或 `hybrid_memory` | ❌ 必须有图结构，才能运行 PageRank                       |
| `augment.reinforce` | 支持 `update_memory_strength()`   | ❌ 服务必须实现记忆强化接口                              |
| 其他策略            | 任意                              | ✅ 通用策略，适用于所有结构                              |

### 当前实现限制

**Operator Pipeline 不支持多 Action 组合**：

当前 operator.py 只支持单个 action，理想的 Pipeline 组合暂不可用：
- 理想架构：`actions: ["rerank.time_weighted", "filter.threshold", "augment"]`
- 当前实现：只能选择一个 action

**解决方案**：
- **短期**：每个实验只测试单一 action 的效果
- **长期**：实现 Pipeline 支持，允许 action 组合

______________________________________________________________________

## 1. 三个代表性记忆体结构选取

### 1.1 向量数据库结构 - TiM

**代表工作**: `locomo_tim_pipeline.yaml`
**架构特点**: LSH哈希桶 + 向量检索
**固定配置**:
- `pre_insert: extract.triple`
- `pre_retrieval: embedding`
- `post_insert: conflict_resolution.semantic_consolidation`

**适合测试的 PostRetrieval 策略**：
- `none`: 无后处理基线
- `rerank.time_weighted`: 时间加权重排序
- `filter.threshold`: 阈值过滤

### 1.2 多层结构 - MemoryOS

**代表工作**: `locomo_memoryos_pipeline.yaml`
**架构特点**: STM/MTM/LTM 三层 + 热度评分 + 主动迁移
**固定配置**:
- `pre_insert: score.heat`
- `pre_retrieval: embedding`
- `post_insert: tier_migration.heat_migration`

**适合测试的 PostRetrieval 策略**：
- `none`: 无后处理基线
- `rerank.time_weighted`: 时间加权重排序
- `augment`: 添加 persona 信息

### 1.3 图结构 - Mem0ᵍ

**代表工作**: `locomo_mem0g_pipeline.yaml`
**架构特点**: 向量 + 知识图谱 + 实体链接
**固定配置**:
- `pre_insert: extract.triple`
- `pre_retrieval: embedding`
- `post_insert: conflict_resolution.semantic_consolidation`

**适合测试的 PostRetrieval 策略**：
- `none`: 无后处理基线
- `merge.link_expand`: 扩展图节点邻居（A-Mem 策略）
- `filter.threshold`: 阈值过滤

______________________________________________________________________

## 2. 实验配置矩阵

### 2.1 TiM 系列实验

| 配置ID | 配置文件                                                 | 内存名称                      | PostRetrieval 策略     |
| ------ | -------------------------------------------------------- | ----------------------------- | ---------------------- |
| **T1** | `TiM_locomo_none_post_retrieval_pipeline.yaml`           | `TiM-postretrieval-none`      | `none`                 |
| **T2** | `TiM_locomo_time_weighted_post_retrieval.yaml`           | `TiM-postretrieval-timeweight`| `rerank.time_weighted` |
| **T3** | `TiM_locomo_threshold_post_retrieval.yaml`               | `TiM-postretrieval-threshold` | `filter.threshold`     |

### 2.2 MemoryOS 系列实验

| 配置ID | 配置文件                                                    | 内存名称                           | PostRetrieval 策略     |
| ------ | ----------------------------------------------------------- | ---------------------------------- | ---------------------- |
| **M1** | `MemoryOS_locomo_none_post_retrieval_pipeline.yaml`         | `MemoryOS-postretrieval-none`      | `none`                 |
| **M2** | `MemoryOS_locomo_time_weighted_post_retrieval.yaml`         | `MemoryOS-postretrieval-timeweight`| `rerank.time_weighted` |
| **M3** | `MemoryOS_locomo_augment_post_retrieval.yaml`               | `MemoryOS-postretrieval-augment`   | `augment`              |

### 2.3 Mem0ᵍ 系列实验

| 配置ID | 配置文件                                                  | 内存名称                         | PostRetrieval 策略   |
| ------ | --------------------------------------------------------- | -------------------------------- | -------------------- |
| **G1** | `Mem0g_locomo_none_post_retrieval_pipeline.yaml`          | `Mem0g-postretrieval-none`       | `none`               |
| **G2** | `Mem0g_locomo_link_expand_post_retrieval.yaml`            | `Mem0g-postretrieval-linkexpand` | `merge.link_expand`  |
| **G3** | `Mem0g_locomo_threshold_post_retrieval.yaml`              | `Mem0g-postretrieval-threshold`  | `filter.threshold`   |

**实验总数**: 9 个配置（3 个记忆体 × 3 个策略）

______________________________________________________________________

## 3. 配置文件详情

### 3.1 TiM + time_weighted 配置

```yaml
# TiM_locomo_time_weighted_post_retrieval.yaml
runtime:
  dataset: locomo
  memory_name: TiM-postretrieval-timeweight
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
  services_type: "partitional.lsh_hash"
  lsh_hash:
    vector_dim: 1024
    lsh_nbits: 128
    retrieval_top_k: 10

operators:
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10
    keep_original: false

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: rerank.time_weighted
    decay_rate: 0.05             # 时间衰减系数
    time_weight: 0.3             # 时间因子权重
    score_weight: 0.7            # 原始分数权重
    enable_reinforcement: true   # 是否更新记忆强度
```

### 3.2 MemoryOS + augment 配置

```yaml
# MemoryOS_locomo_augment_post_retrieval.yaml
runtime:
  dataset: locomo
  memory_name: MemoryOS-postretrieval-augment
  # ... 其他 runtime 配置同上

services:
  services_type: "hierarchical.tiered_memory"
  tiered_memory:
    tier_names: ["stm", "mtm", "ltm"]
    tier_capacities:
      stm: 50
      mtm: 500
      ltm: -1

operators:
  pre_insert:
    action: score.heat
    access_weight: 0.6
    recency_weight: 0.4

  pre_retrieval:
    action: embedding

  post_insert:
    action: tier_migration.heat_migration
    migration_threshold: 0.7

  post_retrieval:
    action: augment
    include_persona: true        # 添加用户画像
    include_traits: true         # 添加性格特征
    include_summary: true        # 添加记忆摘要
    max_context_tokens: 512      # 上下文 token 限制
```

### 3.3 Mem0ᵍ + link_expand 配置

```yaml
# Mem0g_locomo_link_expand_post_retrieval.yaml
runtime:
  dataset: locomo
  memory_name: Mem0g-postretrieval-linkexpand
  # ... 其他 runtime 配置同上

services:
  services_type: "hierarchical.graph_memory"
  graph_memory:
    enable_graph: true
    vector_dim: 1024

operators:
  pre_insert:
    action: extract.triple
    extraction_method: llm
    max_triplets: 10

  pre_retrieval:
    action: embedding

  post_insert:
    action: conflict_resolution.semantic_consolidation
    retrieve_count: 10
    min_merge_count: 5

  post_retrieval:
    action: merge.link_expand
    expand_top_n: 5              # 对 Top-5 节点扩展邻居
    max_depth: 1                 # 只扩展一层
    max_neighbors: 3             # 每个节点最多 3 个邻居
    neighbor_weight: 0.5         # 邻居节点的权重衰减
```

______________________________________________________________________

## 4. 实验执行计划

### 4.1 实验顺序

```
Phase 1: Baseline (none) 对照
├── TiM-postretrieval-none
├── MemoryOS-postretrieval-none
└── Mem0g-postretrieval-none

Phase 2: 通用策略验证
├── TiM-postretrieval-timeweight
├── MemoryOS-postretrieval-timeweight
└── Mem0g-postretrieval-threshold

Phase 3: 结构特定策略
├── TiM-postretrieval-threshold
├── MemoryOS-postretrieval-augment
└── Mem0g-postretrieval-linkexpand
```

### 4.2 评估指标

| 指标类别   | 指标名称           | 说明                               |
| ---------- | ------------------ | ---------------------------------- |
| 质量指标   | Accuracy           | 基于检索记忆的回答准确率           |
| 质量指标   | Recall@K           | Top-K 检索的召回率                 |
| 质量指标   | Precision@K        | Top-K 检索的精确率                 |
| 效率指标   | Retrieval Latency  | 检索 + 后处理的总延迟              |
| 效率指标   | Result Count       | 返回结果数量（过滤效果）           |

______________________________________________________________________

## 5. 脚本文件

```
benchmarks/experiment/script/result_optimization_strategy/
├── run_tim_locomo_none.sh
├── run_tim_locomo_time_weighted.sh
├── run_tim_locomo_threshold.sh
├── run_memoryos_locomo_none.sh
├── run_memoryos_locomo_time_weighted.sh
├── run_memoryos_locomo_augment.sh
├── run_mem0g_locomo_none.sh
├── run_mem0g_locomo_link_expand.sh
└── run_mem0g_locomo_threshold.sh
```

---

**更新日志**：
- 2026-01-13: 创建 PostRetrieval 实验设计文档
- 按照"每类选取一个典型策略"原则精简实验矩阵
- 设计 3×3=9 个实验配置
