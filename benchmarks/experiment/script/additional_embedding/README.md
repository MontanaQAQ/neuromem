# 补充实验：e5-large-v2 Embedding 对比

## 实验目的

对比不同 embedding 模型对 D2 (Normalization Strategy) 实验的影响：
- **原始实验**: BAAI/bge-m3 (port 8091)
- **补充实验**: intfloat/e5-large-v2 (port 8092)

## 实验设置

### 控制变量
- **数据集**: Locomo
- **记忆结构**: Mem0g (Semantic Inverted Knowledge Graph)
- **任务数量**: 10个对话 (conv-26, 30, 41-44, 47-50)

### 实验变量
- **D2 (PreInsert)**:
  - None (无预处理)
  - Rewrite (三元组提取)

### 实验配置

| 实验组 | Embedding模型 | Port | PreInsert | 配置文件 |
|--------|---------------|------|-----------|---------|
| 对照组1 | BAAI/bge-m3 | 8091 | None | normalization_strategy/Mem0g_locomo_none_pre_insert_pipeline.yaml |
| 对照组2 | BAAI/bge-m3 | 8091 | Rewrite | normalization_strategy/Mem0g_locomo_rewrite_triplet_extract_pre_insert_pipeline.yaml |
| **实验组1** | **intfloat/e5-large-v2** | **8092** | **None** | **additional_embedding/Mem0g_locomo_none_e5_large.yaml** |
| **实验组2** | **intfloat/e5-large-v2** | **8092** | **Rewrite** | **additional_embedding/Mem0g_locomo_rewrite_e5_large.yaml** |

## 使用指南

### 1. 启动 Embedding Server

```bash
# 确保在 SAGE 项目目录下
cd /home/zrc/develop_item/SAGE

# 启动 e5-large-v2 embedding server (GPU 1, port 8092)
HF_ENDPOINT=https://hf-mirror.com python packages/sage-common/src/sage/common/components/sage_embedding/embedding_server.py \
  --model intfloat/e5-large-v2 \
  --port 8092 \
  --gpu 1
```

### 2. 运行实验

```bash
# 切换到 neuromem 项目目录
cd /home/zrc/develop_item/bench/neuromem

# 方案A: 运行所有实验
bash benchmarks/experiment/script/additional_embedding/run_all_e5_large.sh

# 方案B: 单独运行实验
bash benchmarks/experiment/script/additional_embedding/run_mem0g_none_e5_large.sh
bash benchmarks/experiment/script/additional_embedding/run_mem0g_rewrite_e5_large.sh
```

### 3. 查看结果

实验输出路径：
```
.sage/output/benchmarks/benchmark_memory/locomo/
├── Additional_Mem0g_none_e5_large/      # Mem0g + None + e5-large-v2
│   ├── conv-26_HHMMSS/
│   ├── conv-30_HHMMSS/
│   └── ...
└── Additional_Mem0g_rewrite_e5_large/   # Mem0g + Rewrite + e5-large-v2
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
python benchmarks/experiment/script/additional_embedding/quick_compare.py
```

输出示例：
```
【None 策略 - Embedding 对比】
  bge-m3:      F1 = 0.7234 (±0.1234)
  e5-large-v2: F1 = 0.7456 (±0.1156)
  Δ F1:        +0.0222 (+3.07%)

  bge-m3:      Retrieval = 45.23 ms
  e5-large-v2: Retrieval = 48.56 ms
  Δ Time:      +3.33 ms (+7.36%)
```

### 完整分析

```bash
# 生成完整的图表和报告
bash benchmarks/experiment/script/additional_embedding/analyze_e5_large_comparison.sh
```

### 分析维度

1. **检索效果对比**
   - F1 Score (Token-level)
   - Category-wise F1
   - 各轮次表现趋势

2. **Embedding 质量对比**
   - bge-m3 vs e5-large-v2 检索准确率
   - 向量检索时间对比
   - 成本效益分析

3. **PreInsert 策略影响**
   - None vs. Rewrite 在不同 embedding 下的表现差异
   - 插入时间开销对比

### 生成的分析结果

结果路径：`.sage/benchmarks/benchmark_memory/locomo/output/round_analysis_additional_embedding/`

**图表文件**：
- `comparison_f1.png` - F1 分数对比曲线
- `comparison_insert_time.png` - 插入时间对比
- `comparison_retrieval_time.png` - 检索时间对比
- `comparison_cost_effectiveness.png` - 成本效益分析
- `comparison_category_f1.png` - 各类别问题准确率对比

**数据文件**：
- `f1_scores.csv` - F1 分数数据表
- `insert_times.csv` - 插入时间数据
- `retrieval_times.csv` - 检索时间数据
- `category_f1_scores.csv` - 各类别 F1 分数

**报告**：
- `analysis_report.md` - 完整分析报告（包含统计数据和结论）

### 对比组

| 组别 | Embedding模型 | PreInsert策略 | 实验目录 |
|------|---------------|---------------|----------|
| 对照1 | bge-m3 | None | PreInsert_Mem0g_none |
| 实验1 | e5-large-v2 | None | Additional_Mem0g_none_e5_large |
| 对照2 | bge-m3 | Rewrite | PreInsert_Mem0g_rewrite_triplet_extract |
| 实验2 | e5-large-v2 | Rewrite | Additional_Mem0g_rewrite_e5_large |

## 注意事项

1. **端口冲突**: 确保 port 8092 未被占用
2. **GPU资源**: embedding server 运行在 GPU 1
3. **磁盘空间**: 每个实验约占用 100-500MB
4. **运行时间**: 预计每个任务 5-10 分钟，总共约 2-4 小时

## 更新日志

- 2026-01-26: 创建补充实验框架，配置 e5-large-v2 embedding 对比实验
