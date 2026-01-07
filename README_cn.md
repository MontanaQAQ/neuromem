![NeuroMem Logo](docs/assets/neuromem.png)

<h3 align="center">
初忆如种 爱随年生 ~
</h3>

<p align="center">
| <a href="README.md"><b>English Documentation</b></a> | <a href="https://intellistream.slack.com/"><b>开发者Slack</b></a> |
</p>

🔥 欢迎使用NeuroMem！NeuroMem是[SAGE](https://github.com/intellistream/SAGE)的子项目，专注于探索大型语言模型的记忆系统。

---

## 快速开始

使用`pip`安装neuromem：

```bash
pip install isage-neuromem
```

对于开发环境，克隆仓库并使用提供的快速启动脚本：

```bash
git clone https://github.com/intellistream/NeuroMem.git
cd neuromem
./quickstart.sh
```

这将设置本地开发环境（虚拟环境 + 依赖项），适用于运行测试和基准测试。然后您可以：

- 在`examples/`中探索示例
- 在`benchmarks/`中运行基准测试套件
- 深入了解`sage/neuromem/`下的核心实现

## 主要特性

**NeuroMem**是一个受大脑启发的记忆管理引擎，专为SAGE（结构化AI图引擎）设计。它提供灵活的记忆集合抽象，支持向量数据库、键值存储和图结构，专门为RAG（检索增强生成）应用而设计。

### 核心功能

- **多后端支持**：VDB（向量数据库）、KV（键值对）、Graph（图数据库）
- **灵活的存储引擎**：可插拔的存储后端，支持向量、文本和元数据
- **强大的搜索引擎**：多种索引类型（FAISS、BM25s等）
- **集合管理**：创建、加载、存储和管理记忆集合
- **记忆管理器**：多个集合的集中管理

## 架构

```
sage/neuromem/
├── memory_manager.py          # 集合的中央管理器
├── memory_collection/         # 集合抽象
│   ├── base_collection.py
│   ├── vdb_collection.py
│   ├── kv_collection.py
│   └── graph_collection.py
├── search_engine/             # 索引实现
│   ├── vdb_index/
│   ├── kv_index/
│   └── graph_index/
├── storage_engine/            # 存储后端
│   ├── vector_storage.py
│   ├── text_storage.py
│   └── metadata_storage.py
└── utils/                     # 实用工具函数
```

## 使用示例

```python
from sage.neuromem import MemoryManager

# 创建管理器
manager = MemoryManager()

# 创建VDB集合
config = {
    "name": "my_collection",
    "backend_type": "VDB",
    "description": "我的向量数据库集合"
}
collection = manager.create_collection(config)

# 插入数据
collection.batch_insert_data(
    texts=["你好世界", "再见世界"],
    metadatas=[{"source": "doc1"}, {"source": "doc2"}]
)

# 创建索引
index_config = {
    "name": "my_index",
    "embedding_model": "mockembedder",
    "dim": 128,
    "backend_type": "FAISS"
}
collection.create_index(index_config)

# 检索
results = collection.retrieve(
    "你好",
    index_name="my_index",
    topk=5
)
```

## 包结构

NeuroMem是SAGE生态系统的一部分，作为命名空间包安装：
- **PyPI上的包名**：`isage-neuromem`
- **导入路径**：`sage.neuromem`
- **命名空间**：SAGE（结构化AI图引擎）的一部分

## 基准测试

在`benchmarks/`中提供了完整的基准测试套件：
- **实验流水线**：完整的记忆操作基准测试流水线
- **评估工具**：性能分析和指标
- **配置文件**：预配置的测试场景

详情请参见[benchmarks/README.md](benchmarks/README.md)。

## 未来计划

这个子项目设计为SAGE的核心记忆组件，未来可能会用C++/Rust重写以获得更好的性能。

## SAGE生态系统的一部分

NeuroMem是IntelliStream团队的SAGE（结构化AI图引擎）项目的一个组件。

## 许可证

Apache-2.0许可证 - 详见LICENSE文件。
