# 记忆体系统实现总结

本文档基于 `reference/` 目录下的代码仓库，结合 benchmark 实验配置，对主流记忆体系统进行总结。

---

## 1. TiM (Think-in-Memory)

> 📌 **参考代码**: 暂未找到开源实现

### 核心特征
- **LSH 哈希分桶**: Locality-Sensitive Hashing 将语义相近的 thoughts 映射到同一桶
- **三元组存储**: 每个 thought 表示为 "(Subject, Predicate, Object)" 形式
- **LLM 驱动优化**: Forget (去矛盾) + Merge (合并同实体)

### 关键实现
```
数据结构: 哈希表 {hash → [thoughts]}
插入: LSH(thought) → bucket → append
检索: LSH(query) → 定位桶 → 相似度排序 → top-k
优化: LLM 判断矛盾/合并 → 清空桶 → 重建
```

**设计亮点**: Post-thinking 后处理生成归纳性记忆，模拟人类记忆的整合与遗忘机制。

---

## 2. MemoryBank

> 📂 **参考代码**: `reference/MemoryBank-SiliconFriend/`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (ForgettingMixin, UserPortraitMixin)

### 核心特征
- **三层存储**: 原始对话 + 事件摘要 (Daily/Global) + 用户画像
- **Ebbinghaus 遗忘曲线**: 记忆强度 $R = e^{-t/S}$，低强度自动淘汰
- **FAISS 向量检索**: MiniLM/Text2vec 编码，语义相似度检索

### 关键实现
```python
# reference/MemoryBank-SiliconFriend/
- 事件摘要生成: LLM prompt "Summarize events..."
- 用户画像更新: LLM prompt "Personality traits..."
- 遗忘机制: 检索时 S += 1, 未被检索则 R 衰减

# SAGE 实现
class EbbinghausForgetting:
    def calculate_retention(self, last_access, strength):
        return exp(-time_elapsed / strength)

class UserPortraitMixin:
    def update_portrait(self, dialogue):
        # 维护 User Profile + Traits
```

**Benchmark 配置**: `config/locomo_memorybank_pipeline.yaml`

---

## 3. MemGPT

> 📂 **参考代码**: `reference/MemGPT/memgpt/`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (MemGPTStorageMixin)

### 核心特征
- **三层功能分区**: Working Context (固定) + FIFO Queue (临时) + Recall Storage (持久)
- **Agent 工具管理**: `core_memory_append` / `core_memory_replace`
- **混合检索**: 向量检索 (Archival) + 全文检索 (Recall) + RRF 融合

### 关键实现
```python
# reference/MemGPT/memgpt/agent.py
class Agent:
    def core_memory_append(self, key, value):
        # 追加到 Working Context

    def core_memory_replace(self, old_key, new_key, value):
        # 替换 Working Context 条目

# SAGE 实现
class MemGPTStorageMixin:
    _working_context: dict  # {"name": "Alice", ...}
    _fifo_queue: deque      # 最新对话
    _recall_storage: list   # 所有历史
```

**Benchmark 配置**: `config/locomo_memgpt_pipeline.yaml`

---

## 4. A-Mem (Agentic Memory)

> 📂 **参考代码**: `reference/A-mem/memory_layer.py`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (AMemNoteMixin, LinkEvolutionMixin)

### 核心特征
- **Note 结构**: content + keywords + tags + context + links
- **Link Evolution**: KNN 邻居建链 + LLM 判断相关性
- **Memory Evolution**: 更新旧记忆的 keywords/tags/context

### 关键实现
```python
# reference/A-mem/memory_layer.py
class MemoryNote:
    def __init__(self, content, keywords, tags, context):
        self.links = []  # 自动建立的链接

    def add_link(self, other_note):
        # 基于 embedding 相似度建链

# SAGE 实现
class AMemNoteMixin:
    def insert_note(self, content, keywords, tags, context):
        # 插入带结构化字段的 Note

class LinkEvolutionMixin:
    def auto_link(self, new_note):
        # KNN 检索 → LLM 判断 → 建立双向链接
```

**Benchmark 配置**: `config/locomo_amem_pipeline.yaml`

---

