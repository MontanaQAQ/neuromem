# NeuroMem Experimental Testbed

> **Document Type**: Research Testbed Specification  
> **Version**: v2.0  
> **Last Updated**: January 2026  
> **Purpose**: Comprehensive description of the experimental platform for memory management system evaluation

---

## Abstract

This document describes the experimental testbed designed for systematic evaluation of memory management strategies in Retrieval-Augmented Generation (RAG) systems. Our testbed implements a five-dimensional experimental framework that enables controlled isolation and evaluation of individual memory components, supporting reproducible benchmarking across 13+ state-of-the-art memory systems from recent literature.

---

## Table of Contents

1. [Testbed Overview](#testbed-overview)
2. [Five-Dimensional Experimental Framework](#five-dimensional-experimental-framework)
3. [Memory Service Taxonomy](#memory-service-taxonomy)
4. [Experimental Design Methodology](#experimental-design-methodology)
5. [Implementation Details](#implementation-details)

---

## Testbed Overview

### System Architecture

Our testbed implements a modular pipeline architecture that decouples memory operations into five orthogonal dimensions:

```
Retrieval Flow: Query → D4(PreRetrieval) → D1(Retrieve) → D5(PostRetrieval) → Response
Insertion Flow: Data → D2(PreInsert) → D1(Insert) → D3(PostInsert) → Storage
```

### Five-Dimensional Framework (D1-D5)

We propose a novel five-dimensional decomposition of memory management systems:

| Dimension | Component | Paper Terminology | Description | Complexity |
|-----------|-----------|-------------------|-------------|------------|
| **D1** | Memory Service | Memory Data Structure | Core data structures and indexing mechanisms | High |
| **D2** | Pre-Insert Processing | Normalization Strategy | Input transformation and normalization | Medium |
| **D3** | Post-Insert Maintenance | Consolidation Policy | Memory consolidation and evolution policies | High |
| **D4** | Pre-Retrieval Optimization | Query Formulation Strategy | Query formulation and enhancement | Low |
| **D5** | Post-Retrieval Refinement | Context Integration Mechanism | Result reranking and filtering | Medium |

**Terminology Mapping**: The "Component" column uses implementation-oriented terms, while "Paper Terminology" reflects the terminology used in our research publications for conceptual clarity.

This decomposition enables:
- **Controlled Variable Testing**: Isolate individual component effects
- **Ablation Studies**: Systematically remove components to assess contribution
- **Cross-System Comparison**: Fair comparison by matching architectural patterns

---

## Five-Dimensional Experimental Framework

### Dimension 1: Memory Service Architecture

**Taxonomy of Memory Organizations**

We categorize memory services into two architectural paradigms:

**1. Partitional Memory Systems** (Flat storage with multi-index combinations)
- Focus on efficient retrieval through complementary indexing strategies
- Combine temporal, semantic, and textual access patterns
- Examples: FIFO queues, LSH hashing, hybrid vector-keyword indices

**2. Hierarchical Memory Systems** (Structured relationships with dynamic evolution)
- Emphasize semantic connections and knowledge graph structures
- Support relational reasoning and transitive retrieval
- Examples: Bidirectional link graphs, property graphs, semantic knowledge graphs

**Memory Service Implementations**

| Service Category | Implementation | Indexing Mechanism | Source Paper |
|-----------------|----------------|-------------------|--------------|
| **Partitional** |
| | `fifo_queue` | FIFO temporal ordering | SCM [1] |
| | `lsh_hash` | Locality-Sensitive Hashing | TiM [2] |
| | `inverted_vectorstore_combination` | BM25 + FAISS dual-index | Mem0 [3] |
| | `feature_queue_vectorstore_combination` | BM25 + FIFO + FAISS fusion | MemGPT [4] |
| | `feature_queue_segment_combination` | BM25 + FIFO + Segmentation | MemoryOS [5] |
| | `feature_queue_summary_combination` | BM25 + FIFO + Summarization | LDAgent [6] |
| | `feature_summary_vectorstore_combination` | BM25 + Summary + FAISS | MemoryBank [7] |
| **Hierarchical** |
| | `linknote_graph` | Bidirectional semantic links | A-Mem [8] |
| | `property_graph` | RDF-style triple store | Mem0ᵍ [9] |
| | `semantic_inverted_knowledge_graph` | Three-layer retrieval (Semantic→Inverted→Graph) | HippoRAG [10] |

---

### Dimension 2: Pre-Insert Processing

**Objective**: Transform raw input into memory-optimized representations before storage.

**Action Registry**: `pre_insert.action`

| Action | Operation | Purpose | Implementation Source |
|--------|-----------|---------|----------------------|
| `none` | Identity mapping | Baseline: no preprocessing | - |
| `transform.summarize` | Event summarization | Reduce storage footprint | MemoryBank [7] |
| `transform.segment_denoise` | Semantic chunking + noise filtering | Improve retrieval precision | SeCom [11] |
| `extract.triple` | Relation triple extraction | Enable graph-based reasoning | TiM [2], Mem0ᵍ [9] |
| `extract.entity` | Named entity recognition | Support entity-centric queries | - |
| `extract.keyword` | Keyword extraction | Lightweight indexing | MemoryOS [5] |
| `extract.fact` | Atomic fact extraction | Granular knowledge units | Mem0 [3] |

**Configuration Example**:
```yaml
operators:
  pre_insert:
    action: "extract.triple"
    extraction_method: "llm"      # or "pattern", "hybrid"
    max_triplets: 10
    keep_original: false          # Store only extracted triples
```

---

### Dimension 3: Post-Insert Maintenance

**Objective**: Implement memory consolidation, decay, and structural evolution after insertion.

**Strategy Taxonomy**:

```
Post-Insert Strategies
├── Conflict Resolution           # Handle contradictory information
│   ├── llm_crud                 # LLM-driven CRUD operations (Mem0)
│   └── semantic_consolidation   # Semantic deduplication (TiM)
│
├── Decay & Eviction              # Memory forgetting mechanisms
│   ├── forgetting_curve         # Ebbinghaus-inspired decay (MemoryBank)
│   └── time_decay               # Timeout-based deletion (LDAgent)
│
├── Structure Enrichment          # Dynamic knowledge enhancement
│   ├── link_evolution           # Semantic link generation (A-Mem)
│   └── graph_construction       # Synonym edge building (HippoRAG)
│
└── Tier Migration                # Hierarchical memory management
    └── heat_migration           # Access-based tier movement (MemoryOS)
```

**Action Registry**: `post_insert.action`

| Action | Strategy Type | Mechanism | Source Paper |
|--------|--------------|-----------|--------------|
| `none` | Baseline | No post-processing | - |
| `conflict_resolution.llm_crud` | Conflict Resolution | LLM judges create/update/delete | Mem0 [3] |
| `conflict_resolution.semantic_consolidation` | Conflict Resolution | Merge similar, delete contradictory | TiM [2] |
| `decay_eviction.forgetting_curve` | Decay & Eviction | Exponential decay with reinforcement | MemoryBank [7] |
| `decay_eviction.time_decay` | Decay & Eviction | TTL-based removal | LDAgent [6] |
| `structure_enrichment.link_evolution` | Structure Enrichment | Automatic link discovery | A-Mem [8] |
| `structure_enrichment.graph_construction` | Structure Enrichment | Synonym graph building | HippoRAG [10] |
| `tier_migration.heat_migration` | Tier Migration | Hot/cold memory separation | MemoryOS [5] |

**Configuration Example**:
```yaml
operators:
  post_insert:
    action: "decay_eviction.forgetting_curve"
    decay_rate: 0.01              # Daily decay factor
    min_strength: 0.1             # Eviction threshold
    only_on_session_end: true     # Batch processing mode
```

---

### Dimension 4: Pre-Retrieval Optimization

**Objective**: Enhance query representations to improve retrieval effectiveness.

**Action Registry**: `pre_retrieval.action`

| Action | Technique | Effect | Computational Cost |
|--------|-----------|--------|-------------------|
| `none` | Direct query passthrough | Baseline | O(1) |
| `embedding` | Neural embedding | Dense vector representation | O(N) encoder |
| `validate` | Query quality check | Filter invalid queries | O(1) |
| `keyword_extract` | Salient term extraction | Reduce noise | O(N) |
| `optimize.rewrite` | Query reformulation | Semantic expansion | O(N) LLM |
| `optimize.expand` | Term expansion | Recall improvement | O(N·K) |
| `enhancement.decompose` | Multi-query decomposition | Complex query handling | O(N) LLM |
| `enhancement.multi_embed` | Multi-perspective encoding | Diverse representations | O(N·M) |
| `enhancement.route` | Intent-based routing | Index selection | O(1) |

**Configuration Example**:
```yaml
operators:
  pre_retrieval:
    action: "keyword_extract"
    max_keywords: 5
    extraction_method: "tfidf"    # or "llm", "rake"
```

---

### Dimension 5: Post-Retrieval Refinement

**Objective**: Rerank, filter, and merge retrieved results for optimal relevance.

**Action Registry**: `post_retrieval.action`

| Action | Method | Purpose | Source Paper |
|--------|--------|---------|--------------|
| `none` | Identity | Baseline | - |
| `rerank.time_weighted` | Temporal scoring | Recency bias | MemoryBank [7] |
| `rerank.recency` | Timestamp sorting | Latest-first | - |
| `rerank.llm` | LLM-based scoring | Semantic relevance | - |
| `filter.threshold` | Similarity cutoff | Precision improvement | Mem0 [3] |
| `merge.simple` | List concatenation | Multi-source aggregation | - |
| `merge.multi_query` | Multi-level fusion | Hierarchical retrieval | MemoryOS [5] |
| `merge.link_expand` | Graph traversal | Transitive retrieval | A-Mem [8] |

**Configuration Example**:
```yaml
operators:
  post_retrieval:
    action: "rerank.time_weighted"
    decay_rate: 0.05               # Exponential time decay
    enable_reinforcement: true     # Update access timestamps
```

---

## Memory Service Taxonomy

### Representative Service Selection

From 11 available implementations, we selected 5 representative services for comprehensive evaluation based on:
- **Architectural diversity**: Coverage of both partitional and hierarchical paradigms
- **Indexing complexity**: Range from single-index to triple-index systems
- **Scalability profiles**: Different performance characteristics across data scales
- **Literature impact**: Coverage of influential papers in the memory management domain

**Selected Services**:

| Service | Architecture | Index Combination | Time Complexity | Scale | Vector Required | Source Paper |
|---------|-------------|------------------|-----------------|-------|-----------------|--------------|
| `fifo_queue` | Partitional | FIFO only | O(1) insert/delete | <1K | ❌ | SCM [1] |
| `lsh_hash` | Partitional | LSH approximate | O(1) expected | 1M+ | ✅ | TiM [2] |
| `feature_queue_vectorstore` | Partitional | BM25+FIFO+FAISS | O(log N) retrieve | 10K-100K | ✅ | MemGPT [4] |
| `linknote_graph` | Hierarchical | Graph+Vector | O(N+E) traverse | 10K | Optional | A-Mem [8] |
| `semantic_inverted_kg` | Hierarchical | Graph+Inverted+Vector | O(log N) retrieve | 100K+ | ✅ | HippoRAG [10] |

**Architectural Characteristics**:

1. **FIFO Queue**: Simplest temporal baseline, constant-time operations, no semantic understanding
2. **LSH Hash**: Sub-linear approximate similarity search, trades accuracy for speed
3. **Feature-Queue-Vector Combination**: Hybrid retrieval with RRF fusion, balances keyword/semantic/temporal signals
4. **Linknote Graph**: Lightweight knowledge graph with bidirectional semantic links
5. **Semantic Inverted KG**: Complex three-stage retrieval (embedding→keyword→graph), supports reasoning

### Comparison Dimensions

**Storage Overhead**:
- FIFO: O(N) raw text
- LSH: O(N·H) hash tables (H = number of hash functions)
- Feature-Queue-Vector: O(N) + O(N·D) vectors + O(T) terms (inverted index)
- Linknote Graph: O(N + E) nodes + edges
- Semantic Inverted KG: O(N + E + T) comprehensive

**Query Patterns Supported**:
- FIFO: Temporal range queries
- LSH: Approximate nearest neighbor
- Feature-Queue-Vector: Hybrid keyword+semantic+temporal
- Linknote Graph: Link traversal + semantic similarity
- Semantic Inverted KG: Multi-hop reasoning + entity-centric

---

## Experimental Design Methodology

### Controlled Variable Testing Strategy

We employ a **staged experimental design** that progressively introduces complexity while maintaining controlled variables. This approach enables:
1. **Isolated effect measurement**: Each dimension's contribution is quantified independently
2. **Cumulative optimization**: Best configurations from earlier stages inform later experiments
3. **Reproducibility**: Fixed configurations ensure consistent comparison

### Five-Phase Experimental Protocol

**Phase A: Pre-Retrieval Strategy Evaluation** (Complexity: Low)
- **Fixed**: D2=none, D3=none, D5=none, D1=fifo_queue
- **Variable**: D4 ∈ {none, embedding, validate, keyword_extract, decompose}
- **Objective**: Identify optimal query formulation strategy
- **Metrics**: Retrieval accuracy, query latency

**Phase B: Post-Retrieval Refinement** (Complexity: Medium-Low)
- **Fixed**: D4=⟨A*⟩, D2=none, D3=none, D1=fifo_queue
- **Variable**: D5 ∈ {none, rerank.time_weighted, filter.threshold}
- **Objective**: Assess result refinement impact
- **Metrics**: Precision@K, ranking quality (NDCG)

**Phase C: Pre-Insert Normalization** (Complexity: Medium)
- **Fixed**: D4=⟨A*⟩, D5=⟨B*⟩, D3=none, D1=fifo_queue
- **Variable**: D2 ∈ {none, transform.summarize, extract.triple}
- **Objective**: Evaluate input transformation effects
- **Metrics**: Storage efficiency, retrieval recall

**Phase D: Post-Insert Maintenance** (Complexity: High)
- **Fixed**: D4=⟨A*⟩, D5=⟨B*⟩, D2=⟨C*⟩, D1=fifo_queue
- **Variable**: D3 ∈ {none, decay_eviction.forgetting_curve, conflict_resolution.llm_crud}
- **Objective**: Quantify memory evolution impact
- **Metrics**: Memory consistency, long-term recall

**Phase E: Memory Architecture Comparison** (Complexity: Very High)
- **Fixed**: D4/D5/D2/D3 = ⟨Optimal configuration from A-D⟩
- **Variable**: D1 ∈ {fifo_queue, lsh_hash, feature_queue_vectorstore, linknote_graph, semantic_inverted_kg}
- **Objective**: Compare fundamental architectural approaches
- **Metrics**: End-to-end performance, scalability, resource consumption

**Notation**: ⟨X*⟩ denotes the best-performing configuration from Phase X.

### Configuration File Structure

**Naming Convention**: `{System}_{Dataset}_{Dimension}_pipeline.yaml`

**Directory Organization**:
```
benchmarks/experiment/config/
├── primitive_memory_model/              # Baseline systems (13 papers)
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
├── query_formulation_strategy/          # Phase A (D4 experiments)
│   ├── TiM_locomo_embedding_pre_retrieval_pipeline.yaml
│   ├── TiM_locomo_validate_pre_retrieval_pipeline.yaml
│   ├── Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml
│   └── ...
│
├── result_optimization_strategy/        # Phase B (D5 experiments)
├── normalization_strategy/              # Phase C (D2 experiments)
├── consolidation_policy/                # Phase D (D3 experiments)
└── memory_data_structure/               # Phase E (D1 experiments)
```

**Configuration Template**:
```yaml
runtime:
  dataset: "locomo"                      # Benchmark dataset
  memory_name: "TiM-embedding"           # Experiment identifier
  embedding_base_url: "http://localhost:8091/v1"
  embedding_model: "BAAI/bge-m3"

services:
  services_type: "partitional.lsh_hash"  # D1: Memory service
  lsh_hash:
    embedding_dim: 1024
    num_tables: 10
    hash_size: 128
  memory_retrieval_adapter: "none"

operators:
  pre_insert:                            # D2
    action: "extract.triple"
    extraction_method: "llm"

  post_insert:                           # D3
    action: "conflict_resolution.semantic_consolidation"

  pre_retrieval:                         # D4
    action: "embedding"

  post_retrieval:                        # D5
    action: "none"
```

---

## Implementation Details

### Software Stack

**Core Framework**: NeuroMem v0.2.1+
- **Language**: Python 3.10+
- **Memory Backend**: Pluggable storage (Memory, Redis, SageDB)
- **Vector Index**: FAISS, LSH, MockVectorDB
- **Text Index**: BM25s (sparse retrieval)
- **Graph Backend**: NetworkX (in-memory), Neo4j (optional)

**Dependencies**:
```python
# Core
neuromem>=0.2.1
sage-common>=0.1.0      # Logging, embeddings
sagedb>=0.1.0           # Vector database

# Optional backends
redis>=4.0.0
neo4j>=5.0.0
networkx>=3.0
```

### Benchmark Datasets

| Dataset | Conversations | Avg. Turns | Questions | Domain | Characteristics |
|---------|--------------|------------|-----------|---------|-----------------|
| **Locomo** | 100 | 20-30 | 500 | Multi-task | Long context, temporal dependencies |
| **LongMemEval** | TBD | TBD | TBD | TBD | Planned |

**Dataset Properties** (Locomo):
- **Conversation Length**: 500-1000 tokens/conversation
- **Temporal Span**: Multiple sessions, evolving context
- **Query Types**: Factual recall, reasoning, summarization
- **Difficulty**: Medium-Hard (requires multi-hop retrieval)

### Evaluation Metrics

**Retrieval Quality**:
- **Accuracy**: Exact match / F1 score for answer correctness
- **Precision@K**: Fraction of relevant results in top-K
- **Recall@K**: Coverage of relevant results in top-K
- **NDCG@K**: Normalized Discounted Cumulative Gain (ranking quality)

**System Performance**:
- **Latency**:
  - Insert latency (ms/item)
  - Retrieval latency (ms/query)
  - End-to-end response time
- **Throughput**: Queries per second (QPS)
- **Storage Efficiency**: Bytes per memory item

**Scalability**:
- **Memory Footprint**: Peak RAM usage
- **Index Size**: Disk space for indices
- **Time Complexity**: Empirical scaling with data size

### Experimental Execution

**Single Experiment Run**:
```bash
# Using configuration file
python benchmarks/experiment/memory_test_pipeline.py \
  --config config/primitive_memory_model/locomo_tim_pipeline.yaml \
  --task_id conv-26

# Using shell script
bash benchmarks/experiment/script/query_formulation_strategy/run_tim_locomo_embedding.sh
```

**Batch Execution** (Phase A example):
```bash
for strategy in embedding validate keyword_extract decompose; do
  python memory_test_pipeline.py \
    --config config/query_formulation_strategy/TiM_locomo_${strategy}_pre_retrieval_pipeline.yaml \
    --task_id conv-26 \
    --output_dir results/phase_a/${strategy}
done
```

**Output Structure**:
```
.sage/output/benchmarks/benchmark_memory/{dataset}/{date}/{memory_name}/
├── config.yaml                 # Experiment configuration
├── metrics.json                # Performance metrics
├── results.jsonl               # Per-query results
├── logs/
│   ├── insert.log             # Insertion operations
│   └── retrieve.log           # Retrieval operations
└── analysis/
    ├── accuracy_report.txt
    ├── latency_distribution.png
    └── memory_usage.csv
```

### Reproducibility Checklist

- [ ] **Random Seed**: Fixed across all experiments
- [ ] **Model Versions**: Document embedding model versions
- [ ] **Hardware Spec**: CPU/GPU, RAM, storage type
- [ ] **Software Versions**: Python, library dependencies
- [ ] **Configuration Backup**: Store all YAML configs in version control
- [ ] **Dataset Hash**: Verify dataset integrity with checksums

### Statistical Analysis

**Hypothesis Testing**:
- Paired t-test for comparing configurations (same dataset split)
- Bonferroni correction for multiple comparisons
- Significance threshold: α = 0.05

**Reporting Standards**:
- Mean ± Standard Deviation (3+ runs)
- Confidence intervals (95%)
- Effect size (Cohen's d)

---

## Appendices

### Appendix A: Complete Action Registry

**Programmatic Access**:
```python
# List all registered post-insert actions
from benchmarks.experiment.libs.post_insert.registry import PostInsertActionRegistry
print(PostInsertActionRegistry.list_actions())
# Output: ['none', 'conflict_resolution.llm_crud',
#          'conflict_resolution.semantic_consolidation',
#          'decay_eviction.forgetting_curve', 'decay_eviction.time_decay',
#          'structure_enrichment.link_evolution',
#          'structure_enrichment.graph_construction',
#          'tier_migration.heat_migration']

# List all registered pre-retrieval actions
from benchmarks.experiment.libs.pre_retrieval.registry import PreRetrievalActionRegistry
print(PreRetrievalActionRegistry.list_actions())
# Output: ['none', 'embedding', 'validate', 'keyword_extract',
#          'optimize.rewrite', 'optimize.expand',
#          'enhancement.decompose', 'enhancement.multi_embed',
#          'enhancement.route']
```

### Appendix B: Paper References

**Memory Systems Literature**:

[1] **SCM**: Simple Conversational Memory  
[2] **TiM**: Think-in-Memory for knowledge consolidation  
[3] **Mem0**: Intelligent memory layer with LLM-driven CRUD  
[4] **MemGPT**: Virtual context management with hierarchical memory  
[5] **MemoryOS**: Operating system paradigm for LLM memory  
[6] **LDAgent**: Long-term dialogue agent with topic tracking  
[7] **MemoryBank**: Ebbinghaus forgetting curve implementation  
[8] **A-Mem**: Associative memory with link evolution  
[9] **Mem0ᵍ**: Mem0 with knowledge graph extension  
[10] **HippoRAG**: Hippocampus-inspired retrieval with PPR  
[11] **SeCom**: Semantic compression for memory efficiency

### Appendix C: Dataset Specifications

**Locomo Dataset Structure**:
```json
{
  "conversation_id": "conv-26",
  "turns": [
    {
      "turn_id": 1,
      "speaker": "user",
      "utterance": "I need to book a flight to Paris",
      "timestamp": "2024-01-15T10:00:00Z"
    },
    {
      "turn_id": 2,
      "speaker": "assistant",
      "utterance": "Sure, when would you like to travel?",
      "timestamp": "2024-01-15T10:00:05Z"
    }
  ],
  "questions": [
    {
      "question_id": "q1",
      "query": "Where did the user want to travel?",
      "answer": "Paris",
      "type": "factual_recall"
    }
  ]
}
```

### Appendix D: Hardware Requirements

**Minimum Configuration**:
- CPU: 4 cores, 2.0 GHz
- RAM: 16 GB
- Storage: 50 GB SSD
- Network: 100 Mbps (for embedding API)

**Recommended Configuration**:
- CPU: 8 cores, 3.0 GHz
- RAM: 32 GB
- GPU: NVIDIA RTX 3090 (for local embeddings)
- Storage: 200 GB NVMe SSD
- Network: 1 Gbps

### Appendix E: Common Experimental Patterns

**Ablation Study Example**:
```yaml
# Baseline: Full system
D1: semantic_inverted_kg
D2: extract.triple
D3: structure_enrichment.graph_construction
D4: enhancement.decompose
D5: merge.link_expand

# Ablation 1: Remove graph construction (D3)
D3: none  # Keep others same

# Ablation 2: Remove triple extraction (D2)
D2: none  # Restore D3, keep others same

# Ablation 3: Remove query decomposition (D4)
D4: none  # Restore D2, D3, keep others same
```

**Cross-System Comparison**:
```bash
# Compare all 13 baseline systems on same task
for system in scm tim mem0 mem0g memgpt memorybank memoryos ldagent secom amem hipporag hipporag2; do
  python memory_test_pipeline.py \
    --config config/primitive_memory_model/locomo_${system}_pipeline.yaml \
    --task_id conv-26 \
    --output_dir results/baseline_comparison/${system}
done
```

---

## Citation

If you use this testbed in your research, please cite:

```bibtex
@software{neuromem_testbed_2026,
  title = {NeuroMem: A Five-Dimensional Experimental Testbed for Memory Management in RAG Systems},
  author = {{NeuroMem Contributors}},
  year = {2026},
  url = {https://github.com/intellistream/neuromem},
  version = {0.2.1}
}
```

---

**Document Changelog**:
- **2026-01-17**: Restructured for academic audience, added comprehensive implementation details
- **2026-01-13**: Initial v2.0 release with five-dimensional framework
- **2025-12**: Legacy v1.0 operational guide
