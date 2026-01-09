# Query Formulation Strategy (PreRetrieval) 实验配置生成指南

> **任务**: 为 B3 实验组（PreRetrieval 维度探索）生成完整的配置文件和执行脚本
> **时间**: 2026-01-09
> **目标文件数**: 12个配置文件 + 12个执行脚本

---

## 📋 任务总览

根据 `Data_Structure_Selection_Rationale.md` 中定义的 **B3 实验组**，需要生成：

### B3 实验矩阵（固定 D2/D3/D5，探索 D4）

| 实验ID | 数据结构 | D2 (固定) | D3 (固定) | D4 (变化) | D5 (固定) | 配置文件名 |
|--------|---------|----------|----------|----------|----------|-----------|
| B3-1 | TiM | `extract.triple` | `distillation` | `embedding` ✅论文 | `none` | `TiM_locomo_embedding_pre_retrieval_pipeline.yaml` |
| B3-2 | TiM | `extract.triple` | `distillation` | `validate` | `none` | `TiM_locomo_validate_pre_retrieval_pipeline.yaml` |
| B3-3 | TiM | `extract.triple` | `distillation` | `keyword_extract` | `none` | `TiM_locomo_keyword_extract_pre_retrieval_pipeline.yaml` |
| B3-4 | TiM | `extract.triple` | `distillation` | `decompose` | `none` | `TiM_locomo_decompose_pre_retrieval_pipeline.yaml` |
| B3-5 | Mem0ᵍ | `extract.triple` | `crud` | `embedding` ✅论文 | `none` | `Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml` |
| B3-6 | Mem0ᵍ | `extract.triple` | `crud` | `validate` | `none` | `Mem0g_locomo_validate_pre_retrieval_pipeline.yaml` |
| B3-7 | Mem0ᵍ | `extract.triple` | `crud` | `keyword_extract` | `none` | `Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml` |
| B3-8 | Mem0ᵍ | `extract.triple` | `crud` | `decompose` | `none` | `Mem0g_locomo_decompose_pre_retrieval_pipeline.yaml` |
| B3-9 | MemoryOS | `none` | `migrate` | `embedding` | `merge.multi_query` | `MemoryOS_locomo_embedding_pre_retrieval_pipeline.yaml` |
| B3-10 | MemoryOS | `none` | `migrate` | `validate` | `merge.multi_query` | `MemoryOS_locomo_validate_pre_retrieval_pipeline.yaml` |
| B3-11 | MemoryOS | `none` | `migrate` | `keyword_extract` ✅论文 | `merge.multi_query` | `MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml` |
| B3-12 | MemoryOS | `none` | `migrate` | `decompose` | `merge.multi_query` | `MemoryOS_locomo_decompose_pre_retrieval_pipeline.yaml` |

---

## 📂 文件结构要求

### 目录结构

```
benchmarks/experiment/
├── config/query_formulation_strategy/
│   ├── TiM_locomo_embedding_pre_retrieval_pipeline.yaml        ✅ 已存在
│   ├── TiM_locomo_validate_pre_retrieval_pipeline.yaml         ✅ 已存在
│   ├── TiM_locomo_keyword_extract_pre_retrieval_pipeline.yaml  ✅ 已存在
│   ├── TiM_locomo_decompose_pre_retrieval_pipeline.yaml        ✅ 已存在
│   ├── Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml      ❌ 需要创建
│   ├── Mem0g_locomo_validate_pre_retrieval_pipeline.yaml       ❌ 需要创建
│   ├── Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml ❌ 需要创建
│   ├── Mem0g_locomo_decompose_pre_retrieval_pipeline.yaml      ❌ 需要创建
│   ├── MemoryOS_locomo_embedding_pre_retrieval_pipeline.yaml   ❌ 需要创建
│   ├── MemoryOS_locomo_validate_pre_retrieval_pipeline.yaml    ❌ 需要创建
│   ├── MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml ❌ 需要创建
│   └── MemoryOS_locomo_decompose_pre_retrieval_pipeline.yaml   ❌ 需要创建
│
└── script/query_formulation_strategy/
    ├── run_tim_locomo_embedding.sh                             ✅ 已存在
    ├── run_tim_locomo_validate.sh                              ✅ 已存在
    ├── run_tim_locomo_keyword_extract.sh                       ✅ 已存在
    ├── run_tim_locomo_decompose.sh                             ✅ 已存在
    ├── run_mem0g_locomo_embedding.sh                           ❌ 需要创建
    ├── run_mem0g_locomo_validate.sh                            ❌ 需要创建
    ├── run_mem0g_locomo_keyword_extract.sh                     ❌ 需要创建
    ├── run_mem0g_locomo_decompose.sh                           ❌ 需要创建
    ├── run_memoryos_locomo_embedding.sh                        ❌ 需要创建
    ├── run_memoryos_locomo_validate.sh                         ❌ 需要创建
    ├── run_memoryos_locomo_keyword_extract.sh                  ❌ 需要创建
    └── run_memoryos_locomo_decompose.sh                        ❌ 需要创建
```

