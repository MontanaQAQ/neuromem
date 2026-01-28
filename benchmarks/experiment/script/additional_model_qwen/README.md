# 补充实验：Qwen-Plus D2 (Normalization) 实验

## 实验概述

测试 **qwen-plus-2025-12-01** 模型在 D2 (Normalization) 维度下的表现，对比 PreInsert 策略：None vs Rewrite (三元组抽取)。

## LLM 配置

- **模型**: qwen-plus-2025-12-01
- **API**: https://dashscope.aliyuncs.com/compatible-mode/v1
- **API Key**: sk-a2a1a4e27f2646a6a364c432bc13aeb3
- **特殊参数**: enable_thinking=false

## 实验设计

### 对比维度：D2 (PreInsert/Normalization)

| 策略 | 配置 | 说明 |
|------|------|------|
| **None** | `pre_insert: action: "none"` | 直接存储原始对话，无预处理 |
| **Rewrite** | `pre_insert: action: "rewrite.triplet_extract"` | 三元组抽取+规范化 |

### 内存结构

- **Mem0g**: Semantic Inverted Knowledge Graph
  - 向量维度: 1024
  - 层级: 3
  - 路由策略: parallel
  - 默认索引: semantic_index

### 数据集

- **LoCoMo**: 10 个对话任务 (conv-26, 30, 41-44, 47-50)

## 目录结构

```
benchmarks/experiment/
├── config/additional_experiments_ds_qwen/qwen_triple_extraction/
│   ├── Mem0g_locomo_none_qwen.yaml
│   └── Mem0g_locomo_rewrite_qwen.yaml
└── script/additional_model_qwen/
    ├── run_mem0g_none_qwen.sh
    ├── run_mem0g_rewrite_qwen.sh
    ├── run_all_qwen.sh
    ├── analyze_qwen_comparison.sh
    ├── quick_compare.py
    └── README.md (本文件)
```

## 运行方式

### 1. 运行单个实验

```bash
# Mem0g + None
bash benchmarks/experiment/script/additional_model_qwen/run_mem0g_none_qwen.sh

# Mem0g + Rewrite
bash benchmarks/experiment/script/additional_model_qwen/run_mem0g_rewrite_qwen.sh
```

### 2. 批量运行所有实验

```bash
bash benchmarks/experiment/script/additional_model_qwen/run_all_qwen.sh
```

### 3. 分析结果

```bash
# 使用 round_analyzer 生成完整分析报告
bash benchmarks/experiment/script/additional_model_qwen/analyze_qwen_comparison.sh

# 或使用快速对比工具
cd benchmarks/experiment/script/additional_model_qwen
python quick_compare.py
```

## 输出目录

```
.sage/
├── output/benchmarks/benchmark_memory/locomo/
│   ├── Additional_Qwen_Mem0g_none/          # None 实验结果
│   └── Additional_Qwen_Mem0g_rewrite/       # Rewrite 实验结果
└── benchmarks/benchmark_memory/locomo/output/
    └── round_analysis_additional_model_qwen/  # 分析报告
```

## 对比分析

分析脚本会同时加载 PanGu 和 Qwen 两组实验，生成：

1. **LLM 模型对比**: PanGu-1B vs Qwen-Plus
2. **策略对比**: None vs Rewrite (两个模型分别对比)
3. **最优组合**: 确定模型-策略最佳配置

## 关键指标

- **F1 Score**: Token-level 匹配准确率
- **Retrieval Time**: 检索耗时
- **三元组质量**: Rewrite 策略的抽取效果

## 注意事项

1. **enable_thinking=false**: Qwen 模型需要显式禁用思维链模式
2. **API 限流**: 注意阿里云 API 调用频率限制
3. **对比基准**: 与原始 PanGu 实验保持相同配置（除 LLM 外）

## 预期结果

- Qwen-Plus 作为更强大的模型，预期在三元组抽取质量上优于 PanGu-1B
- Rewrite 策略应带来 F1 提升（特别是在 Qwen 模型下）
- 检索时间可能略有增加（因三元组抽取需 LLM 调用）
