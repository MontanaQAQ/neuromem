# Post-Retrieval Actions 设计维度

## 维度总览（5个维度）

| 维度 | 职责 | Action数量 |
|------|------|-----------|
| **None (透传)** | 无操作，直接返回结果 | 1 |
| Filter | 过滤和筛选结果 | 3 |
| Rerank | 重新排序结果 | 4 |
| Merge | 合并多路结果 | 4 |
| Augment | 增强结果质量 | 1 |

> **💡 透传操作**: `none_action.py` 用于简单检索系统，直接返回原始检索结果，不做后处理。

---

## 1. Filter 维度

**目的**: 从检索结果中筛选出符合条件的子集

| Action | 过滤标准 | 参数 | 应用场景 |
|--------|---------|------|---------|
| **threshold.py** | 相似度阈值 | min_score (如0.7) | 过滤低质量结果 |
| **top_k.py** | 数量限制 | k (如5) | 限制返回数量 |
| **token_budget.py** | Token预算 | max_tokens (如2048) | LLM上下文窗口限制 |

**Threshold过滤**:
```python
# 相似度过滤
filtered = [result for result in results
            if result.score >= threshold]

# 自适应阈值
threshold = mean(scores) - std(scores)  # 动态阈值
```

**Top-K过滤**:
```python
# 简单Top-K
filtered = results[:k]

# 多样性Top-K（MMR）
filtered = []
while len(filtered) < k:
    best = max(candidates, key=lambda x:
        lambda_val * similarity(query, x) -
        (1-lambda_val) * max_similarity(x, filtered))
    filtered.append(best)
```

**Token Budget过滤**:
```python
# 累积token计数
selected = []
total_tokens = 0
for result in sorted_results:
    tokens = count_tokens(result.content)
    if total_tokens + tokens <= max_tokens:
        selected.append(result)
        total_tokens += tokens
    else:
        break
```

**组合使用**:
```yaml
post_retrieval:
  - filter.threshold: {min_score: 0.7}  # 先过滤低分
  - filter.top_k: {k: 10}               # 再取Top-10
  - filter.token_budget: {max_tokens: 2048}  # 最后限制token
```

---

## 2. Rerank 维度

**目的**: 对检索结果重新排序以提升相关性

| Action | 排序依据 | 权重参数 | 应用场景 |
|--------|---------|---------|---------|
| **semantic.py** | 语义相似度 | 无 | 精准语义匹配 |
| **time_weighted.py** | 时间加权 | alpha (时间衰减系数) | 优先最新信息 |
| **weighted.py** | 多特征加权 | weights={sem:0.7, time:0.2, heat:0.1} | 综合排序 |
| **ppr.py** | PageRank | damping_factor, iterations | 图检索（HippoRAG） |

**Semantic Rerank**:
```python
# 使用更强大的模型重排
scores = cross_encoder.predict([(query, doc) for doc in results])
reranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
```

**Time Weighted Rerank**:
```python
# 时间衰减加权
current_time = now()
for result in results:
    time_diff = current_time - result.timestamp
    time_weight = exp(-alpha * time_diff)
    result.score = result.score * time_weight

reranked = sorted(results, key=lambda x: x.score, reverse=True)
```

**Weighted Rerank**:
```python
# 多特征加权
final_score = (
    w_semantic * semantic_score +
    w_time * time_score +
    w_heat * heat_score +
    w_importance * importance_score
)
```

**PPR (Personalized PageRank)**:
```python
# HippoRAG的图遍历重排
1. 构建查询的Personalized节点集 Q
2. 从Q出发执行PageRank游走
3. 根据节点访问概率重排结果

ppr_scores = personalized_pagerank(
    graph,
    personalization=query_nodes,
    damping=0.85,
    max_iter=100
)
```

**Rerank策略对比**:

| 策略 | 计算成本 | 效果提升 | 适用场景 |
|------|---------|---------|---------|
| semantic | 高（需要模型） | 大 | 语义匹配重要 |
| time_weighted | 低（简单计算） | 中 | 时效性重要 |
| weighted | 低 | 中-大 | 综合排序 |
| ppr | 中-高（图遍历） | 大 | 图检索 |

