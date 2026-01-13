# Post-Insert Actions 设计维度

## 维度总览（5个策略维度）

| 策略维度 | 设计意图 | Action数量 | 代表系统 |
|---------|---------|-----------|---------|
| **None (透传)** | 无后续维护操作 | 1 | HippoRAG2, SCM |
| Conflict Resolution | 解决记忆冲突和重复 | 2 | Mem0, MemGPT, TiM |
| Decay Eviction | 遗忘过时记忆 | 2 | MemoryBank, LD-Agent |
| Structure Enrichment | 增强记忆结构 | 2 | A-Mem, HippoRAG |
| Tier Migration | 分层记忆迁移 | 1 | MemoryOS |

> **设计理念**: Post-Insert采用"策略分类"而非"功能分类"，因为这些操作的触发机制和执行逻辑高度依赖系统的整体记忆管理策略。
>
> **💡 透传操作**: `none_action.py` 用于不需要后插入维护的系统，插入后不做任何处理。

---

## 1. Conflict Resolution（冲突解决）

**策略意图**: 当新记忆与已有记忆冲突时，通过LLM决策进行CRUD操作

| Action | 决策方式 | 可用操作 | 触发机制 |
|--------|---------|---------|---------|
| **llm_crud.py** | LLM判断 | ADD, UPDATE, DELETE, NOOP | 检索相似记忆后 |
| **semantic_consolidation.py** | 语义合并 | MERGE, NOOP | 相似度超过阈值 |

**LLM CRUD决策流程**:
```python
1. 插入新记忆 memory_new
2. 检索相似记忆 similar_memories = retrieve(memory_new, top_k=5)
3. LLM决策:
   prompt = f"新记忆: {memory_new}\n相似记忆: {similar_memories}\n决策: ADD/UPDATE/DELETE/NOOP?"
   decision = llm(prompt)
4. 执行决策:
   - ADD: 直接添加
   - UPDATE: 更新某条已有记忆
   - DELETE: 删除冲突记忆后添加
   - NOOP: 什么都不做
```

**语义合并流程**:
```python
1. 插入新记忆 memory_new
2. 检索最相似记忆 most_similar = retrieve(memory_new, top_k=1)
3. if similarity(memory_new, most_similar) > threshold:
       merged = llm.merge(memory_new, most_similar)
       update(most_similar, merged)
   else:
       add(memory_new)
```

**应用系统对比**:

| 系统 | 策略 | 特点 |
|------|------|------|
| **Mem0** | LLM CRUD | 四种操作，LLM完全决策 |
| **Mem0ᵍ** | Graph + LLM | 基于图关系的CRUD |
| **TiM** | Semantic Merge | 语义合并相似记忆 |
| **MemGPT** | Reflection + Edit | 反思式记忆编辑 |

---

## 2. Decay Eviction（衰减驱逐）

**策略意图**: 根据时间衰减或遗忘曲线删除过时记忆

| Action | 衰减模型 | 可用操作 | 触发机制 |
|--------|---------|---------|---------|
| **forgetting_curve.py** | Ebbinghaus遗忘曲线 | DELETE, NOOP | 定期扫描 |
| **time_decay.py** | 线性/指数衰减 | DELETE, NOOP | 定期扫描或容量触发 |

**Forgetting Curve公式**:
```python
# Ebbinghaus遗忘曲线
R(t) = e^(-t/S)

# R(t): t时刻的记忆强度
# S: 记忆稳定性（与重要性、复习次数相关）

if R(t) < threshold:
    delete(memory)
```

**Time Decay策略**:
```python
# 线性衰减
score(t) = initial_score - decay_rate * t

# 指数衰减
score(t) = initial_score * e^(-lambda * t)

# 访问刷新
if accessed:
    score = refresh(score)  # 重置或增强

if score < threshold:
    delete(memory)
```

**应用系统对比**:

| 系统 | 策略 | 特点 |
|------|------|------|
| **MemoryBank** | 遗忘曲线 + 复习 | 符合人类记忆规律 |
| **LD-Agent** | 时间衰减 | 简单高效，适合实时系统 |
| **MemoryOS** | 热度衰减 | 结合访问频率 |

**触发时机**:
- **主动触发**: 定期扫描（如每小时）
- **被动触发**: 容量达到上限时

---

## 3. Structure Enrichment（结构增强）

**策略意图**: 构建记忆间的关联结构（链接、图）

| Action | 结构类型 | 可用操作 | 触发机制 |
|--------|---------|---------|---------|
| **link_evolution.py** | 记忆链接 | LINK, NOOP | 插入后检索相关记忆 |
| **graph_construction.py** | 知识图谱 | ADD_NODE, ADD_EDGE, NOOP | 插入后提取实体关系 |

**Link Evolution流程**:
```python
# A-Mem自动链接机制
1. 插入新记忆 memory_new
2. 检索K个最相似记忆 neighbors = retrieve(memory_new, top_k=K)
3. for each neighbor in neighbors:
       if similarity(memory_new, neighbor) > threshold:
           LLM决策是否建立链接
           if llm.should_link(memory_new, neighbor):
               create_link(memory_new, neighbor, relation_type)
```