---

## 🔧 配置文件生成指南

### 第一步：确定三个基础模板

为三个数据结构分别创建基础配置（从 `primitive_memory_model/` 获取）：

#### 1. TiM 基础模板
**源文件**: `benchmarks/experiment/config/primitive_memory_model/locomo_tim_pipeline.yaml`
**已有参考**: `benchmarks/experiment/config/query_formulation_strategy/TiM_locomo_embedding_pre_retrieval_pipeline.yaml`

**核心配置**:
```yaml
runtime:
  memory_name: "TiM-<strategy>"  # strategy = embedding/validate/keyword_extract/decompose

services:
  services_type: "partitional.lsh_hash"
  lsh_hash:
    vector_dim: 1024
    lsh_nbits: 128
    lsh_rotate_data: true
    lsh_train_thresholds: false
    retrieval_top_k: 10
  memory_retrieval_adapter: none

operators:
  pre_insert:
    action: extract.triple      # 固定
    extraction_method: llm
    max_triplets: 10
    keep_original: false
    triple_extraction_prompt: |
      You are a factual knowledge extractor.
      Analyze the dialogue below and extract all subject–predicate–object triples...
      (使用 TiM 已有 prompt)

  post_insert:
    action: distillation        # 固定
    retrieve_count: 10
    min_merge_count: 5
    merge_prompt: |
      You are a memory consolidation expert...
      (使用 TiM 已有 prompt)

  pre_retrieval:
    action: <strategy>          # 变化：embedding/validate/keyword_extract/decompose

  post_retrieval:
    action: none                # 固定
    conversation_format_prompt: |
      The following is some history information.
```

#### 2. Mem0ᵍ 基础模板
**源文件**: `benchmarks/experiment/config/primitive_memory_model/locomo_mem0g_pipeline.yaml`

**核心配置**:
```yaml
runtime:
  memory_name: "Mem0g-<strategy>"

services:
  services_type: "hierarchical.semantic_inverted_knowledge_graph"
  semantic_inverted_knowledge_graph:
    vector_dim: 1024
    hierarchy_levels: 3
    routing_strategy: "parallel"
    enable_cross_layer_query: true
    max_hops: 3
    default_index: "semantic_index"
  memory_retrieval_adapter: "none"

operators:
  pre_insert:
    action: "extract.triple"    # 固定
    extraction_method: "llm"
    triple_extraction_prompt: |
      You are a knowledge graph builder. Extract factual triples from the dialogue...
      (使用 Mem0g 已有 prompt)

  post_insert:
    action: "crud"              # 固定
    crud_strategy: "auto"
    update_threshold: 0.85
    delete_threshold: 0.95
    merge_threshold: 0.90

  pre_retrieval:
    action: <strategy>          # 变化：embedding/validate/keyword_extract/decompose

  post_retrieval:
    action: "none"              # 固定
    conversation_format_prompt: |
      The following is some history information.
```

#### 3. MemoryOS 基础模板
**源文件**: `benchmarks/experiment/config/primitive_memory_model/locomo_memoryos_pipeline.yaml`

**核心配置**:
```yaml
runtime:
  memory_name: "MemoryOS-<strategy>"

services:
  services_type: "partitional.feature_queue_segment_combination"
  feature_queue_segment_combination:
    vector_dim: 1024
    fifo_max_size: 20
    segment_strategy: "time"
    segment_threshold: 3600
    enable_feature_extraction: true
    combination_strategy: "weighted"
    weights:
      feature_index: 0.3
      fifo_index: 0.4
      segment_index: 0.3
  memory_retrieval_adapter: "none"

operators:
  pre_insert:
    action: "none"              # 固定

  post_insert:
    action: "migrate"           # 固定
    migrate_strategy: "time_based"
    stm_threshold: 20
    mtm_threshold: 50
    heat_score_enabled: true
    heat_decay_factor: 0.9

  pre_retrieval:
    action: <strategy>          # 变化：embedding/validate/keyword_extract/decompose

  post_retrieval:
    action: "merge.multi_query" # 固定
    merge_strategy: "weighted"
    diversify_results: true
    deduplication_threshold: 0.90
```

