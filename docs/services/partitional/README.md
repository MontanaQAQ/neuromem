# Partitional Services - 简单分区型记忆服务

Partitional Services 是基于单个 `UnifiedCollection` + 多个索引组合的简单分区型服务，适用于对话历史、文档去重、分段存储等场景。

---

## 服务列表

| 服务 | Service Type | 索引类型 | 适用场景 |
|------|-------------|---------|---------|
| FIFOQueueService | `fifo_queue` | FIFO Queue | 对话历史、实时日志 |
| LSHHashService | `lsh_hash` | LSH Hash | 大规模去重、近似搜索 |
| SegmentService | `segment` | Segment Index | 长文本分段、章节管理 |

---

## 1. FIFOQueueService

### 概述

**FIFOQueueService** 实现了先进先出 (FIFO) 队列语义的记忆服务，适合需要保留最近 N 条数据的场景。

### 特性

- ✅ **固定容量**: 自动淘汰最老数据
- ✅ **时间顺序**: 按插入时间排序
- ✅ **低开销**: 无向量计算，性能极高
- ✅ **元数据支持**: 保留完整元数据

### 使用示例

#### 基础用法

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 创建 Collection
collection = UnifiedCollection("conversation_history")

# 创建 FIFO 服务（保留最近 20 条）
service = MemoryServiceRegistry.create(
    "fifo_queue",
    collection,
    config={"max_size": 20}
)

# 插入对话
service.insert("User: Hello!", metadata={"speaker": "user", "timestamp": "2025-01-26 10:00"})
service.insert("Assistant: Hi there!", metadata={"speaker": "assistant", "timestamp": "2025-01-26 10:01"})

# 检索最近对话
recent = service.retrieve(query="", top_k=5)
for msg in recent:
    print(f"{msg['metadata']['speaker']}: {msg['text']}")
```

#### 高级用法：元数据过滤

```python
# 插入带元数据的对话
service.insert(
    "User: What's the weather?",
    metadata={"speaker": "user", "topic": "weather", "priority": "high"}
)
service.insert(
    "Assistant: It's sunny today.",
    metadata={"speaker": "assistant", "topic": "weather"}
)

# 过滤查询
results = service.retrieve(
    query="",
    top_k=10,
    filters={"topic": "weather"}  # 只返回天气相关对话
)
```

#### 获取最近 N 条数据（便捷方法）

```python
# 获取最近 10 条
recent_10 = service.get_recent(limit=10)

# 等价于
recent_10 = service.retrieve(query="", top_k=10)
```

### 配置参数

```python
config = {
    "max_size": 20,  # 队列最大容量（必填）
}
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_size` | int | 10 | 队列最大容量，超出自动淘汰最老数据 |

### API 参考

#### `insert(text: str, **kwargs) -> str`

插入数据到 FIFO 队列。

**参数**:
- `text` (str): 文本内容
- `metadata` (dict, 可选): 元数据字典

**返回**: 数据 ID (str)

**示例**:
```python
data_id = service.insert(
    "User: Hello",
    metadata={"speaker": "user"}
)
```

#### `retrieve(query: str, top_k: int = 5, **kwargs) -> list[dict]`

检索最近的数据。

**参数**:
- `query` (str): 查询文本（FIFO 不使用，传入空字符串）
- `top_k` (int): 返回数量
- `filters` (dict, 可选): 元数据过滤条件

**返回**: 结果列表 `[{"id": "...", "text": "...", "metadata": {...}, "score": 1.0}, ...]`

**示例**:
```python
results = service.retrieve(query="", top_k=5)
```

#### `get_recent(limit: int = 10) -> list[dict]`

便捷方法，获取最近 N 条数据。

**参数**:
- `limit` (int): 返回数量

**返回**: 结果列表

#### `delete(data_id: str) -> bool`

删除指定数据。

**参数**:
- `data_id` (str): 数据 ID

**返回**: 是否成功 (bool)

### 性能

| 指标 | 值 |
|------|-----|
| 插入吞吐量 | > 1000 ops/s |
| 检索吞吐量 | > 100 queries/s |
| 内存占用 (10K) | ~50 MB |
| 时间复杂度 | O(1) 插入, O(k) 检索 |

### 适用场景

✅ **推荐**:
- 对话历史（保留最近 N 轮）
- 实时日志记录
- 滑动窗口缓存
- 短期记忆（< 1000 条）

❌ **不推荐**:
- 需要语义搜索
- 长期存储（> 10K 条）
- 需要随机访问

---

## 2. LSHHashService

### 概述

**LSHHashService** 使用 LSH (Locality-Sensitive Hashing) 算法实现快速近似相似度搜索，适合大规模向量去重和检索。

### 特性

- ✅ **O(1) 查询**: 平均时间复杂度
- ✅ **大规模支持**: 适合 100K+ 向量
- ✅ **去重高效**: 快速发现相似文档
- ⚠️ **近似结果**: 精度 ~90-95%

### 使用示例

#### 基础用法

```python
import numpy as np
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 创建 Collection
collection = UnifiedCollection("document_dedup")