**Graph Construction流程**:
```python
# HippoRAG图构建
1. 插入新记忆 memory_new
2. 提取实体和关系 entities, relations = extract(memory_new)
3. for entity in entities:
       add_or_update_node(entity)
4. for (subj, pred, obj) in relations:
       add_or_update_edge(subj, pred, obj)
5. 计算图属性（PageRank, Community等）
```

**应用系统对比**:

| 系统 | 结构 | 检索方式 |
|------|------|---------|
| **A-Mem** | 记忆链接网络 | 链接传播 + KNN |
| **HippoRAG** | 知识图谱 | PPR (Personalized PageRank) |
| **HippoRAG2** | 双层图（记忆+实体） | 协同检索 |

**链接类型**:
- **语义链接**: 基于内容相似度
- **时序链接**: 基于时间邻近性
- **因果链接**: 基于逻辑关系

---

## 4. Tier Migration（层级迁移）

**策略意图**: 根据访问热度在不同存储层间迁移记忆

| Action | 迁移策略 | 可用操作 | 触发机制 |
|--------|---------|---------|---------|
| **heat_migration.py** | 热度阈值 | MIGRATE, EXTRACT, NOOP | 热度变化或定期扫描 |

**MemoryOS三层架构**:
```
STM (Short-Term Memory)
  ↓ 热度高 → 提升
MTM (Medium-Term Memory)
  ↓ 热度低 → 降级
LTM (Long-Term Memory)
  ↑ 热度高 → 提升
```

**迁移逻辑**:
```python
# 热度计算
heat = alpha * access_frequency + (1-alpha) * recency

# 迁移决策
if current_tier == "STM" and heat > threshold_high:
    migrate_to("MTM")
elif current_tier == "MTM":
    if heat > threshold_very_high:
        migrate_to("LTM")
    elif heat < threshold_low:
        migrate_to("STM")
elif current_tier == "LTM" and heat < threshold_very_low:
    migrate_to("MTM")

# 提取精华（可选）
if migrating_to_LTM:
    extracted = llm.extract_essence(memory)
    store_in_LTM(extracted)
```

**操作类型**:
- **MIGRATE**: 完整迁移记忆
- **EXTRACT**: 提取精华后迁移（压缩）
- **NOOP**: 保持当前层级

**触发机制**:
- **访问触发**: 每次访问后更新热度，检查是否需要迁移
- **定期扫描**: 批量检查所有记忆的热度

---

## 策略组合模式

### 模式1: Mem0风格（冲突优先）
```yaml
post_insert:
  - conflict_resolution.llm_crud  # LLM决策CRUD
  # 不使用遗忘（记忆永久保留）
```

### 模式2: MemoryBank风格（遗忘优先）
```yaml
post_insert:
  - decay_eviction.forgetting_curve  # 遗忘曲线删除
  # 不处理冲突（允许重复）
```

### 模式3: HippoRAG风格（结构优先）
```yaml
post_insert:
  - structure_enrichment.graph_construction  # 构建知识图谱
  # 不处理冲突和遗忘
```

### 模式4: MemoryOS风格（分层优先）
```yaml
post_insert:
  - tier_migration.heat_migration     # 热度迁移
  - decay_eviction.time_decay         # 低热度删除
  # 结合迁移和遗忘
```

### 模式5: 综合策略（全功能）
```yaml
post_insert:
  - conflict_resolution.llm_crud           # 处理冲突
  - structure_enrichment.link_evolution    # 建立链接
  - tier_migration.heat_migration          # 分层迁移
  - decay_eviction.forgetting_curve        # 遗忘过时
```

---

## 触发机制对比

| 触发方式 | 适用策略 | 执行时机 | 性能影响 |
|---------|---------|---------|---------|
| **Retrieval触发** | Conflict Resolution | 插入后立即检索并决策 | 中等（需要检索） |
| **Temporal触发** | Decay Eviction | 定期扫描或容量触发 | 低（批量处理） |
| **Semantic触发** | Structure Enrichment | 插入后提取+构建 | 高（需要LLM） |
| **Threshold触发** | Tier Migration | 热度变化时 | 低（简单判断） |

---

## 与其他阶段的衔接

```
Post-Insert维护 → 影响后续检索

Conflict Resolution:
  - 去重 → Retrieval召回更少但更准确

Decay Eviction:
  - 删除过时 → Retrieval范围缩小，速度提升

Structure Enrichment:
  - 构建图 → Retrieval可用图遍历（PPR）
  - 建立链接 → Retrieval可链接传播

Tier Migration:
  - 分层存储 → Retrieval优先查高层（速度快）
```

---

## 设计权衡

| 策略 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| **Conflict Resolution** | 无冗余、一致性高 | LLM调用昂贵 | 高质量记忆系统 |
| **Decay Eviction** | 自动清理、节省空间 | 可能删除有用记忆 | 长期运行系统 |
| **Structure Enrichment** | 增强关联、提升检索 | 构建成本高 | 知识密集型应用 |
| **Tier Migration** | 性能优化、成本控制 | 复杂度高 | 大规模记忆系统 |