---

### 第二步：PreRetrieval 策略配置详情

根据 `benchmarks/experiment/libs/pre_retrieval/registry.py`，四种策略的完整配置如下：

#### 策略 1: `embedding`
```yaml
pre_retrieval:
  action: embedding
  # 默认使用 runtime.embedding_model
  # 无需额外参数
```

**功能**: 将查询向量化（标准 RAG baseline）

---

#### 策略 2: `validate`
```yaml
pre_retrieval:
  action: validate
  validation_type: "quality"         # 或 "relevance" / "completeness"
  reject_threshold: 0.3              # 低于此分数的查询拒绝
  fallback_strategy: "rephrase"      # 或 "expand" / "none"
  validation_prompt: |
    You are a query quality validator. Assess whether the following query is clear, specific, and answerable.
    Query: {query}
    Provide a score from 0.0 to 1.0:
```

**功能**: 验证查询质量，低质量查询触发改写

---

#### 策略 3: `keyword_extract`
```yaml
pre_retrieval:
  action: keyword_extract
  extraction_method: "llm"           # 或 "tfidf" / "rake"
  max_keywords: 5
  filter_stopwords: true
  keyword_extraction_prompt: |
    Extract the 3-5 most important keywords from the following query for retrieval.
    Query: {query}
    Keywords (comma-separated):
```

**功能**: 提取关键词，增强混合检索效果（BM25 + 向量）

---

#### 策略 4: `decompose`
```yaml
pre_retrieval:
  action: decompose
  decomposition_method: "llm"        # 或 "rule_based"
  max_subqueries: 3
  enable_dependency_analysis: true
  decomposition_prompt: |
    You are a query decomposer. Break down the following complex question into 2-3 simpler sub-questions that can be answered independently.

    Original Question: {query}

    Sub-questions (one per line):
    1.
    2.
    3.
```

**功能**: 将复杂查询分解为多个子查询（Multi-Hop Reasoning）

---

### 第三步：生成配置文件

#### 示例：Mem0g + embedding

**文件名**: `benchmarks/experiment/config/query_formulation_strategy/Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml`

```yaml
# ============================================================
# PreRetrieval 实验: Mem0ᵍ + Embedding
# 记忆体结构: Mem0ᵍ (语义倒排知识图谱)
# PreRetrieval 策略: embedding
# 配置名称: Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml
# ============================================================

runtime:
  dataset: locomo
  memory_insert_verbose: false
  memory_test_verbose: true
  test_segments: 10
  service_timeout: 600.0

  prompt_template: |
    Based on the above context, answer the following question concisely.

    Question: {question}
    Answer:

  prompt_template_category5: |
    Based on the above context, answer the following question.

    Question: {question}
    Answer:

  # LLM 配置
  api_key: token-abc123
  base_url: http://sage2:8000/v1
  model_name: /home/cyb/Llama-3.1-8B-Instruct
  llm_base_url: http://sage2:8000/v1
  llm_model: /home/cyb/Llama-3.1-8B-Instruct
  max_tokens: 512
  temperature: 0.3
  seed: 42
  memory_name: Mem0g-embedding

  # Embedding 配置
  embedding_base_url: http://localhost:8091/v1
  embedding_model: BAAI/bge-m3

services:
  services_type: "hierarchical.semantic_inverted_knowledge_graph"
  semantic_inverted_knowledge_graph:
    vector_dim: 1024
    hierarchy_levels: 3
    routing_strategy: "parallel"
    enable_cross_layer_query: true
    max_hops: 3
    default_index: "semantic_index"
  memory_retrieval_adapter: "none"

operators:
  pre_insert:
    action: "extract.triple"
    extraction_method: "llm"
    triple_extraction_prompt: |
      You are a knowledge graph builder. Extract factual triples from the dialogue.

      Guidelines:
      - Map "I", "me", "my" to the speaker's name.
      - Use format: (Subject, Predicate, Object)
      - Only extract explicit facts, no assumptions.

      Dialogue:
      {dialogue}

      Output:
      (Subject, Predicate, Object)
      ...

  post_insert:
    action: "crud"
    crud_strategy: "auto"
    update_threshold: 0.85
    delete_threshold: 0.95
    merge_threshold: 0.90

  pre_retrieval:
    action: embedding

  post_retrieval:
    action: "none"
    conversation_format_prompt: |
      The following is some history information.
```

