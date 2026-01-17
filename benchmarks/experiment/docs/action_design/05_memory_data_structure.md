# 05. Memory Data Structure（跨阶段数据结构）

本维度用于回答一个很“工程”的问题：**Action 写起来到底在读写哪些字段？这些字段最后会落到 NeuroMem 底层的什么数据结构里？**

它是跨越四个阶段（Pre-Insert / Post-Insert / Pre-Retrieval / Post-Retrieval）的横切面，重点描述：

- Benchmark Pipeline 中每个 packet（`dict`）在不同阶段的字段形态
- 各 Action 的输入/输出约束（哪些字段必须存在、哪些是可选）
- 与 NeuroMem 底层 `UnifiedCollection / StorageBackend / Index` 的映射关系

---

## 1. Pipeline packet 在各阶段的“字段演化”

以 `benchmarks/experiment/memory_test_pipeline.py` 的两条 Pipeline 为准：

- 插入链路：`MemorySource → PreInsert → MemoryInsert → PostInsert`
- 测试链路：`PreRetrieval → MemoryRetrieval → PostRetrieval → MemoryEvaluation`

### 1.1 MemorySource 输出（最上游输入）

来源：`benchmarks/experiment/libs/memory_source.py`

核心字段（简化）：

- `task_id: str`
- `session_id: int|str`
- `dialog_id: int`（当前 dialog 指针）
- `dialogs: list[dict]`（每条含 `speaker/role` 与 `text/content`）
- `dialog_len: int`
- `packet_idx: int`
- `total_packets: int`
- `is_session_end: bool`

这些字段会被透传到后续阶段，Action 可按需读取。

### 1.2 PreInsert 输出：`memory_entries[]`

来源：`benchmarks/experiment/libs/pre_insert/base.py`

PreInsert 统一输出：

- `memory_entries: list[dict[str, Any]]`
  - `text: str`（必须）
  - `embedding: list[float] | None`（可选）
  - `metadata: dict`（可选，但推荐始终提供）
  - `insert_mode: str`（默认 `passive`）
  - `insert_method: str`（默认 `default`；一般写 action 标识）
  - `insert_params: dict`（可选）

备注：大多数实现会通过 `_set_default_fields()` 补齐默认字段。

### 1.3 MemoryInsert 输出：`insert_stats`

来源：`benchmarks/experiment/libs/memory_insert.py`

MemoryInsert 会遍历 `memory_entries` 并调用 service 的 `insert`，并把统计结果写回 packet：

- `insert_stats: dict`
  - `inserted: int`
  - `failed: int`
  - `entry_ids: list[str]`
  - `entries: list[{id,text,embedding,metadata}]`（**保留完整信息，避免 PostInsert 重复查询**）
  - `errors: list[{entry,error}]`

同时会追加：

- `stage_timings.memory_insert_ms`

### 1.4 PostInsert 输出：通常只写 `metadata` / side-effect

来源：`benchmarks/experiment/libs/post_insert/base.py` 及各 action

PostInsert Action 的输入主要来自：

- `data`（全量 packet）
- `insert_stats`（尤其是 `entries`）
- `is_session_end`（是否本 session 最后一个包）

PostInsert 一般不会改变已插入的数据文本本身（因为插入已发生），更多是：

- 调 service 做维护（delete/update/link/migrate…）
- 把执行信息写入 `data.metadata` 或 `data.stage_timings.post_insert_ms`

### 1.5 PreRetrieval 输出：`question / query_embedding / retrieve_params`

来源：`benchmarks/experiment/libs/pre_retrieval/operator.py`

PreRetrieval 会将 Action 输出统一写回 packet：

- `question: str`（规范化后的查询）
- `query_embedding: list[float]`（可选）
- `retrieve_mode: str`（可选）
- `retrieve_params: dict`（默认至少是 `{}`）
- `metadata: dict`（可选；例如 `tier`、`needs_embedding`、`keywords` 等）

### 1.6 MemoryRetrieval 输出：`memory_data`

来源：`benchmarks/experiment/libs/memory_retrieval.py`

检索结果写入：

- `memory_data: list[dict]`
  - `text: str`
  - `score: float | None`
  - `metadata: dict`

以及：