---

## 3. Merge 维度

**目的**: 合并多路检索结果

| Action | 合并场景 | 合并策略 | 应用场景 |
|--------|---------|---------|---------|
| **multi_query.py** | 多个查询 | 投票/加权平均 | Query Decomposition |
| **multi_tier.py** | 多层记忆 | 优先级合并 | MemoryOS分层检索 |
| **link_expand.py** | 链接扩展 | 相关性传播 | A-Mem链接检索 |
| **scm_three_way.py** | 三路检索 | SCM特定逻辑 | SCM系统 |

**Multi-Query Merge**:
```python
# 场景：查询分解后的多个子查询结果
sub_results = [
    retrieve(sub_q1),  # 结果集1
    retrieve(sub_q2),  # 结果集2
    retrieve(sub_q3)   # 结果集3
]

# 策略1: RRF (Reciprocal Rank Fusion)
def rrf_score(doc, results_lists, k=60):
    score = 0
    for results in results_lists:
        rank = results.index(doc) if doc in results else None
        if rank is not None:
            score += 1 / (k + rank + 1)
    return score

# 策略2: 加权投票
def weighted_vote(doc, results_lists, weights):
    score = 0
    for results, weight in zip(results_lists, weights):
        if doc in results:
            score += weight * (1 / (results.index(doc) + 1))
    return score
```

**Multi-Tier Merge**:
```python
# MemoryOS: STM → MTM → LTM
results_stm = retrieve_from_tier("STM", query, k=5)
results_mtm = retrieve_from_tier("MTM", query, k=10)
results_ltm = retrieve_from_tier("LTM", query, k=20)

# 优先级合并
merged = []
merged.extend(results_stm)  # 优先级最高
if len(merged) < target_k:
    merged.extend(results_mtm[:target_k - len(merged)])
if len(merged) < target_k:
    merged.extend(results_ltm[:target_k - len(merged)])
```

**Link Expand Merge**:
```python
# A-Mem: 初始检索 + 链接扩展
initial_results = retrieve(query, k=5)

# 扩展链接节点
expanded = []
for result in initial_results:
    linked_nodes = get_linked_memories(result)
    expanded.extend(linked_nodes)

# 合并并去重
merged = deduplicate(initial_results + expanded)
merged = rerank_by_relevance(merged, query)
```

**SCM Three-Way Merge**:
```python
# SCM: 短期 + 长期 + 外部知识
short_term = retrieve_from_short_term(query)
long_term = retrieve_from_long_term(query)
external = retrieve_from_external(query)

# SCM特定合并逻辑
merged = scm_fusion(short_term, long_term, external,
                    weights=[0.5, 0.3, 0.2])
```

---

## 4. Augment 维度

**目的**: 增强检索结果的质量和可用性

| Action | 增强方式 | 输出 | 应用场景 |
|--------|---------|------|---------|
| **reinforce.py** | 强化学习增强 | 调整后的结果 | 基于用户反馈优化 |

**Reinforce增强**:
```python
# 基于历史反馈调整检索结果
1. 检索初始结果 results = retrieve(query)
2. 应用强化学习模型调整
   rewards = get_historical_rewards(results, query)
   adjusted_scores = reinforcement_model.adjust(results, rewards)
3. 重排序
   reranked = sorted(results, key=adjusted_scores, reverse=True)

# 训练数据来源：
# - 用户点击率
# - 用户停留时间
# - 明确反馈（点赞/点踩）
```

**Augment vs Rerank**:
- **Rerank**: 基于静态特征重排（相似度、时间等）
- **Augment**: 基于动态学习调整（用户行为、反馈）

---

## 组合使用示例

### 场景1: 标准RAG流程
```yaml
post_retrieval:
  - filter.threshold: {min_score: 0.7}    # 过滤低分
  - rerank.semantic                       # 语义重排
  - filter.top_k: {k: 5}                 # 取Top-5
  - filter.token_budget: {max_tokens: 2048}  # Token限制
```

