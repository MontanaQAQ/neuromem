# 补充实验：Llama-3-8B PostRetrieval 策略对比

## 实验目的

对比不同 LLM 模型对 D5 (Integration/PostRetrieval) 实验的影响：
- **原始实验**: PanGu Embedded 1B (本地 1040 端口)
- **补充实验**: Llama-3-8B-Instruct (sage2:8001)

## 实验设置

### 控制变量
- **数据集**: Locomo
- **记忆结构**: Mem0g (Semantic Inverted Knowledge Graph)
- **任务数量**: 10个对话 (conv-26, 30, 41-44, 47-50)
- **Embedding**: BAAI/bge-m3 (port 8091)

### 实验变量
- **D5 (PostRetrieval)**:
  - Augment (结果增强)
  - Multi-query (多查询检索)

### 实验配置

| 实验组 | LLM模型 | PostRetrieval | 配置文件 |
|--------|---------|---------------|---------|
| **实验组1** | **Llama-3-8B** | **Augment** | **Mem0g_locomo_augment_post_retrieval_pipeline.yaml** |
| **实验组2** | **Llama-3-8B** | **Multi-query** | **Mem0g_locomo_multi_query_post_retrieval_pipeline.yaml** |

## 使用指南

### 1. 确保 Llama 服务运行

```bash
# 测试 Llama 服务连接
curl -X POST "http://sage2:8001/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token-abc123" \
  -d '{
    "model": "meta-llama/Meta-Llama-3-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 32
  }'
```

### 2. 运行实验

```bash
# 切换到 neuromem 项目目录
cd /home/zrc/develop_item/bench/neuromem

# 方案A: 运行所有实验
bash benchmarks/experiment/script/additional_model_llama/run_all_llama.sh

# 方案B: 单独运行实验
bash benchmarks/experiment/script/additional_model_llama/run_mem0g_augment_llama.sh
bash benchmarks/experiment/script/additional_model_llama/run_mem0g_multi_query_llama.sh
```

### 3. 查看结果

实验输出路径：
```
.sage/output/benchmarks/benchmark_memory/locomo/
├── PostRetrieval_Mem0g_augment_Llama/       # Mem0g + Augment + Llama
│   ├── conv-26_HHMMSS/
│   ├── conv-30_HHMMSS/
│   └── ...
└── PostRetrieval_Mem0g_multi_query_Llama/   # Mem0g + Multi-query + Llama
    ├── conv-26_HHMMSS/
    └── ...
```

每个任务目录包含：
- `terminal.log`: 完整执行日志
- `memory_operations.jsonl`: 内存操作记录
- `qa_results.json`: 问答结果
- `metrics.json`: 评估指标

## 数据分析

### 快速查看结果

```bash
# 快速对比关键指标（无需生成图表）
python benchmarks/experiment/script/additional_model_llama/quick_compare.py
```

输出示例：
```
【PostRetrieval 策略对比 - Llama-3-8B】
  Augment:      F1 = 0.7456 (±0.1234)
  Multi-query:  F1 = 0.7823 (±0.1156)
  Δ F1:        +0.0367 (+4.92%)

  Augment:      Retrieval = 52.34 ms
  Multi-query:  Retrieval = 78.56 ms
  Δ Time:      +26.22 ms (+50.09%)
```

### 完整分析

```bash
# 生成完整的图表和报告
bash benchmarks/experiment/script/additional_model_llama/analyze_llama_comparison.sh
```

### 分析维度

1. **检索效果对比**
   - F1 Score (Token-level)
   - Category-wise F1
   - 各轮次表现趋势

2. **PostRetrieval 策略影响**
   - Augment vs Multi-query 在 Llama 模型下的表现
   - 检索时间开销对比
   - 成本效益分析

3. **LLM 模型影响**
   - Llama-3-8B 对 PostRetrieval 策略的影响
   - 与 PanGu 1B 的对比分析

### 生成的分析结果

结果路径：`.sage/benchmarks/benchmark_memory/locomo/output/round_analysis_additional_model_llama/`

**图表文件**：
- `comparison_f1.png` - F1 分数对比曲线
- `comparison_retrieval_time.png` - 检索时间对比
- `comparison_cost_effectiveness.png` - 成本效益分析
- `comparison_category_f1.png` - 各类别问题准确率对比

**数据文件**：
- `f1_scores.csv` - F1 分数数据表
- `retrieval_times.csv` - 检索时间数据
- `category_f1_scores.csv` - 各类别 F1 分数

**报告**：
- `analysis_report.md` - 完整分析报告（包含统计数据和结论）

### 对比组

| 组别 | LLM模型 | PostRetrieval策略 | 实验目录 |
|------|---------|-------------------|----------|
| 实验1 | Llama-3-8B | Augment | PostRetrieval_Mem0g_augment_Llama |
| 实验2 | Llama-3-8B | Multi-query | PostRetrieval_Mem0g_multi_query_Llama |

## 注意事项

1. **网络连接**: 确保能访问 sage2:8001 服务器
2. **API认证**: 使用正确的 API key (token-abc123)
3. **磁盘空间**: 每个实验约占用 100-500MB
4. **运行时间**: 预计每个任务 5-10 分钟，总共约 2-4 小时
5. **模型差异**: Llama-3-8B 比 PanGu 1B 性能更强，预期 F1 分数更高

## 更新日志

- 2026-01-26: 创建补充实验框架，配置 Llama-3-8B PostRetrieval 对比实验
