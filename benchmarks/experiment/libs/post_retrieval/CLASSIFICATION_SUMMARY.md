# PostRetrieval 分类依据总结

## 分类依据：操作类型 (Operation Type)

`post_retrieval` 目录按照**对检索结果的操作类型**分为四大类：

```
post_retrieval/
├── rerank/      # 重排序 - 调整结果顺序
├── filter/      # 过滤 - 减少结果数量
├── merge/       # 合并 - 整合多次检索
└── augment/     # 增强 - 添加额外信息
```

---

## 当前已实现算子清单

### 1. Rerank (重排序) - 4个

| 算子 | 注册名 | 对应论文 | 核心逻辑 |
|-----|--------|---------|---------|
| SemanticRerankAction | `rerank.semantic` | 通用 | LLM语义理解重排 |
| TimeWeightedRerankAction | `rerank.time_weighted` | MemoryBank | $score = sim \times e^{-decay \times t}$ |
| PPRRerankAction | `rerank.ppr` | HippoRAG | Personalized PageRank图遍历 |
| WeightedRerankAction | `rerank.weighted` | LD-Agent | 语义+时间+话题多因子加权 |

### 2. Filter (过滤) - 3个

| 算子 | 注册名 | 对应论文 | 核心逻辑 |
|-----|--------|---------|---------|
| TopKFilterAction | `filter.top_k` | 通用 | 保留分数最高的K个结果 |
| ThresholdFilterAction | `filter.threshold` | Mem0 | 过滤低于阈值的结果 |
| TokenBudgetFilterAction | `filter.token_budget` | SCM | 限制总token数量 |

### 3. Merge (合并) - 4个

| 算子 | 注册名 | 对应论文 | 核心逻辑 |
|-----|--------|---------|---------|
| MultiQueryMergeAction | `merge.multi_query` | MemoryOS | 多次查询结果Union/Intersection |
| MultiTierMergeAction | `merge.multi_tier` | MemGPT | RRF融合多层检索结果 |
| LinkExpandMergeAction | `merge.link_expand` | A-Mem | 扩展图邻居节点 |
| SCMThreeWayMergeAction | `scm_three_way` | SCM | Drop/Summary/Raw三元决策 |

### 4. Augment (增强) - 2个

| 算子 | 注册名 | 对应论文 | 核心逻辑 |
|-----|--------|---------|---------|
| AugmentAction | `augment` | MemoryOS | 添加persona/traits/summary上下文 |
| ReinforceAction | `augment.reinforce` | MemoryBank | 更新记忆访问强度 |

**总计**: 13个算子 (4+3+4+2)

---

## 12篇论文覆盖情况

### ? 已完全覆盖 (9篇)

| # | 论文 | 对应算子 | 算子类别 |
|---|------|---------|---------|
| 1 | MemoryBank | `rerank.time_weighted`, `augment.reinforce` | Rerank + Augment |
| 2 | MemGPT | `merge.multi_tier` | Merge |
| 3 | A-Mem | `merge.link_expand` | Merge |
| 4 | HippoRAG | `rerank.ppr` | Rerank |
| 5 | HippoRAG2 | `rerank.ppr` | Rerank |
| 6 | MemoryOS | `merge.multi_query`, `augment` | Merge + Augment |
| 7 | LD-Agent | `rerank.weighted` | Rerank |
| 8 | SCM | `filter.token_budget`, `scm_three_way` | Filter + Merge |
| 9 | Mem0 | `filter.threshold` | Filter |

### ?? 部分覆盖 (2篇)

| # | 论文 | 现有算子 | 缺失内容 |
|---|------|---------|---------|
| 10 | Mem0? | `rerank.ppr` (可复用) | 需验证有向图适配性 |
| 11 | TiM | `rerank.semantic` (通用) | 缺LSH桶过滤 |

### ? 未覆盖 (1篇)

| # | 论文 | 需要算子 | 优先级 |
|---|------|---------|--------|
| 12 | SeCom | `filter.semantic_cluster` | ? 中 |

---

## 四类可适配数据结构

### 按数据结构推荐算子

| 数据结构 | Rerank | Filter | Merge | Augment |
|---------|--------|--------|-------|---------|
| **分层式** (MemoryBank, MemGPT, MemoryOS, LD-Agent) | ? `time_weighted` | ? `token_budget` | ? `multi_tier` | ? `augment` |
| **图结构** (A-Mem, HippoRAG, Mem0?) | ? `ppr` | ? `threshold` | ? `link_expand` | ?? `reinforce` |
| **分区式** (TiM, SCM, SeCom) | ? `semantic` | ? `token_budget` | ? `scm_three_way` | ?? `reinforce` |
| **混合式** (Mem0) | ? `weighted` | ? `threshold` | ?? `multi_query` | ?? `augment` |

**图例**:
- ? 原生支持，可直接使用
- ?? 可适配但需扩展metadata

---

## 每类挑选一个代表算子

根据以下标准进行选择：
1. **适配性广**: 支持多种数据结构
2. **实用性强**: 解决实际问题
3. **论文覆盖**: 对应主流论文
4. **性能稳定**: 易于测试和调优

### 最终推荐

| 类别 | 推荐算子 | 理由 |
|------|---------|------|
| **Rerank** | `time_weighted` | ? 适配分层/分区式结构<br>? 有数学理论基础(Ebbinghaus)<br>? 对应MemoryBank论文 |
| **Filter** | `token_budget` | ? 解决实际长文本问题<br>? 适配所有结构<br>? 对应SCM论文 |
| **Merge** | `multi_tier` | ? 典型分层融合模式<br>? RRF算法成熟<br>? 对应MemGPT论文 |
| **Augment** | `augment` | ? 完整上下文增强<br>? 适配分层结构<br>? 对应MemoryOS论文 |

---

## 补充算子优先级

### ? 高优先级 (TiM)
```python
# filter/lsh_bucket.py
class LSHBucketFilterAction:
    """LSH哈希桶过滤 (TiM论文)"""
```
**理由**: TiM论文影响力大，LSH是其核心特性

### ? 中优先级 (SeCom)
```python
# filter/semantic_cluster.py
class SemanticClusterFilterAction:
    """语义聚类过滤 (SeCom论文)"""
```
**理由**: 语义聚类有通用价值

### ? 低优先级 (验证性工作)
- 验证 `rerank.ppr` 对 Mem0? 有向图的支持
- 扩展 `augment.reinforce` 到图结构

---

## 总结

### ? 现状
- **13个算子** 覆盖 **4大类操作**
- **9/12篇论文** 完全覆盖
- 每类都有 **2-4个** 可选算子
- 支持 **4种数据结构** (分层/图/分区/混合)

### ? 结论
**每一类都可以挑选出适配各种数据结构的算子**，现有实现已满足主要需求。补充2-3个算子后可达到100%论文覆盖。

### ? 推荐配置
```yaml
# 通用配置 (适配大多数数据结构)
operators:
  post_retrieval:
    action: "rerank"
    rerank_type: "time_weighted"  # 时间加权重排
    time_decay_rate: 0.1

    # 或使用过滤
    # action: "filter"
    # filter_type: "token_budget"
    # max_tokens: 2000

    # 或使用合并
    # action: "merge"
    # merge_type: "multi_tier"

    # 或使用增强
    # action: "augment"
```
