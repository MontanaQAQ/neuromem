# Pre-Retrieval Actions 设计维度

## 维度总览（5个维度）

| 维度 | 职责 | Action数量 |
|------|------|-----------|
| **Embedding (透传)** | 向量化基础转换 | 1 |
| **None (透传)** | 无操作，直接传递查询 | 1 |
| Enhancement | 增强查询的多样性和覆盖面 | 3 |
| Optimize | 优化查询质量和精确度 | 3 |
| Validate | 验证查询合法性 | 1 |

> **💡 透传操作**:
> - **`embedding`**: 基础向量化，不做复杂处理，是所有向量检索系统的必备基础操作
> - **`none`**: 完全无操作，适用于纯文本检索（BM25等）

---

## 1. Embedding 维度（透传）

**目的**: 为向量检索提供查询的向量表示（基础转换，不做复杂优化）

| Action | 功能 | 模型类型 | 关键参数 |
|--------|------|---------|---------|
| **embedding.py** | 查询向量化 | 任意embedding模型 | model_name, dim, normalize |

**透传特性**:
- **简单转换**: 仅做向量化，不进行查询改写或优化
- **必备操作**: 所有向量检索系统的基础步骤
- **与优化分离**: 复杂处理由 Enhancement/Optimize 维度负责

**设计要点**:
- **一致性**: 必须与存储时使用的模型一致
- **批处理**: 支持批量查询的向量化
- **缓存**: 相同查询复用已生成的向量

**示例**:
```python
# 单查询
vector = embedding.execute(query="如何提升记忆性能")

# 批量查询
vectors = embedding.batch_execute(queries=[q1, q2, q3])
```

---

## 2. Enhancement 维度

**目的**: 通过查询扩展提升召回率

| Action | 增强策略 | 输出 | 应用场景 |
|--------|---------|------|---------|
| **decompose.py** | 查询分解 | 多个子查询 | 复杂问答、Multi-hop推理 |
| **multi_embed.py** | 多模型嵌入 | 多个向量 | 提升召回（模型互补） |
| **route.py** | 查询路由 | 路由决策 + 子查询 | 混合检索（向量/文本/图） |

**Decompose示例**:
```python
# 输入
query = "如何在AI系统中实现长期记忆且保持高性能？"

# 输出
sub_queries = [
    "AI长期记忆实现方法",
    "记忆系统性能优化",
    "长期记忆与性能的平衡策略"
]
```

**Multi-Embed示例**:
```python
# 使用多个模型
models = ["bge-m3", "gte-large", "e5-mistral"]
vectors = multi_embed.execute(query, models)
# 后续检索合并多个模型的结果
```

**Route示例**:
```python
# 根据查询类型路由
if is_factual_query(query):
    route_to = "graph_index"  # 图检索
elif is_semantic_query(query):
    route_to = "vector_index"  # 向量检索
else:
    route_to = "text_index"   # 文本检索
```

---

## 3. Optimize 维度

**目的**: 改写或扩展查询以提升检索质量

| Action | 优化方法 | 召回变化 | 准确率变化 | 应用场景 |
|--------|---------|---------|-----------|---------|
| **expand.py** | 添加同义词/相关词 | ↑↑ 增加 | ↓ 降低 | 提升召回、术语变体 |
| **keyword_extract.py** | 提取核心关键词 | ↓ 减少 | ↑ 提升 | BM25检索、精准匹配 |
| **rewrite.py** | LLM改写查询 | ± 依赖质量 | ↑ 提升 | 消歧、补全、规范化 |

**Expand示例**:
```python
# 输入
query = "如何提升AI记忆"

# 输出（添加同义词）
expanded = "如何提升AI记忆 | 增强 改进 优化 | 记忆系统 记忆能力 记忆管理"
```

**Keyword Extract示例**:
```python
# 输入
query = "请问在实际应用中如何有效地提升AI系统的长期记忆能力？"

# 输出
keywords = ["AI系统", "长期记忆", "能力", "提升"]
```