# 创建 LSH 服务
service = MemoryServiceRegistry.create(
    "lsh_hash",
    collection,
    config={
        "embedding_dim": 768,
        "num_tables": 10,
        "hash_size": 8
    }
)

# 插入文档（需要提供 embedding）
vector = np.random.randn(768).astype(np.float32)
vector = vector / (np.linalg.norm(vector) + 1e-10)  # 归一化

service.insert(
    "Document content here",
    vector=vector,
    metadata={"doc_id": "doc_001"}
)

# 查询相似文档
query_vector = np.random.randn(768).astype(np.float32)
query_vector = query_vector / (np.linalg.norm(query_vector) + 1e-10)

results = service.retrieve(
    query="",
    vector=query_vector,
    top_k=10
)
```

#### 去重应用

```python
# 插入多个文档
documents = [
    "Python is a programming language",
    "Python is used for data science",
    "Java is also a programming language"
]

for doc in documents:
    # 假设有 embedding 函数
    vector = get_embedding(doc)  # 需要自己实现
    service.insert(doc, vector=vector)

# 检测重复文档
new_doc = "Python is a popular programming language"
new_vector = get_embedding(new_doc)

duplicates = service.retrieve(
    query="",
    vector=new_vector,
    top_k=5
)

# 如果相似度高，可能是重复
for dup in duplicates:
    if dup["score"] > 0.9:  # 阈值可调
        print(f"可能重复: {dup['text']}")
```

### 配置参数

```python
config = {
    "embedding_dim": 768,    # 向量维度（必填）
    "num_tables": 10,        # LSH 表数量
    "hash_size": 8,          # 哈希位数
}
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `embedding_dim` | int | 必填 | 向量维度 |
| `num_tables` | int | 10 | LSH 表数量，越多精度越高但内存越大 |
| `hash_size` | int | 8 | 每个哈希的位数，越大精度越高 |

**精度 vs 速度权衡**:
- 快速模式: `num_tables=10, hash_size=8` → 精度 ~90%, 速度快
- 平衡模式: `num_tables=15, hash_size=10` → 精度 ~93%, 速度中等
- 高精度模式: `num_tables=20, hash_size=12` → 精度 ~95%, 速度慢

### API 参考

#### `insert(text: str, vector: np.ndarray, **kwargs) -> str`

插入文档和向量。

**参数**:
- `text` (str): 文本内容
- `vector` (np.ndarray): 归一化后的向量 (float32)
- `metadata` (dict, 可选): 元数据

**返回**: 数据 ID

**注意**: 向量必须归一化！

#### `retrieve(query: str, vector: np.ndarray, top_k: int = 5, **kwargs) -> list[dict]`

查询相似向量。

**参数**:
- `query` (str): 查询文本（可选，主要用 vector）
- `vector` (np.ndarray): 查询向量
- `top_k` (int): 返回数量

**返回**: 结果列表（按相似度排序）

### 性能

| 指标 | 值 |
|------|-----|
| 插入吞吐量 | > 500 ops/s |
| 检索吞吐量 | > 50 queries/s |
| 内存占用 (100K, 768维) | ~1.2 GB |
| 精度 | ~90-95% |

### 适用场景

✅ **推荐**:
- 大规模文档去重（> 100K）
- 快速近似搜索
- 高维向量检索
- 实时推荐系统

❌ **不推荐**:
- 小数据集（< 1K）
- 要求 100% 精度
- 低维向量（< 64）

---

## 3. SegmentService

### 概述

**SegmentService** 将长文本自动或手动分段存储，支持段落级检索和上下文保留。

### 特性

- ✅ **自动分段**: 按长度自动切分
- ✅ **保留上下文**: 段落重叠
- ✅ **段落检索**: 返回最相关段落
- ✅ **元数据继承**: 段落继承文档元数据

### 使用示例

#### 基础用法

```python
from sage.middleware.components.sage_mem.neuromem.memory_collection import (
    UnifiedCollection
)
from sage.middleware.components.sage_mem.neuromem.services import (
    MemoryServiceRegistry
)

# 创建 Collection
collection = UnifiedCollection("document_segments")

# 创建 Segment 服务
service = MemoryServiceRegistry.create(
    "segment",
    collection,
    config={
        "max_segment_length": 500,  # 最大段落长度
        "overlap": 50               # 段落重叠字符数
    }
)

# 插入长文本（自动分段）
long_text = """
这是一篇很长的文章...
（省略几千字）
"""

service.insert(
    long_text,
    metadata={"doc_id": "article_001", "title": "AI 技术综述"}
)

# 检索相关段落
results = service.retrieve(query="深度学习", top_k=5)
for result in results:
    print(f"段落 {result['metadata']['segment_id']}: {result['text'][:100]}...")
```