## 5. HippoRAG / HippoRAG 2

> 📂 **参考代码**: `reference/HippoRAG/src/`  
> 🔧 **SAGE 实现**: `sage/neuromem/services/hierarchical/semantic_inverted_knowledge_graph.py`

### 核心特征 (HippoRAG)
- **知识图谱**: Phrase Nodes (实体) + Relation Edges (关系) + Synonym Edges (同义词)
- **OpenIE 提取**: LLM 提取 (Subject, Predicate, Object) 三元组
- **PPR 检索**: Personalized PageRank 图遍历

### 核心特征 (HippoRAG 2)
- **增强 PPR**: depth=3, num_start_nodes=15
- **Passage + Phrase 双节点**: Context Edges 连接段落与实体
- **增强重排序**: PPR 分数 (0.6) + 语义相似度 (0.4)

### 关键实现
```python
# reference/HippoRAG/src/hipporag.py
def extract_triples(passage):
    # OpenIE 提取 (S, P, O)

def ppr_retrieval(query, graph):
    # Query → NER → 定位种子节点 → PPR 遍历

# SAGE 实现
class HippoRAGMixin:
    def insert_phrase_node(self, phrase, source_passage_id):
        # 插入实体节点 + contains 边

    def add_synonym_edge(self, phrase_id_1, phrase_id_2):
        # 语义相似度超阈值 → 建立同义词边
```

**Benchmark 配置**:
- `config/locomo_hipporag_pipeline.yaml`
- `config/locomo_hipporag2_pipeline.yaml`

---

## 6. MemoryOS

> 📂 **参考代码**: `reference/MemoryOS/`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (SegmentPageMixin, HeatMigrationMixin)

### 核心特征
- **三层架构**: STM (FIFO 20) + MTM (Segment-Page 200) + LPM (Persona 无限)
- **Segment-Page 结构**: Segment (主题摘要) + Page (原始对话)
- **Heat Score 迁移**: Nvisit + Linteraction + Rrecency → 高热迁移到 LPM

### 关键实现
```python
# SAGE 实现
class MemoryOSSegment:
    summary: str         # LLM 生成的主题摘要
    keywords: list       # 关键词
    pages: list[Page]    # 所属对话页

class HeatMigrationMixin:
    def calculate_heat(self, segment):
        return Nvisit * w1 + Linteraction * w2 + Rrecency * w3

    def migrate_to_lpm(self, segment):
        # Heat >= τ → 提取 User KB/Traits → FIFO 插入 LPM
```

**Benchmark 配置**: `config/locomo_memoryos_pipeline.yaml`

---

## 7. LD-Agent

> 📂 **参考代码**: `reference/LD-Agent/`  
> 🔧 **SAGE 实现**: `benchmarks/experiment/libs/post_insert/decay_eviction/time_decay.py`

### 核心特征
- **双层结构**: 短时缓存 (600s 超时) + 长时记忆库 (事件摘要向量)
- **时间衰减**: 语义相似度 + 话题重叠 + 时间衰减系数
- **自动摘要**: 会话超时 → LLM 生成事件摘要 → 插入长时库

### 关键实现
```python
# SAGE 实现
class TimeDecayAction:
    def execute(self, input_data):
        if time_elapsed > 600:
            summary = llm.summarize(short_term_cache)
            long_term_bank.insert(summary, timestamp)
            short_term_cache.clear()
```

**Benchmark 配置**: `config/locomo_ldagent_pipeline.yaml`

---

## 8. SCM (Self-Controlled Memory)

> 📂 **参考代码**: `reference/SCM4LLMs/`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (TokenBudgetMixin)

### 核心特征
- **Memory Stream**: interaction + response + summarization + embedding
- **Memory Controller**: LLM 判断是否激活记忆 (yes/no)
- **Token Budget 过滤**: 长度 > 800 tokens → 用 summary 替代原文

### 关键实现
```python
# SAGE 实现
class TokenBudgetMixin:
    def filter_by_budget(self, memories, max_tokens=2000):
        if total_tokens > max_tokens:
            for mem in memories:
                if len(mem.text) > 800:
                    mem.text = mem.summary  # 替换为摘要
```