---

## 🚀 执行脚本生成指南

### Shell 脚本模板

**文件名**: `benchmarks/experiment/script/query_formulation_strategy/run_mem0g_locomo_embedding.sh`

```bash
#!/bin/bash
# 运行 Mem0g Locomo PreRetrieval 实验 - embedding
# 使用方法: bash script/query_formulation_strategy/run_mem0g_locomo_embedding.sh

set -e  # 遇到错误立即退出

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 获取项目根目录 (从 script/query_formulation_strategy/ 向上 4 层到 neuromem/)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
# Python 脚本的相对路径
PYTHON_SCRIPT="$SCRIPT_DIR/../../memory_test_pipeline.py"
# 配置文件路径
CONFIG_FILE="$SCRIPT_DIR/../../config/query_formulation_strategy/Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml"

# 定义所有任务 ID
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  "conv-42"
  "conv-43"
  "conv-44"
  "conv-47"
  "conv-48"
  "conv-49"
  "conv-50"
)

# 创建日志目录结构
DATASET="locomo"
DATE=$(date +%Y%m%d)
MEMORY_NAME="Mem0g-embedding"
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$DATE/$MEMORY_NAME"
mkdir -p "$LOG_BASE_DIR"

echo "========================================================================"
echo "Mem0g Locomo PreRetrieval 实验 - embedding"
echo "========================================================================"
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "Python 脚本: $(realpath "$PYTHON_SCRIPT")"
echo "配置文件: $(realpath "$CONFIG_FILE")"
echo "日志目录: $LOG_BASE_DIR"
echo "总任务数: ${#TASK_IDS[@]}"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 依次运行所有任务
for i in "${!TASK_IDS[@]}"; do
  TASK_ID="${TASK_IDS[$i]}"
  TASK_NUM=$((i + 1))

  # 生成带时间戳的日志文件名
  TIMESTAMP=$(date +%H%M%S)
  LOG_FILE="$LOG_BASE_DIR/${TASK_ID}_${TIMESTAMP}.log"

  echo "--------------------------------------------------------------------"
  echo "🚀 开始运行任务 [$TASK_NUM/${#TASK_IDS[@]}]: $TASK_ID"
  echo "📝 日志文件: $LOG_FILE"
  echo "--------------------------------------------------------------------"

  # 运行任务并将输出重定向到日志文件（同时显示到终端）
  PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH" python "$PYTHON_SCRIPT" --config "$CONFIG_FILE" --task_id "$TASK_ID" 2>&1 | tee "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✅ 任务 $TASK_ID 完成，日志已保存到: $LOG_FILE"
  else
    echo "❌ 任务 $TASK_ID 失败，日志已保存到: $LOG_FILE"
    exit 1
  fi

  echo ""
done

echo "========================================================================"
echo "🎉 所有任务执行完毕 - Mem0g-embedding"
echo "📁 所有日志已保存到: $LOG_BASE_DIR"
echo "========================================================================"
```

---

## 📝 命名规范

### 配置文件命名
```
<DataStructure>_locomo_<strategy>_pre_retrieval_pipeline.yaml
```

**示例**:
- `TiM_locomo_embedding_pre_retrieval_pipeline.yaml`
- `Mem0g_locomo_validate_pre_retrieval_pipeline.yaml`
- `MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml`

### 脚本文件命名
```
run_<datastructure>_locomo_<strategy>.sh
```

**示例**:
- `run_tim_locomo_embedding.sh`
- `run_mem0g_locomo_validate.sh`
- `run_memoryos_locomo_keyword_extract.sh`

**注意**: 数据结构名全小写

### memory_name 命名
```
<DataStructure>-<strategy>
```

**示例**:
- `TiM-embedding`
- `Mem0g-validate`
- `MemoryOS-keyword_extract`

---

## ✅ 实现检查清单