#### 手动分段

```python
# 手动指定段落
segments = [
    "第一章：引言\n这是引言部分...",
    "第二章：方法\n本文提出的方法...",
    "第三章：实验\n我们进行了以下实验..."
]

for i, segment in enumerate(segments):
    service.insert(
        segment,
        metadata={"doc_id": "paper_001", "chapter": i}
    )
```

### 配置参数

```python
config = {
    "max_segment_length": 500,  # 最大段落长度
    "overlap": 50,              # 段落重叠字符数
}
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_segment_length` | int | 500 | 单个段落最大字符数 |
| `overlap` | int | 50 | 相邻段落重叠字符数（保留上下文） |

### API 参考

#### `insert(text: str, **kwargs) -> str`

插入文本（自动分段）。

**参数**:
- `text` (str): 文本内容
- `metadata` (dict, 可选): 元数据（会继承到每个段落）

**返回**: 主文档 ID

**自动分段逻辑**:
1. 按 `max_segment_length` 切分文本
2. 相邻段落保留 `overlap` 字符重叠
3. 每个段落添加 `segment_id` 元数据

#### `retrieve(query: str, top_k: int = 5, **kwargs) -> list[dict]`

检索相关段落。

**参数**:
- `query` (str): 查询文本
- `top_k` (int): 返回段落数量

**返回**: 段落结果列表

### 性能

| 指标 | 值 |
|------|-----|
| 插入吞吐量 | > 100 docs/s |
| 检索吞吐量 | > 50 queries/s |
| 内存占用 | 依赖段落数量 |

### 适用场景

✅ **推荐**:
- 长文档存储（论文、书籍）
- 章节管理
- 段落级检索
- 保留上下文的分块

❌ **不推荐**:
- 短文本（< 500 字符）
- 需要全文检索
- 结构化数据

---

## 对比总结

| 特性 | FIFO Queue | LSH Hash | Segment |
|------|-----------|----------|---------|
| **索引类型** | FIFO Queue | LSH Hash | Segment Index |
| **需要向量** | ❌ | ✅ | ❌ |
| **插入速度** | ⚡ 极快 | 🚀 快 | ✅ 中等 |
| **检索速度** | ⚡ 极快 | 🚀 快 | ✅ 中等 |
| **内存占用** | 💚 低 | ⚠️ 高 | 💛 中等 |
| **适用数据量** | < 10K | > 100K | 任意 |
| **检索方式** | 时间顺序 | 向量相似度 | 文本匹配 |

---

## 最佳实践

### 1. 选择合适的服务

**场景 1: 对话历史**
- 推荐: **FIFOQueueService**
- 配置: `max_size=100`

**场景 2: 大规模文档去重**
- 推荐: **LSHHashService**
- 配置: `embedding_dim=768, num_tables=10`

**场景 3: 长文档检索**
- 推荐: **SegmentService**
- 配置: `max_segment_length=500, overlap=50`

### 2. 性能优化

**FIFO Queue**:
- 设置合理的 `max_size`（避免过大）
- 使用元数据过滤减少检索范围

**LSH Hash**:
- 只在大数据集使用（> 10K）
- 调整 `num_tables` 平衡精度/速度
- 向量必须归一化

**Segment**:
- 调整 `max_segment_length` 适配文档类型
- 使用 `overlap` 保留上下文
- 考虑分段粒度（章节 vs 段落）

### 3. 内存管理

- 定期清理不需要的数据
- 监控 Collection 大小
- 使用合适的 `max_size` 限制

---

## 测试

### 单元测试

```bash
# FIFO Queue
pytest packages/sage-middleware/tests/unit/services/partitional/test_fifo_queue_service.py -v

# LSH Hash
pytest packages/sage-middleware/tests/unit/services/partitional/test_lsh_hash_service.py -v

# Segment
pytest packages/sage-middleware/tests/unit/services/partitional/test_segment_service.py -v
```

### E2E 测试

```bash
pytest packages/sage-middleware/tests/e2e/test_complete_workflows.py::TestFIFOQueueWorkflow -v
```

---

## 参考资料

- **Service Registry**: [../SERVICES_README.md](../SERVICES_README.md)
- **性能基准**: [../BENCHMARKS.md](../BENCHMARKS.md)
- **Hierarchical Services**: [../hierarchical/README.md](../hierarchical/README.md)

---

**最后更新**: 2025-01-26  
**版本**: v1.0.0 (T4.4a)