**Benchmark 配置**: `config/locomo_scm_pipeline.yaml`

---

## 9. Mem0 / Mem0ᵍ

> 📂 **参考代码**: `reference/mem0/mem0/`  
> 🔧 **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py` (ConflictDetectionMixin, Mem0gMixin)

### 核心特征 (Mem0)
- **事实存储**: 自然语言文本片段 + 全局摘要 S
- **CRUD 决策**: LLM 工具调用 ADD / UPDATE / DELETE / NOOP
- **冲突检测**: 检索相似记忆 → LLM 判断矛盾 → 删除旧版本

### 核心特征 (Mem0ᵍ - 图增强版)
- **有向标签图**: Entity Nodes + Relation Edges (valid flag)
- **实体复用**: 语义相似度 > t → 复用节点
- **冲突标记**: 新关系与旧关系冲突 → 标记旧关系为 invalid

### 关键实现
```python
# SAGE 实现
class ConflictDetectionMixin:
    def detect_conflict(self, new_fact, existing_facts):
        conflicts = llm.find_conflicts(new_fact, existing_facts)
        for old_fact in conflicts:
            self.delete(old_fact.id)

class Mem0gMixin:
    def add_entity(self, name, entity_type):
        similar = self.search_similar_entities(name)
        if similar and similarity > threshold:
            return similar.id  # 复用节点
        else:
            return self.create_node(name, entity_type)
```

**Benchmark 配置**: `config/locomo_mem0_pipeline.yaml`

---

## 10. SeCom

> 📂 **参考代码**: `reference/SeCom/`  
> 🔧 **SAGE 实现**: `benchmarks/experiment/libs/pre_insert/semantic_clustering/`

### 核心特征
- **Segment-Level 存储**: 语义连贯的对话片段 (非 turn-level)
- **压缩式去噪**: LLM 压缩冗余内容，保留关键信息
- **语义聚类**: Mistral-7B/RoBERTa 分割 + MPNet 检索

### 关键实现
```python
# SAGE 实现 (简化)
def compression_denoising(dialogue_turns):
    compressed = llm.compress(dialogue_turns)  # 去噪
    return compressed

def semantic_segmentation(compressed_text):
    segments = model.split_by_topic(compressed_text)
    return segments
```

**Benchmark 配置**: `config/locomo_secom_pipeline.yaml`

---

## 对比总结

| 记忆体 | 数据结构 | 核心机制 | 典型应用 | 代码实现 |
|--------|----------|----------|----------|----------|
| TiM | LSH 哈希桶 | Post-thinking 三元组 | 知识归纳 | ❌ 未找到 |
| MemoryBank | 三层 (对话+摘要+画像) | Ebbinghaus 遗忘 | 长期陪伴 | ✅ `MemoryBank-SiliconFriend/` |
| MemGPT | 三层功能分区 | Agent 工具调用 | OS 式记忆管理 | ✅ `MemGPT/memgpt/` |
| A-Mem | Note 图谱 | Link Evolution | 代理记忆网络 | ✅ `A-mem/memory_layer.py` |
| HippoRAG | 知识图谱 | PPR 图遍历 | 多跳推理 | ✅ `HippoRAG/src/` |
| MemoryOS | 三层 (STM+MTM+LPM) | Heat Score 迁移 | 智能助手 | ✅ `MemoryOS/` |
| LD-Agent | 双层 (短时+长时) | 时间衰减 | 对话系统 | ✅ `LD-Agent/` |
| SCM | Memory Stream | Token Budget 过滤 | 对话压缩 | ✅ `SCM4LLMs/` |
| Mem0 | 事实文本 | CRUD 决策 | 生产级 RAG | ✅ `mem0/mem0/` |
| SeCom | Segment-Level | 压缩去噪 + 聚类 | 个性化对话 | ✅ `SeCom/` |

---

## 参考资料

- **代码仓库**: `reference/` 目录
- **SAGE 实现**: `sage/neuromem/memory_collection/paper_features.py`
- **Benchmark 配置**: `benchmarks/experiment/config/primitive_memory_model/`
- **详细文档**: `docs/services/SERVICES_README.md`
