# Pre-Insert Actions 设计维度

## 维度总览（4个维度）

| 维度 | 职责 | Action数量 |
|------|------|-----------|
| **None (透传)** | 无操作，直接传递原始数据 | 1 |
| Extract | 从原始数据提取结构化信息 | 6 |
| Score | 计算数据的重要性/优先级 | 2 |
| Transform | 转换数据格式以适配存储 | 2 |

> **💡 透传操作**: `none_action.py` 用于不需要预处理的系统（如 HippoRAG2, SCM），直接传递原始数据。

---

## 1. Extract 维度

**目的**: 将非结构化文本转换为可索引的结构化数据

| Action | 功能 | 输出格式 | 应用系统 |
|--------|------|---------|---------|
| **entity.py** | 实体提取 | 实体列表 [人名/地名/组织...] | 知识图谱、实体索引 |
| **fact.py** | 事实提取 | 事实陈述列表 | 事实验证、知识库 |
| **keyword.py** | 关键词提取 | 关键词列表 + 权重 | BM25检索、标签系统 |
| **triple.py** | 三元组提取 | SPO三元组 [(主语,谓语,宾语)...] | 知识图谱、关系推理 |
| **noun.py** | 名词短语提取 | 名词短语列表 | 概念索引 |
| **multi_summary.py** | 多粒度摘要 | 不同长度的摘要 (短/中/长) | 层次化索引、快速预览 |

**技术特点**:
- 可组合：一次插入可同时提取多种信息
- 增量式：不破坏原始数据，只添加元数据
- 粒度范围：从细粒度（实体）到粗粒度（摘要）

---

## 2. Score 维度

**目的**: 量化数据的重要性，为后续维护提供依据

| Action | 评分依据 | 评分范围 | 应用场景 |
|--------|---------|---------|---------|
| **heat.py** | 访问频率 + 最近访问时间 | 0.0 - 1.0 | MemoryOS热度迁移、容量淘汰 |
| **importance.py** | 语义重要性 + 关键性 | 0.0 - 1.0 | 优先级队列、选择性保留 |

**评分公式示例**:
```python
# heat.py
heat_score = alpha * access_freq + (1-alpha) * recency

# importance.py  
importance = w1*semantic_score + w2*keyword_density + w3*novelty
```

**用途**:
- 容量管理：删除低分记忆
- 分层存储：高分→高层，低分→低层
- 检索排序：优先返回高分结果

---

## 3. Transform 维度

**目的**: 转换数据格式以适配不同存储后端

| Action | 转换类型 | 参数 | 应用场景 |
|--------|---------|------|---------|
| **chunking.py** | 文本分块 | chunk_size, overlap | 向量数据库（长度限制）、LLM上下文窗口 |
| **continuity_check.py** | 时序连续性检查 | time_gap_threshold | 对话历史、时间序列数据 |

**Chunking策略**:
```python
# 固定大小分块
chunks = split_by_size(text, size=512, overlap=50)

# 语义分块
chunks = split_by_semantics(text, method="sentence_bert")

# 层次分块
chunks = hierarchical_split(text, levels=[128, 512, 2048])
```

**Continuity Check逻辑**:
```python
# 检查时间间隔
if current_time - last_time > threshold:
    insert_continuity_marker()
```

---

## 组合使用示例

### 场景1: 长文档RAG（HippoRAG）
```yaml
pre_insert:
  - extract.multi_summary    # 多级摘要索引
  - extract.triple           # 构建知识图谱
  - transform.chunking       # 切分为检索单元
  - score.importance         # 评估chunk重要性
```

### 场景2: 对话记忆（MemoryOS）
```yaml
pre_insert:
  - extract.entity           # 提取对话实体
  - score.heat               # 计算访问热度
  - transform.continuity_check  # 确保对话连续
```

### 场景3: 知识库构建
```yaml
pre_insert:
  - extract.triple           # SPO三元组
  - extract.entity           # 实体识别
  - extract.keyword          # 关键词索引
  - score.importance         # 知识重要性
```

---

## 与后续阶段的衔接

```
Pre-Insert输出 → 用于后续阶段

Extract结果:
  - triple → Post-Insert的graph_construction（构建图）
  - entity → Retrieval的实体匹配
  - summary → Retrieval的快速预览

Score结果:
  - heat → Post-Insert的tier_migration（热度迁移）
  - importance → Post-Insert的decay_eviction（重要性保留）

Transform结果:
  - chunks → Retrieval的检索单元
  - continuity → Post-Insert的时序维护
```
