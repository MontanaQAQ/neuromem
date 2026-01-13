# PostInsert 记忆巩固策略实验设计

> 基于已复现的代表性工作，针对三个记忆体结构设计 PostInsert 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估记忆维护策略对长期记忆质量的影响
>
> 实验范围：PostInsert 阶段（难度★★★★☆），固定其他阶段为对应系统的 baseline 配置

______________________________________________________________________

## 📋 PostInsert 策略分类体系

本实验采用以下统一的策略分类标准，按策略类型分类：

| 策略类别                                 | 策略名称                                     | 功能定位                       | 代表系统              |
| ---------------------------------------- | -------------------------------------------- | ------------------------------ | --------------------- |
| **1. 透传 (None)**                       | `none`                                       | 不做后处理，直接存储           | Baseline              |
| **2. 冲突解决 (Conflict Resolution)**    | `conflict_resolution.llm_crud`               | LLM 驱动的 CRUD 决策           | Mem0, MemGPT          |
|                                          | `conflict_resolution.semantic_consolidation` | 语义去重合并                   | TiM, Mem0ᵍ            |
| **3. 衰减淘汰 (Decay Eviction)**         | `decay_eviction.forgetting_curve`            | Ebbinghaus 遗忘曲线            | MemoryBank            |
|                                          | `decay_eviction.time_decay`                  | 时间线性衰减                   | LD-Agent              |
| **4. 结构增强 (Structure Enrichment)**   | `structure_enrichment.link_evolution`        | 自动链接演化                   | A-Mem                 |
|                                          | `structure_enrichment.graph_construction`    | 知识图谱构建                   | HippoRAG              |
| **5. 层级迁移 (Tier Migration)**         | `structure_enrichment.heat_migration`              | 基于热度的层级迁移             | MemoryOS              |

**分类设计原则**：

- **策略驱动**：按维护策略的设计意图分类，而非功能分类
- **互斥选择**：每个实验仅使用一种后插入策略
- **系统映射**：每个策略明确对应一个或多个代表系统

**典型策略选取原则（每类1个）**：

| 策略类别       | 选取的典型策略                               | 选取理由                           |
| -------------- | -------------------------------------------- | ---------------------------------- |
| 透传           | `none`                                       | 唯一选项，作为基线                 |
| 冲突解决       | `conflict_resolution.semantic_consolidation` | 更通用，不依赖额外 LLM 调用        |
| 衰减淘汰       | `decay_eviction.forgetting_curve`            | 符合人类记忆规律，应用广泛         |
| 结构增强       | `structure_enrichment.link_evolution`        | 相比 graph_construction 更轻量     |
| 层级迁移       | `structure_enrichment.heat_migration`              | 唯一选项                           |

______________________________________________________________________

## ⚠️ 重要架构约束

### PostInsert 策略与数据结构的兼容性

| Action                                      | 依赖的数据结构              | 约束说明                                           |
| ------------------------------------------- | --------------------------- | -------------------------------------------------- |
| `structure_enrichment.link_evolution`       | `graph_memory` / `hybrid`   | ❌ 必须有图结构才能建立链接                        |
| `structure_enrichment.graph_construction`   | `graph_memory` / `hybrid`   | ❌ 必须有图结构才能添加节点和边                    |
| `structure_enrichment.heat_migration`             | `hierarchical_memory`       | ❌ 必须有多层结构才能迁移                          |
| `conflict_resolution.*`                     | 任意                        | ✅ 通用策略，适用于所有结构                        |
| `decay_eviction.*`                          | 任意                        | ✅ 通用策略，适用于所有结构                        |

### 与 PreInsert 的关联

某些 PostInsert 策略依赖 PreInsert 的输出：

| PostInsert 策略                            | PreInsert 依赖               | 说明                               |
| ------------------------------------------ | ---------------------------- | ---------------------------------- |
| `structure_enrichment.graph_construction`  | `extract.triple`             | 需要三元组作为图的边               |
| `structure_enrichment.heat_migration`            | `score.heat`                 | 需要热度评分作为迁移依据           |
| `decay_eviction.forgetting_curve`          | `score.importance`（可选）   | 重要性可影响记忆稳定性             |