### Mem0ᵍ 配置文件 (4个)
- [ ] `Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml`
- [ ] `Mem0g_locomo_validate_pre_retrieval_pipeline.yaml`
- [ ] `Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml`
- [ ] `Mem0g_locomo_decompose_pre_retrieval_pipeline.yaml`

### Mem0ᵍ 执行脚本 (4个)
- [ ] `run_mem0g_locomo_embedding.sh`
- [ ] `run_mem0g_locomo_validate.sh`
- [ ] `run_mem0g_locomo_keyword_extract.sh`
- [ ] `run_mem0g_locomo_decompose.sh`

### MemoryOS 配置文件 (4个)
- [ ] `MemoryOS_locomo_embedding_pre_retrieval_pipeline.yaml`
- [ ] `MemoryOS_locomo_validate_pre_retrieval_pipeline.yaml`
- [ ] `MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml`
- [ ] `MemoryOS_locomo_decompose_pre_retrieval_pipeline.yaml`

### MemoryOS 执行脚本 (4个)
- [ ] `run_memoryos_locomo_embedding.sh`
- [ ] `run_memoryos_locomo_validate.sh`
- [ ] `run_memoryos_locomo_keyword_extract.sh`
- [ ] `run_memoryos_locomo_decompose.sh`

---

## 🔍 关键注意事项

### 1. 配置文件头部注释
每个配置文件开头必须包含：
```yaml
# ============================================================
# PreRetrieval 实验: <DataStructure> + <Strategy>
# 记忆体结构: <DataStructure> (架构描述)
# PreRetrieval 策略: <strategy>
# 配置名称: <filename>
# ============================================================
```

### 2. Runtime 配置统一
所有配置文件的 runtime 部分除了 `memory_name` 外，其余参数保持一致：
- `dataset: locomo`
- `test_segments: 10`
- LLM 配置使用相同的 `base_url` 和 `model_name`
- Embedding 配置使用 `BAAI/bge-m3`

### 3. Operator 配置锁定
- **D2 (PreInsert)**: 每个数据结构使用固定配置（见 B3 矩阵）
- **D3 (PostInsert)**: 每个数据结构使用固定配置（见 B3 矩阵）
- **D4 (PreRetrieval)**: **唯一变化的维度**（embedding/validate/keyword_extract/decompose）
- **D5 (PostRetrieval)**: 每个数据结构使用固定配置（见 B3 矩阵）

### 4. 任务 ID 列表
所有脚本使用相同的 10 个任务：
```bash
TASK_IDS=(
  "conv-26"
  "conv-30"
  "conv-41"
  "conv-42"
  "conv-43"
  "conv-44"
  "conv-47"
  "conv-48"
  "conv-49"
  "conv-50"
)
```

### 5. 日志路径规范
```bash
LOG_BASE_DIR="$PROJECT_ROOT/.sage/output/benchmarks/benchmark_memory/$DATASET/$DATE/$MEMORY_NAME"
```

### 6. PreRetrieval 策略参数
- **embedding**: 无需额外参数（默认使用 runtime 的 embedding 配置）
- **validate**: 需要 `validation_type`, `reject_threshold`, `fallback_strategy`, `validation_prompt`
- **keyword_extract**: 需要 `extraction_method`, `max_keywords`, `filter_stopwords`, `keyword_extraction_prompt`
- **decompose**: 需要 `decomposition_method`, `max_subqueries`, `enable_dependency_analysis`, `decomposition_prompt`

---

## 🎯 实现顺序建议

### Phase 1: Mem0ᵍ (4个配置 + 4个脚本)
1. 先创建 `Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml`（最简单，无额外参数）
2. 测试运行 `run_mem0g_locomo_embedding.sh` 确保基础配置正确
3. 依次创建 validate/keyword_extract/decompose 配置
4. 测试所有 Mem0ᵍ 脚本

### Phase 2: MemoryOS (4个配置 + 4个脚本)
1. 先创建 `MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml`（论文原配置）
2. 测试运行 `run_memoryos_locomo_keyword_extract.sh`
3. 依次创建 embedding/validate/decompose 配置
4. 测试所有 MemoryOS 脚本

---

## 📚 参考文件位置

### 基础配置参考
- TiM: `benchmarks/experiment/config/primitive_memory_model/locomo_tim_pipeline.yaml`
- Mem0ᵍ: `benchmarks/experiment/config/primitive_memory_model/locomo_mem0g_pipeline.yaml`
- MemoryOS: `benchmarks/experiment/config/primitive_memory_model/locomo_memoryos_pipeline.yaml`