**Rewrite示例**:
```python
# 输入
query = "AI咋记住东西的？"

# 输出（LLM改写）
rewritten = "AI系统如何实现信息的存储和检索？"
```

**优化策略对比**:

| 策略 | 适用场景 | 优势 | 劣势 |
|------|---------|------|------|
| expand | 召回优先 | 覆盖面广 | 噪音多 |
| keyword_extract | 精准优先 | 准确度高 | 召回受限 |
| rewrite | 复杂查询 | 语义清晰 | 依赖LLM质量 |

---

## 4. Validate 维度

**目的**: 拦截无效查询，避免无效检索

| Action | 验证内容 | 失败处理 |
|--------|---------|---------|
| **validate.py** | 长度/格式/语言检查 | 返回错误或默认查询 |

**验证规则**:
```python
# 长度验证
MIN_LENGTH = 3
MAX_LENGTH = 1000

# 字符验证
ALLOWED_CHARS = r'[a-zA-Z0-9\u4e00-\u9fa5\s\.,!?；。，！？]'

# 语义验证
def is_meaningful(query):
    # 检查是否包含实际内容
    return len(extract_keywords(query)) > 0
```

---

## 推荐组合模式

### 模式1: 高召回检索（广泛搜索）
```yaml
pre_retrieval:
  - validate.base              # 验证有效性
  - optimize.expand            # 同义词扩展
  - enhancement.multi_embed    # 多模型嵌入
  # → 召回↑↑ 准确率↓
```

### 模式2: 高精度检索（精准搜索）
```yaml
pre_retrieval:
  - validate.base              # 验证有效性
  - optimize.keyword_extract   # 提取关键词
  - embedding.base             # 单一高质量模型
  # → 召回↓ 准确率↑↑
```

### 模式3: 复杂问答（Multi-hop）
```yaml
pre_retrieval:
  - validate.base              # 验证有效性
  - enhancement.decompose      # 分解子问题
  - optimize.rewrite           # LLM改写每个子问题
  - embedding.base             # 向量化
  # → 各子问题独立检索，Post-Retrieval合并
```

### 模式4: 混合检索（向量+文本+图）
```yaml
pre_retrieval:
  - validate.base              # 验证有效性
  - enhancement.route          # 路由决策
    ├─ vector_route:
    │   └─ embedding.base      # 向量检索分支
    ├─ text_route:
    │   └─ optimize.keyword_extract  # 文本检索分支
    └─ graph_route:
        └─ extract.entity      # 图检索分支
  # → Post-Retrieval合并多路结果
```

---

## 与其他阶段的衔接

```
Pre-Retrieval输出 → 用于后续阶段

Embedding结果:
  - query_vector → Retrieval的向量检索

Enhancement结果:
  - sub_queries → 并行检索 → Post-Retrieval的merge
  - route_decision → Retrieval的索引选择

Optimize结果:
  - keywords → Retrieval的BM25检索
  - rewritten_query → Retrieval的主查询

Validate结果:
  - is_valid → 决定是否继续检索
```

---

## 性能优化建议

### 1. 缓存策略
```python
# 缓存embedding结果
@lru_cache(maxsize=1000)
def get_embedding(query: str) -> np.ndarray:
    return model.encode(query)

# 缓存rewrite结果（LLM调用昂贵）
@redis_cache(ttl=3600)
def rewrite_query(query: str) -> str:
    return llm.rewrite(query)
```

### 2. 并行处理
```python
# multi_embed并行
with ThreadPoolExecutor() as executor:
    futures = [executor.submit(model.encode, query)
               for model in models]
    vectors = [f.result() for f in futures]

# decompose后并行检索
sub_results = await asyncio.gather(*[
    retrieve(sub_q) for sub_q in sub_queries
])
```

### 3. 降级策略
```python
# rewrite失败 → 使用原始查询
try:
    rewritten = llm.rewrite(query)
except Exception:
    rewritten = query

# validate失败 → 尝试自动修复
if not validate(query):
    query = auto_fix(query)  # 移除非法字符等
```