______________________________________________________________________

## 1. 三个代表性记忆体结构选取

与 PreRetrieval 实验保持一致，选取以下代表性配置：

### 1.1 向量数据库结构 - TiM

**代表工作**: `locomo_tim_pipeline.yaml`
**架构特点**: LSH哈希桶 + 向量检索 + 三元组提取
**固定配置**:
- `pre_insert: extract.triple`
- `pre_retrieval: embedding`
- `post_retrieval: none`

**适合测试的 PostInsert 策略**：
- `none`: 无后处理基线
- `conflict_resolution.semantic_consolidation`: 语义去重合并（TiM 原生策略）
- `decay_eviction.forgetting_curve`: 遗忘曲线淘汰

### 1.2 多层结构 - MemoryOS

**代表工作**: `locomo_memoryos_pipeline.yaml`
**架构特点**: STM/MTM/LTM 三层 + 热度评分 + 主动迁移
**固定配置**:
- `pre_insert: score.heat`
- `pre_retrieval: embedding`
- `post_retrieval: none`

**适合测试的 PostInsert 策略**：
- `none`: 无后处理基线
- `structure_enrichment.heat_migration`: 热度迁移（MemoryOS 原生策略）
- `decay_eviction.forgetting_curve`: 遗忘曲线淘汰

### 1.3 图结构 - Mem0ᵍ

**代表工作**: `locomo_mem0g_pipeline.yaml`
**架构特点**: 向量 + 知识图谱 + 实体链接
**固定配置**:
- `pre_insert: extract.triple`
- `pre_retrieval: embedding`
- `post_retrieval: none`

**适合测试的 PostInsert 策略**：
- `none`: 无后处理基线
- `conflict_resolution.semantic_consolidation`: 语义去重合并
- `structure_enrichment.link_evolution`: 链接演化（A-Mem 策略）

______________________________________________________________________

## 2. 实验配置矩阵

### 2.1 TiM 系列实验

| 配置ID | 配置文件                                                   | 内存名称                        | PostInsert 策略                              |
| ------ | ---------------------------------------------------------- | ------------------------------- | -------------------------------------------- |
| **T1** | `TiM_locomo_none_post_insert_pipeline.yaml`                | `TiM-postinsert-none`           | `none`                                       |
| **T2** | `TiM_locomo_semantic_consolidation_post_insert.yaml`       | `TiM-postinsert-consolidation`  | `conflict_resolution.semantic_consolidation` |
| **T3** | `TiM_locomo_forgetting_curve_post_insert.yaml`             | `TiM-postinsert-forgetting`     | `decay_eviction.forgetting_curve`            |

### 2.2 MemoryOS 系列实验

| 配置ID | 配置文件                                                     | 内存名称                          | PostInsert 策略                   |
| ------ | ------------------------------------------------------------ | --------------------------------- | --------------------------------- |
| **M1** | `MemoryOS_locomo_none_post_insert_pipeline.yaml`             | `MemoryOS-postinsert-none`        | `none`                            |
| **M2** | `MemoryOS_locomo_heat_migration_post_insert.yaml`            | `MemoryOS-postinsert-migration`   | `structure_enrichment.heat_migration`   |
| **M3** | `MemoryOS_locomo_forgetting_curve_post_insert.yaml`          | `MemoryOS-postinsert-forgetting`  | `decay_eviction.forgetting_curve` |

### 2.3 Mem0ᵍ 系列实验

