# PostRetrieval 检索后处理实验设计

> 基于三个代表性记忆体结构（TiM, MemoryOS, Mem0g），设计 PostRetrieval 阶段的对比实验
>
> 目标：在不同记忆体架构下，评估检索后处理策略对最终答案质量的影响
>
> 实验范围：PostRetrieval 阶段，固定其他阶段为 baseline 配置

______________________________________________________________________

## ? PostRetrieval 策略分类体系

本实验采用以下统一的策略分类标准，按功能类别划分：

| 类别            | 策略名称               | 功能定位                               | 适用场景                                 |
| --------------- | ---------------------- | -------------------------------------- | ---------------------------------------- |
| **1. 过滤**     | `filter.top_k`         | 保留前K个最高分的记忆条目              | 减少噪声，控制上下文长度                 |
|                 | `filter.threshold`     | 根据分数阈值过滤低质量结果             | 质量保证，过滤弱相关记忆                 |
|                 | `filter.token_budget`  | 根据token预算限制结果数量              | LLM上下文窗口限制                        |
| **2. 重排序**   | `rerank.semantic`      | 基于语义相似度重新排序                 | 向量记忆体（TiM），提升相关性            |
|                 | `rerank.time_weighted` | 基于时间权重重新排序                   | 时间敏感场景，强调新近记忆               |
|                 | `rerank.weighted`      | 多因子加权重排序                       | 综合考虑相似度、时间等多个因子           |
|                 | `rerank.ppr`           | PageRank个性化重排序                   | 图记忆体，利用链接关系                   |
| **3. 合并**     | `merge.multi_query`    | 执行多个查询并合并结果                 | 增强召回，多视角检索（MemGPT）           |
|                 | `merge.multi_tier`     | 合并多层检索结果                       | 层次化记忆（MemoryOS）                   |
|                 | `merge.link_expand`    | 扩展链接关系，引入相关记忆             | 图记忆体，利用结构信息                   |
|                 | `merge.scm_three_way`  | SCM三路合并                            | SCM特定场景                              |
| **4. 增强**     | `augment`              | 添加persona/traits/summary等上下文     | 增强结果可读性，个性化信息补充           |
|                 | `augment.reinforce`    | 更新被检索记忆的强度和时间戳           | MemoryBank遗忘曲线，记忆强化             |
| **5. 无处理**   | `none`                 | 直接使用原始检索结果，不做后处理       | Baseline对比                             |

**分类设计原则**：

- **功能正交**：每个类别功能独立，边界清晰
- **适配性**：不同策略适配不同记忆体架构
- **实验友好**：可按类别设计对比实验矩阵

______________________________________________________________________

## ? 实验设计方案

### 固定基础配置

选择三个代表性记忆体结构，使用其原始配置：

| 记忆体      | 配置文件                                      | 架构特点                         |
| ----------- | --------------------------------------------- | -------------------------------- |
| **TiM**     | `locomo_tim_pipeline.yaml`                    | 向量哈希记忆，基于向量检索       |
| **MemoryOS** | `locomo_memoryos_pipeline.yaml`               | 层次化记忆，三层结构             |
| **Mem0g**   | `locomo_mem0g_pipeline.yaml`                  | 语义倒排知识图谱，图+向量混合    |

### PostRetrieval 策略组合

从四个分类中各选一个代表性操作，加上 `none` 作为baseline：

| 分类        | 选择策略              | 理由                                   |
| ----------- | --------------------- | -------------------------------------- |
| **Filter**  | `filter.top_k`        | 最常用的过滤方法，控制结果数量         |
| **Rerank**  | `rerank.semantic`     | 语义重排序，适用于向量记忆，通用性强   |
| **Merge**   | `merge.multi_query`   | 多查询合并，经典RAG增强方法            |
| **Augment** | `augment`             | 添加上下文信息（persona/traits），增强结果可读性 |
| **None**    | `none`                | 不做后处理，作为baseline               |

### 实验矩阵

**总计：3 个记忆体 × 5 个策略 = 15 组实验**

| 记忆体   | None | Filter.TopK | Rerank.Semantic | Merge.MultiQuery | Augment.Reinforce |
| -------- | ---- | ----------- | --------------- | ---------------- | ----------------- |
| TiM      | ?    | ?           | ?               | ?                | ?                 |
| MemoryOS | ?    | ?           | ?               | ?                | ?                 |
| Mem0g    | ?    | ?           | ?               | ?                | ?                 |