### 场景2: Multi-Query检索（HippoRAG）
```yaml
post_retrieval:
  - merge.multi_query                     # 合并子查询结果
  - rerank.ppr                            # PPR图遍历重排
  - filter.top_k: {k: 10}                # 取Top-10
```

### 场景3: 分层检索（MemoryOS）
```yaml
post_retrieval:
  - merge.multi_tier                      # 合并STM/MTM/LTM
  - rerank.time_weighted                  # 时间加权
  - filter.token_budget: {max_tokens: 4096}
```

### 场景4: 链接扩展检索（A-Mem）
```yaml
post_retrieval:
  - merge.link_expand                     # 扩展链接节点
  - filter.threshold: {min_score: 0.6}   # 过滤低相关
  - rerank.weighted: {sem: 0.6, link: 0.4}  # 综合排序
  - filter.top_k: {k: 8}
```

### 场景5: 强化学习优化
```yaml
post_retrieval:
  - filter.threshold: {min_score: 0.65}
  - rerank.semantic
  - augment.reinforce                     # 基于反馈调整
  - filter.top_k: {k: 5}
```

---

## 推荐处理顺序

```
1. Merge      → 先合并多路结果（如有）
2. Filter     → 粗过滤（threshold）
3. Rerank     → 重排序（语义/时间/图）
4. Augment    → 增强（可选）
5. Filter     → 细过滤（top_k, token_budget）
```

**原因**:
- Merge先行：避免重复处理多路结果
- 粗过滤早：减少后续计算量
- Rerank中间：在有限集合上排序
- Augment可选：需要时才用
- 细过滤最后：精确控制输出

---

## 性能优化建议

### 1. 早期过滤
```python
# 在Rerank前先Filter，减少计算量
results = retrieve(query, k=100)
results = filter_threshold(results, min_score=0.7)  # 假设剩50个
results = rerank_semantic(results)  # 只需重排50个
```

### 2. 缓存Rerank结果
```python
# 相同查询+相同结果集 → 复用rerank结果
@lru_cache(maxsize=500)
def cached_rerank(query_hash, results_hash):
    return rerank(query, results)
```

### 3. 并行Merge
```python
# 多路检索并行执行
with ThreadPoolExecutor() as executor:
    futures = [
        executor.submit(retrieve_from_tier, tier, query)
        for tier in ["STM", "MTM", "LTM"]
    ]
    tier_results = [f.result() for f in futures]
    merged = merge_multi_tier(tier_results)
```

### 4. 增量Token Budget
```python
# 边检索边计数，避免检索过多
results = []
total_tokens = 0
for chunk in retrieve_stream(query):
    tokens = count_tokens(chunk)
    if total_tokens + tokens <= max_tokens:
        results.append(chunk)
        total_tokens += tokens
    else:
        break  # 提前终止
```

---

## 与其他阶段的衔接

```
Post-Retrieval优化 → 最终输出

Pre-Retrieval:
  - decompose → Post-Retrieval的multi_query merge
  - route → Post-Retrieval的多路merge

Retrieval:
  - 多层检索 → Post-Retrieval的multi_tier merge
  - 图检索 → Post-Retrieval的ppr rerank
  - 链接检索 → Post-Retrieval的link_expand merge

输出到LLM:
  - token_budget确保不超过上下文窗口
  - rerank确保最相关内容在前
```

---

## 评估指标

| 指标 | 评估内容 | 适用维度 |
|------|---------|---------|
| **Precision@K** | Top-K准确率 | Filter, Rerank |
| **Recall@K** | Top-K召回率 | Merge |
| **MRR** | 平均倒数排名 | Rerank |
| **NDCG** | 归一化折损累计增益 | Rerank |
| **Latency** | 处理延迟 | 所有维度 |
| **Token Efficiency** | Token利用率 | Filter (token_budget) |