| 配置ID | 配置文件                                                    | 内存名称                         | PostInsert 策略                              |
| ------ | ----------------------------------------------------------- | -------------------------------- | -------------------------------------------- |
| **G1** | `Mem0g_locomo_none_post_insert_pipeline.yaml`               | `Mem0g-postinsert-none`          | `none`                                       |
| **G2** | `Mem0g_locomo_semantic_consolidation_post_insert.yaml`      | `Mem0g-postinsert-consolidation` | `conflict_resolution.semantic_consolidation` |
| **G3** | `Mem0g_locomo_link_evolution_post_insert.yaml`              | `Mem0g-postinsert-link`          | `structure_enrichment.link_evolution`        |

**实验总数**: 9 个配置（3 个记忆体 × 3 个策略）

______________________________________________________________________

## 3. 配置文件详情

### 3.1 TiM + semantic_consolidation 配置

```yaml
# TiM_locomo_semantic_consolidation_post_insert.yaml
runtime:
  dataset: locomo
  memory_name: TiM-postinsert-consolidation
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
    retrieve_count: 10           # 检索相似记忆的数量
    min_merge_count: 5           # 触发合并的最小相似记忆数
    similarity_threshold: 0.85   # 合并的相似度阈值

  post_retrieval:
    action: none
```

### 3.2 MemoryOS + heat_migration 配置

```yaml
# MemoryOS_locomo_heat_migration_post_insert.yaml
runtime:
  dataset: locomo
  memory_name: MemoryOS-postinsert-migration
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
    action: structure_enrichment.heat_migration
    migration_threshold: 0.7     # 热度低于此值时迁移
    check_interval: 100          # 每 100 次插入检查一次

  post_retrieval:
    action: none
```

### 3.3 Mem0ᵍ + link_evolution 配置

```yaml
# Mem0g_locomo_link_evolution_post_insert.yaml
runtime:
  dataset: locomo
  memory_name: Mem0g-postinsert-link
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
    action: structure_enrichment.link_evolution
    link_top_k: 5                # 为新记忆链接 Top-5 相关记忆
    similarity_threshold: 0.75   # 链接的相似度阈值
    link_types: ["related_to", "elaborates", "contradicts"]

  post_retrieval:
    action: none
```

______________________________________________________________________

## 4. 实验执行计划

### 4.1 实验顺序

```
Phase 1: Baseline (none) 对照
├── TiM-postinsert-none
├── MemoryOS-postinsert-none
└── Mem0g-postinsert-none

Phase 2: 原生策略验证
├── TiM-postinsert-consolidation (TiM 原生)
├── MemoryOS-postinsert-migration (MemoryOS 原生)
└── Mem0g-postinsert-consolidation

Phase 3: 跨系统策略迁移
├── TiM-postinsert-forgetting (MemoryBank 策略)
├── MemoryOS-postinsert-forgetting (MemoryBank 策略)
└── Mem0g-postinsert-link (A-Mem 策略)
```

### 4.2 评估指标

| 指标类别   | 指标名称           | 说明                               |
| ---------- | ------------------ | ---------------------------------- |
| 质量指标   | Accuracy           | 基于检索记忆的回答准确率           |
| 质量指标   | Recall@K           | Top-K 检索的召回率                 |
| 效率指标   | Insert Latency     | 插入 + 后处理的总延迟              |
| 效率指标   | Memory Count       | 最终存储的记忆数量（去重效果）     |
| 效率指标   | Storage Size       | 存储空间占用                       |

______________________________________________________________________

## 5. 脚本文件

```
benchmarks/experiment/script/consolidation_policy/
├── run_tim_locomo_none.sh
├── run_tim_locomo_semantic_consolidation.sh
├── run_tim_locomo_forgetting_curve.sh
├── run_memoryos_locomo_none.sh
├── run_memoryos_locomo_heat_migration.sh
├── run_memoryos_locomo_forgetting_curve.sh
├── run_mem0g_locomo_none.sh
├── run_mem0g_locomo_semantic_consolidation.sh
└── run_mem0g_locomo_link_evolution.sh
```

---

**更新日志**：
- 2026-01-13: 创建 PostInsert 实验设计文档
- 按照"每类选取一个典型策略"原则精简实验矩阵
- 设计 3×3=9 个实验配置