- `retrieval_stats: {retrieved,time_ms,service_name}`
- `stage_timings.memory_retrieval_ms`

### 1.7 PostRetrieval 输出：`history_text`（面向 LLM 的上下文）

来源：`benchmarks/experiment/libs/post_retrieval/operator.py`

PostRetrieval 会：

- 读取 `memory_data`
- 经过 rerank/filter/merge/augment 后，生成 `history_text: str`
- 可选写入 `processed_memory_items: [{text,score,metadata}]`
- 写入 `stage_timings.post_retrieval_ms`

`history_text` 会被 `MemoryEvaluation` 直接拼进 prompt。

---

## 2. NeuroMem 底层数据结构：`UnifiedCollection / Storage / Index`

这一层是“Action 做的事最终如何落地”的答案。

### 2.1 UnifiedCollection 的单条数据形态

来源：`sage/neuromem/memory_collection/unified_collection.py`

插入后底层存储的数据结构（逻辑上）为：

- `data_id: str`：由 `text + metadata` 生成的 SHA256（内容相同则 id 稳定）
- value：
  - `text: str`
  - `metadata: dict`
  - `created_at: float`（epoch 秒）

同时：

- `storage`：真实存储后端（Memory / Redis / SageDB）
- `raw_data`：对 `storage` 的兼容代理（未来版本计划移除）
- `indexes`：索引容器（多个索引并存）
- `index_metadata`：索引配置元信息（用于持久化/重建）

### 2.2 StorageBackend：同一份数据，多种后端

来源：`sage/neuromem/storage_engine/storage_factory.py`

统一接口：`put/get/delete/keys/clear/__len__`。

- `MemoryStorage`：内存 dict，快但不持久化
- `RedisStorage`：JSON 序列化存 Redis，适合分布式
- `SageDBStorage`：面向向量/大规模持久化（依赖 isage-vdb）

**关键约束**：不管后端是什么，存储的数据字典形态保持一致（至少 `text` 与 `metadata`）。

### 2.3 Index：只存 `data_id`，不存原始数据

来源：`sage/neuromem/memory_collection/indexes/base_index.py`

统一原则：

- 索引只负责“如何查”，不负责“数据存哪里”
- 索引内部持久化的是 id/结构，而不是原文

典型字段约定（由各索引实现决定）：

- **FAISS 向量索引**（`faiss_index.py`）：默认从 `metadata["vector"]` 取向量；没有则用文本生成（测试/兜底逻辑）。
- **Graph 图索引**（`graph_index.py`）：常见需要 `metadata` 中的关系字段（如 `related_to` / `weights`）。
- **FIFO/LSH/BM25/Segment**：分别依赖 `text` 或少量 `metadata`。

---

## 3. 从 Benchmark 字段到 UnifiedCollection metadata 的映射建议

Benchmark 的 `memory_entries[i]` 与 `UnifiedCollection.insert(text, metadata)` 的桥接点在 Memory Service 内部（由 `NeuromemServiceFactory` 创建的各 Service 负责）。

为了让不同索引/服务可互操作，建议在 `metadata` 中遵循这些约定：

- `timestamp`: `str|float`（用于 `rerank.time_weighted` 等）
- `tier`: `"stm"|"mtm"|"ltm"`（用于分层检索/融合）
- `vector`: `list[float]`（用于 FAISS/向量检索）
- `triples`: `list[tuple|list|str]`（用于图构建/知识图谱服务）
- `related_to`: `list[str]`（用于图索引的边构建）
- `source`: 数据来源标识（便于评估/过滤）

---

## 4. 常见坑位（写 Action 时最容易踩的）

1. **不要假设字段一定存在**：Action 读取 packet 时请使用 `data.get()` 并设置默认值（例如 `memory_data` 可能为空）。
2. **时间戳格式不统一会影响 time_weighted**：推荐在 metadata 中同时保留可解析字符串或 epoch 秒。
3. **向量字段名要统一**：底层 FAISS 索引默认读取 `metadata["vector"]`；如果 Benchmark 侧使用 `embedding` 字段，请在服务/插入阶段做一次映射或复制。
4. **`scm_three_way` 的 action key 特例**：它不带 `merge.` 前缀，写配置/文档时要保持一致。