### 已有实现参考
- TiM 配置: `benchmarks/experiment/config/query_formulation_strategy/TiM_locomo_*_pre_retrieval_pipeline.yaml`
- TiM 脚本: `benchmarks/experiment/script/query_formulation_strategy/run_tim_locomo_*.sh`

### PreRetrieval Operator 代码
- Registry: `benchmarks/experiment/libs/pre_retrieval/registry.py`
- Implementations: `benchmarks/experiment/libs/pre_retrieval/*.py`

---

## 🚨 常见错误检查

### 配置文件
- [ ] YAML 缩进正确（2空格，不使用 Tab）
- [ ] `memory_name` 与文件名匹配
- [ ] `pre_retrieval.action` 拼写正确（无 `optimize.`/`enhancement.` 前缀）
- [ ] Prompt 中的占位符使用正确（`{query}`, `{dialogue}` 等）
- [ ] 文件头部注释完整

### 执行脚本
- [ ] Shebang 行正确：`#!/bin/bash`
- [ ] `MEMORY_NAME` 与配置文件中的 `runtime.memory_name` 一致
- [ ] `CONFIG_FILE` 路径正确
- [ ] 脚本有执行权限：`chmod +x run_*.sh`
- [ ] 所有任务 ID 正确（10个 conv-XX）

---

## ✨ 生成后验证步骤

### 1. 配置文件验证
```bash
cd /home/zrc/develop_item/bench/neuromem
python -c "import yaml; yaml.safe_load(open('benchmarks/experiment/config/query_formulation_strategy/Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml'))"
```

### 2. 脚本语法验证
```bash
bash -n benchmarks/experiment/script/query_formulation_strategy/run_mem0g_locomo_embedding.sh
```

### 3. 干运行测试（单任务）
```bash
cd /home/zrc/develop_item/bench/neuromem
bash benchmarks/experiment/script/query_formulation_strategy/run_mem0g_locomo_embedding.sh
# 观察第一个任务是否正常启动
```

### 4. 文件清单验证
```bash
# 检查 Mem0g 配置文件数量
ls benchmarks/experiment/config/query_formulation_strategy/Mem0g_*.yaml | wc -l
# 预期输出: 4

# 检查 Mem0g 脚本文件数量
ls benchmarks/experiment/script/query_formulation_strategy/run_mem0g_*.sh | wc -l
# 预期输出: 4

# 检查 MemoryOS 配置文件数量
ls benchmarks/experiment/config/query_formulation_strategy/MemoryOS_*.yaml | wc -l
# 预期输出: 4

# 检查 MemoryOS 脚本文件数量
ls benchmarks/experiment/script/query_formulation_strategy/run_memoryos_*.sh | wc -l
# 预期输出: 4
```

---

## 📊 预期实验产出

完成后，B3 实验组将产生：

### 配置文件
- **TiM**: 4个配置（已存在）
- **Mem0ᵍ**: 4个配置（新建）
- **MemoryOS**: 4个配置（新建）
- **总计**: 12个 YAML 配置文件

### 执行脚本
- **TiM**: 4个脚本（已存在）
- **Mem0ᵍ**: 4个脚本（新建）
- **MemoryOS**: 4个脚本（新建）
- **总计**: 12个 Shell 脚本

### 实验运行
- 每个配置运行 10 个任务（conv-26, conv-30, conv-41~50）
- 总实验数: 12 × 10 = 120 个任务执行
- 预计总时间: 12 × 10 × 3小时 = 360小时（并行可缩短）

---

## 🎓 总结

遵循本指南，你将能够：

1. ✅ 为 Mem0ᵍ 和 MemoryOS 生成 8 个配置文件
2. ✅ 为 Mem0ᵍ 和 MemoryOS 生成 8 个执行脚本
3. ✅ 确保所有配置符合 B3 实验组的设计要求
4. ✅ 保持与 TiM 已有配置的一致性
5. ✅ 验证所有文件的正确性和可执行性

完成后，B3 实验组（PreRetrieval 维度探索）将拥有完整的实验基础设施，可以系统性地对比四种查询优化策略在三种记忆数据结构上的效果。

---

**祝实现顺利！🚀**
