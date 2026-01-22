# Llama-3.1-8B Backbone 补充实验 (Additional Experiments - Data Structure with Llama)

## 实验目的
针对ICML审稿人关于"仅使用Pangu 1B模型"的评审意见，本目录包含使用 **Llama-3.1-8B-Instruct** 作为Backbone的补充实验配置。

## 文件夹命名
- **配置目录**: `benchmarks/experiment/config/additional_experiments_ds_llama/`
- **脚本目录**: `benchmarks/experiment/script/additional_experiments_ds_llama/`

## 实验设置
- **数据集**: LoCoMo
- **Backbone模型**: Llama-3.1-8B-Instruct (替代 pangu_embedded_1b)
- **Embedding模型**: BAAI/bge-m3 (保持一致)
- **测试维度**: D1 Memory Data Structure (11种配置)

## 配置文件列表
所有配置文件均从 `memory_data_structure/` 目录复制并修改LLM配置：

1. `llama_feature_queue_segment_pipeline.yaml` - Feature+Queue+Segment三索引
2. `llama_feature_queue_summary_pipeline.yaml` - Feature+Queue+Summary三索引 (LDAgent)
3. `llama_feature_queue_vector_pipeline.yaml` - Feature+Queue+Vector三索引 (MemGPT)
4. `llama_feature_summary_vector_pipeline.yaml` - Feature+Summary+Vector三索引 (MemoryBank)
5. `llama_fifo_queue_pipeline.yaml` - FIFO队列基线 (SCM)
6. `llama_inverted_vectorstore_pipeline.yaml` - Inverted+Vector双索引 (Mem0)
7. `llama_linknote_graph_pipeline.yaml` - Linknote图结构 (A-Mem)
8. `llama_lsh_hash_pipeline.yaml` - LSH近似检索 (TiM)
9. `llama_property_graph_pipeline.yaml` - 属性图 (Mem0ᵍ)
10. `llama_segment_pipeline.yaml` - 时间分段管理
11. `llama_semantic_kg_pipeline.yaml` - 语义倒排知识图谱 (HippoRAG)

## LLM配置差异
```yaml
# 原配置 (Pangu 1B)
api_key: "iloveshuhao"
base_url: "http://172.17.0.1:1040/v1"
model_name: "pangu_embedded_1b"
llm_base_url: "http://172.17.0.1:1040/v1"
llm_model: "pangu_embedded_1b"

# 新配置 (Llama-3.1-8B)
api_key: "token-abc123"
base_url: "http://sage2:8000/v1"
model_name: "/home/cyb/Llama-3.1-8B-Instruct"
llm_base_url: "http://sage2:8000/v1"
llm_model: "/home/cyb/Llama-3.1-8B-Instruct"
```

## 运行方式
```bash
# 方式1: 使用配置目录下的批量脚本
cd /home/xty/NeuroMem/benchmarks/experiment/config/additional_experiments_ds_llama
bash run_all_experiments.sh

# 方式2: 使用script目录下的单个脚本
cd /home/xty/NeuroMem
bash benchmarks/experiment/script/additional_experiments_ds_llama/run_llama_feature_queue_vector.sh

# 方式3: 批量运行所有脚本
cd /home/xty/NeuroMem
for script in benchmarks/experiment/script/additional_experiments_ds_llama/run_llama_*.sh; do
  bash "$script"
done
```

## 预期产出
- 所有11种Memory Data Structure在Llama-3.1-8B下的F1分数
- 插入/检索延迟对比
- 与Pangu 1B结果的对比分析，证明STREAM发现的规律不依赖于特定模型
