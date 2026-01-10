# B3实验组使用说明

## 📋 概述

B3实验组探索**PreRetrieval（查询优化）**维度，对比四种查询优化策略在两种数据结构上的效果：

- **数据结构**: Mem0ᵍ、MemoryOS
- **PreRetrieval策略**: embedding、validate、keyword_extract、decompose
- **总实验数**: 8个配置 × 10个任务 = 80次运行

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate sage-mem

# 验证Python版本
python --version  # 应为 3.11.x

# 验证配置文件
python test_b3_configs.py
```

### 2. 服务检查

确保以下服务正常运行：

```bash
# LLM服务（Llama-3.1-8B）
curl http://sage2:8000/v1/models

# Embedding服务（BGE-M3）
curl http://localhost:8091/v1/models
```

### 3. 快速测试

运行每个配置的1个任务，验证流程：

```bash
./test_b3_quick.sh
```

### 4. 运行单个实验

```bash
# Mem0g - embedding
bash benchmarks/experiment/script/query_formulation_strategy/run_mem0g_locomo_embedding.sh

# MemoryOS - keyword_extract
bash benchmarks/experiment/script/query_formulation_strategy/run_memoryos_locomo_keyword_extract.sh
```

### 5. 批量运行

**运行所有Mem0g实验**:
```bash
cd benchmarks/experiment/script/query_formulation_strategy/
for script in run_mem0g_*.sh; do
    echo "执行: $script"
    bash "$script"
done
```

**运行所有MemoryOS实验**:
```bash
cd benchmarks/experiment/script/query_formulation_strategy/
for script in run_memoryos_*.sh; do
    echo "执行: $script"
    bash "$script"
done
```

**运行所有B3实验**:
```bash
cd benchmarks/experiment/script/query_formulation_strategy/
for script in run_mem0g_*.sh run_memoryos_*.sh; do
    echo "执行: $script"
    bash "$script"
done
```

## 📂 文件组织

### 配置文件

```
benchmarks/experiment/config/query_formulation_strategy/
├── Mem0g_locomo_embedding_pre_retrieval_pipeline.yaml
├── Mem0g_locomo_validate_pre_retrieval_pipeline.yaml
├── Mem0g_locomo_keyword_extract_pre_retrieval_pipeline.yaml
├── Mem0g_locomo_decompose_pre_retrieval_pipeline.yaml
├── MemoryOS_locomo_embedding_pre_retrieval_pipeline.yaml
├── MemoryOS_locomo_validate_pre_retrieval_pipeline.yaml
├── MemoryOS_locomo_keyword_extract_pre_retrieval_pipeline.yaml
└── MemoryOS_locomo_decompose_pre_retrieval_pipeline.yaml
```

### 执行脚本

```
benchmarks/experiment/script/query_formulation_strategy/
├── run_mem0g_locomo_embedding.sh
├── run_mem0g_locomo_validate.sh
├── run_mem0g_locomo_keyword_extract.sh
├── run_mem0g_locomo_decompose.sh
├── run_memoryos_locomo_embedding.sh
├── run_memoryos_locomo_validate.sh
├── run_memoryos_locomo_keyword_extract.sh
└── run_memoryos_locomo_decompose.sh
```

### 日志输出

```
.sage/output/benchmarks/benchmark_memory/locomo/YYYYMMDD/
├── Mem0g-embedding/
│   ├── conv-26_HHMMSS.log
│   ├── conv-30_HHMMSS.log
│   └── ...
├── Mem0g-validate/
├── Mem0g-keyword_extract/
├── Mem0g-decompose/
├── MemoryOS-embedding/
├── MemoryOS-validate/
├── MemoryOS-keyword_extract/
└── MemoryOS-decompose/
```

## 🔧 配置说明

### PreRetrieval策略对比

| 策略 | 功能 | 适用场景 | 参数 |
|------|------|----------|------|
| **embedding** | 标准向量化 | Baseline | 无 |
| **validate** | 查询质量验证 | 低质量查询过滤 | reject_threshold=0.3 |
| **keyword_extract** | 关键词提取 | 混合检索增强 | max_keywords=5 |
| **decompose** | 查询分解 | 复杂多跳推理 | max_subqueries=3 |

### 数据结构对比

| 维度 | Mem0ᵍ | MemoryOS |
|------|-------|----------|
| **架构** | 语义倒排知识图谱 | 三层STM/MTM/LPM |
| **Service** | `hierarchical.semantic_inverted_knowledge_graph` | `partitional.feature_queue_segment_combination` |
| **PreInsert** | `extract.triple` | `none` |
| **PostInsert** | `crud` | `migrate` |
| **PostRetrieval** | `none` | `merge.multi_query` |

## 📊 实验任务

每个配置运行10个任务：
- conv-26
- conv-30
- conv-41 ~ conv-50

## 🛠️ 故障排查

### 配置文件错误

```bash
# 验证YAML语法
python -c "import yaml; yaml.safe_load(open('path/to/config.yaml'))"

# 运行配置测试
python test_b3_configs.py
```

### 脚本执行错误

```bash
# 检查脚本语法
bash -n benchmarks/experiment/script/query_formulation_strategy/run_mem0g_locomo_embedding.sh

# 检查执行权限
ls -l benchmarks/experiment/script/query_formulation_strategy/*.sh
```

### LLM服务连接失败

```bash
# 检查LLM服务
curl http://sage2:8000/v1/models

# 修改配置文件中的base_url和model_name
```

### Embedding服务连接失败

```bash
# 检查Embedding服务
curl http://localhost:8091/v1/models

# 确保BGE-M3模型已加载
```

## 📈 结果分析

实验完成后，使用以下工具分析结果：

```bash
# 进入评估目录
cd benchmarks/evaluation/

# 运行分析脚本（具体脚本待项目提供）
# python analyze_b3_results.py
```

## 🎯 实验目标

通过B3实验组，我们希望回答：

1. **PreRetrieval策略效果**: 哪种查询优化策略最有效？
2. **数据结构影响**: PreRetrieval策略在不同数据结构上效果如何？
3. **性能对比**: 查询优化的成本与收益如何平衡？
4. **适用场景**: 不同策略适合哪些问题类型？

## 📝 注意事项

1. **时间估计**: 每个任务约3-5分钟，完整实验需约6-8小时
2. **资源占用**: 确保LLM和Embedding服务有足够资源
3. **磁盘空间**: 预留约10GB用于日志存储
4. **并行执行**: 可手动并行运行多个脚本（注意资源）

## 📚 相关文档

- [Query_Formulation_Strategy_Implementation_Guide.md](./Query_Formulation_Strategy_Implementation_Guide.md) - 实现指南
- [B3_Configuration_Completion_Report.md](./B3_Configuration_Completion_Report.md) - 完成报告
- [Data_Structure_Selection_Rationale.md](./Data_Structure_Selection_Rationale.md) - 设计说明

## 🤝 贡献

如发现问题或有改进建议，请联系项目负责人。

---

**最后更新**: 2026-01-09  
**版本**: 1.0  
**维护者**: NeuroMem Team