______________________________________________________________________

## ? 配置文件命名规范

```
{记忆体}_{数据集}_{策略}_{阶段}_pipeline.yaml
```

示例：
- `TiM_locomo_none_post_retrieval_pipeline.yaml`
- `TiM_locomo_top_k_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_semantic_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_multi_query_post_retrieval_pipeline.yaml`

______________________________________________________________________

## ?? 配置模板结构

每个配置文件包含以下关键部分：

```yaml
# ============================================================
# PostRetrieval 实验: {记忆体} + {策略}
# 记忆体结构: {记忆体描述}
# PostRetrieval 策略: {策略名称}
# 配置名称: {文件名}
# ============================================================

runtime:
  dataset: locomo
  memory_name: "{记忆体}-{策略}"
  # ... 其他运行时配置从原始配置继承

services:
  # 从原始记忆体配置完整继承
  services_type: "..."
  # ...

operators:
  # 从原始配置继承 pre_insert, post_insert, pre_retrieval
  # 仅修改 post_retrieval 部分

  post_retrieval:
    action: "{策略动作}"
    # 策略特定参数
    # ...
```

______________________________________________________________________

## ? 实验评估指标

### 主要指标

1. **答案质量**
   - 准确率（Accuracy）
   - F1 分数
   - ROUGE/BLEU（生成质量）

2. **效率指标**
   - 检索后处理耗时
   - 最终上下文Token数量
   - 端到端响应时间

3. **记忆质量**
   - 相关记忆召回率
   - 平均相关性分数
   - 噪声记忆比例

### 分析维度

- **策略对比**：同一记忆体下，不同策略的效果对比
- **记忆体对比**：同一策略下，不同记忆体的适配性
- **综合对比**：15组实验的整体表现矩阵

______________________________________________________________________

## ? 实验执行流程

1. **准备阶段**
   - 确认三个基础记忆体配置可正常运行
   - 验证 PostRetrieval 各策略的实现完整性

2. **配置生成**
   - 基于原始配置，生成15个实验配置文件
   - 确保只修改 `post_retrieval` 部分，其他保持一致

3. **实验执行**
   - 按矩阵顺序依次运行实验
   - 记录各指标数据

4. **结果分析**
   - 生成对比报告
   - 分析策略适配性和效果

______________________________________________________________________

## ? 注意事项

1. **策略适配性**：
   - `rerank.semantic` 需要 embedding 支持
   - `merge.multi_query` 需要 LLM 生成查询改写
   - `augment` 需要记忆体支持 persona/traits 获取接口

2. **参数调优**：
   - `top_k`: 建议 5-20
   - `num_queries`: 建议 2-5
   - `augment_type`: persona/traits/summary/metadata
   - `position`: before/after/both

3. **对比公平性**：
   - 固定相同的 LLM、Embedding 模型
   - 固定相同的数据集和测试分片
   - 仅变化 PostRetrieval 配置

______________________________________________________________________

## ? 配置文件清单

### TiM (5个配置)
- `TiM_locomo_none_post_retrieval_pipeline.yaml`
- `TiM_locomo_top_k_post_retrieval_pipeline.yaml`
- `TiM_locomo_semantic_post_retrieval_pipeline.yaml`
- `TiM_locomo_multi_query_post_retrieval_pipeline.yaml`
- `TiM_locomo_augment_post_retrieval_pipeline.yaml`

### MemoryOS (5个配置)
- `MemoryOS_locomo_none_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_top_k_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_semantic_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_multi_query_post_retrieval_pipeline.yaml`
- `MemoryOS_locomo_augment_post_retrieval_pipeline.yaml`

### Mem0g (5个配置)
- `Mem0g_locomo_none_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_top_k_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_semantic_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_multi_query_post_retrieval_pipeline.yaml`
- `Mem0g_locomo_augment_post_retrieval_pipeline.yaml`

______________________________________________________________________

## ? 快速开始

```bash
# 运行单个实验
python main.py --config benchmarks/experiment/config/post_retrieval_strategy/TiM_locomo_none_post_retrieval_pipeline.yaml

# 批量运行所有实验
for config in benchmarks/experiment/config/post_retrieval_strategy/*.yaml; do
    python main.py --config "$config"
done
```

______________________________________________________________________

*实验设计日期：2026年1月13日*
