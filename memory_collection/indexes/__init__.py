"""索引组件模块

这个包包含 neuromem 层的索引实现：
- BaseIndex: 索引抽象基类（T1.3）
- IndexFactory: 索引工厂（T1.3）
- MockIndex: 临时 mock 对象（用于 T1.2）
- FAISSIndex: FAISS 向量索引（T1.6）
- GraphIndex: NetworkX 图索引（T1.8）
- 各种具体索引实现（T1.4-T1.7）
"""

__all__ = [
    "BaseIndex",
    "IndexFactory",
    "MockIndex",
    "FIFOQueueIndex",
    "BM25Index",
    "FAISSIndex",
    "GraphIndex",
]

from .base_index import BaseIndex
from .bm25_index import BM25Index
from .faiss_index import FAISSIndex
from .fifo_queue_index import FIFOQueueIndex
from .graph_index import GraphIndex
from .index_factory import IndexFactory
from .mock_index import MockIndex

# 条件导入（依赖可选包）
try:
    from .lsh_index import LSHIndex

    __all__.append("LSHIndex")
    IndexFactory.register("lsh", LSHIndex)
except ImportError:
    pass

try:
    from .segment_index import SegmentIndex

    __all__.append("SegmentIndex")
    IndexFactory.register("segment", SegmentIndex)
except ImportError:
    pass

# 自动注册索引类型（核心索引）
IndexFactory.register("fifo", FIFOQueueIndex)
IndexFactory.register("bm25", BM25Index)
IndexFactory.register("faiss", FAISSIndex)
IndexFactory.register("graph", GraphIndex)
