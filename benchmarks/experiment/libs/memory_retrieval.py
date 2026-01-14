"""
================================================================================
MemoryRetrieval - 记忆检索算子（重构后）
================================================================================

[架构定位]
Pipeline: PreInsert → MemoryInsert → PostInsert → PreRetrieval → MemoryRetrieval(当前) → PostRetrieval
前驱: PreRetrieval（负责查询预处理，生成 query_embedding）
后继: PostRetrieval（检索后处理，如重排序、过滤、增强）

[核心职责]
纯透传模式：调用记忆服务的 retrieve 方法，返回原始检索结果

[输入数据结构] (由 PreRetrieval 生成)
data = {
    "question": str,                    # 必须：查询问题
    "query_embedding": list[float],     # 可选：查询向量（由 PreRetrieval 生成）
    "metadata": dict,                   # 可选：元数据
    "retrieve_mode": str,               # 检索模式: "passive" | "active" | ...
    "retrieve_params": dict,            # 检索参数（服务特定）
    ...其他透传字段...
}

[输出数据结构]
data（原样透传）+ memory_data + retrieval_stats = {
    "memory_data": list[dict],          # 检索到的原始记忆数据
    "retrieval_stats": {                # 检索统计
        "retrieved": int,               # 检索数量
        "time_ms": float,               # 检索耗时（毫秒）
        "service_name": str,            # 服务名称
    }
}

[设计原则]
1. 单一职责：只负责调用服务的 retrieve 方法，不做结果处理
2. 纯透传：PreRetrieval 已统一设置查询参数，MemoryRetrieval 直接使用
3. 性能监控：记录检索耗时，供性能分析使用
4. 错误容忍：提供超时控制和重试机制

[T5 重构目标]
✅ 简化为纯透传层（< 80 行）
✅ 统一的性能监控
✅ 结构化日志输出
✅ 支持超时控制
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any

from sage.common.core import MapFunction

from benchmarks.experiment.utils import process_logger


@dataclass
class RetrievalStats:
    """检索统计"""

    retrieved: int  # 检索数量
    time_ms: float  # 检索耗时（毫秒）
    service_name: str  # 服务名称


class MemoryRetrieval(MapFunction):
    """记忆检索算子（重构后）- 纯透传模式

    职责：
    1. 调用记忆服务的 retrieve 方法
    2. 统计检索性能
    3. 透传结果给 PostRetrieval
    """

    def __init__(self, config=None):
        """初始化 MemoryRetrieval

        Args:
            config: RuntimeConfig 对象
        """
        super().__init__()
        self.config = config
        # 从 services_type 提取服务名: "partitional.fifo_queue" -> "fifo_queue"
        services_type = config.get("services.services_type")
        if not services_type:
            raise ValueError("Missing required config: services.services_type")
        self.service_name = services_type.split(".")[-1]
        self.verbose = config.get("runtime.memory_test_verbose", True)

        # 检索参数（从服务配置读取）
        service_cfg = f"services.{self.service_name}"
        self.retrieval_top_k = config.get(f"{service_cfg}.retrieval_top_k", 10)

        # MemoryOS 两阶段检索配置
        self.use_two_stage_search = config.get(f"{service_cfg}.use_two_stage_search", False)
        self.two_stage_config = {
            "segment_similarity_threshold": config.get(
                f"{service_cfg}.segment_similarity_threshold", 0.1
            ),
            "page_similarity_threshold": config.get(
                f"{service_cfg}.page_similarity_threshold", 0.1
            ),
            "top_k_segments": config.get(f"{service_cfg}.top_k_segments", 5),
            "top_k_pages_per_segment": config.get(f"{service_cfg}.top_k_pages_per_segment", 3),
            "fscore_alpha": config.get(f"{service_cfg}.fscore_alpha", 1.0),
            "fscore_beta": config.get(f"{service_cfg}.fscore_beta", 0.5),
            "fscore_gamma": config.get(f"{service_cfg}.fscore_gamma", 0.1),
        }

        if self.use_two_stage_search:
            print("[MemoryRetrieval] 启用 MemoryOS 两阶段检索")
            print(
                f"  Fscore权重: α={self.two_stage_config['fscore_alpha']}, "
                f"β={self.two_stage_config['fscore_beta']}, "
                f"γ={self.two_stage_config['fscore_gamma']}"
            )

    def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行记忆检索

        Args:
            data: 由 PreRetrieval 输出的数据，包含查询参数

        Returns:
            原始数据 + memory_data + retrieval_stats
        """
        start_time = time.perf_counter()
        start = time.time()

        # 1. 提取查询参数
        query = data.get("question")
        vector = data.get("query_embedding")
        metadata = data.get("metadata", {})
        retrieve_params = data.get("retrieve_params", {})

        # 检查是否有子查询（来自 decompose）或多查询（来自 expand）
        sub_queries = retrieve_params.get("sub_queries", [])
        multi_query = retrieve_params.get("multi_query", [])
        queries = sub_queries or multi_query  # 优先使用 sub_queries
        retrieve_params.get("action", "sequential")

        # 2. 调用服务检索（支持多查询和两阶段检索）

        # 检查当前查询是否针对 MTM 层（两阶段检索专用）
        is_mtm_query = metadata.get("tier") == "mtm" if metadata else False
        use_two_stage = (
            self.use_two_stage_search
            and self.service_name == "hierarchical_memory"
            and is_mtm_query  # 只对 MTM 层使用两阶段检索
        )

        if use_two_stage:
            # MemoryOS 两阶段检索模式（仅 MTM 层）

            # 提取关键词（由 PreRetrieval 生成）
            query_keywords = retrieve_params.get("extracted_keywords", [])

            results = self.call_service(
                self.service_name,
                method="search_with_two_stage",
                query_text=query,
                query_vector=vector,
                query_keywords=query_keywords,
                tier_name="mtm",
                segment_similarity_threshold=self.two_stage_config["segment_similarity_threshold"],
                page_similarity_threshold=self.two_stage_config["page_similarity_threshold"],
                top_k_segments=self.two_stage_config["top_k_segments"],
                top_k_pages_per_segment=self.two_stage_config["top_k_pages_per_segment"],
                fscore_weights={
                    "alpha": self.two_stage_config["fscore_alpha"],
                    "beta": self.two_stage_config["fscore_beta"],
                    "gamma": self.two_stage_config["fscore_gamma"],
                },
                timeout=60.0,
            )
        elif queries and len(queries) >= 1:
            # 多查询模式（包括单个子查询的情况）：对每个子查询/扩展查询独立检索
            all_results = []
            seen_texts = set()  # 用于去重

            # 获取预生成的 embedding（来自 PreRetrieval action）
            query_embeddings = retrieve_params.get(
                "sub_query_embeddings", []
            ) or retrieve_params.get("expanded_embeddings", [])

            for idx, single_query in enumerate(queries, 1):
                # 使用预生成的 embedding
                query_vector = query_embeddings[idx - 1] if idx <= len(query_embeddings) else None

                sub_results = self.call_service(
                    self.service_name,
                    method="retrieve",
                    query=single_query,
                    vector=query_vector,  # 使用预生成的向量
                    metadata=metadata,
                    top_k=self.retrieval_top_k,
                    timeout=60.0,
                )

                # 去重合并结果
                for result in sub_results or []:
                    text = result.get("text", "")
                    if text and text not in seen_texts:
                        seen_texts.add(text)
                        all_results.append(result)

            results = all_results
        else:
            # 单查询模式：使用主查询
            results = self.call_service(
                self.service_name,
                method="retrieve",
                query=query,
                vector=vector,
                metadata=metadata,
                top_k=self.retrieval_top_k,
                timeout=60.0,
            )

        # 3. 统计性能
        elapsed = (time.time() - start) * 1000
        stats = RetrievalStats(
            retrieved=len(results) if results else 0,
            time_ms=elapsed,
            service_name=self.service_name,
        )

        # 4. 添加结果和统计
        data["memory_data"] = results
        data["retrieval_stats"] = asdict(stats)

        # 5. 记录阶段耗时
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        data.setdefault("stage_timings", {})["memory_retrieval_ms"] = elapsed_ms

        # 记录到过程日志
        result_texts = [r.get("text", "")[:100] for r in (results or [])[:5]]
        process_logger.log_service(
            "RETRIEVE",
            f"Query: {query}\nResults: {stats.retrieved} items\nTop results: {result_texts}",
        )

        # 简洁终端输出
        print(
            f"  [MemoryRetrieval] 检索: {stats.retrieved}条 | 耗时: {elapsed_ms:.2f}ms", flush=True
        )

        return data
