"""Multi Query Merge - 多查询合并

使用场景: MemGPT

功能: 执行多个相关查询并合并结果
"""

from typing import Any

from ..base import (
    BasePostRetrievalAction,
    MemoryItem,
    PostRetrievalInput,
    PostRetrievalOutput,
)


class MultiQueryMergeAction(BasePostRetrievalAction):
    """多查询合并策略

    生成多个相关查询（如改写、扩展），分别检索后合并结果。
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.num_queries = self.config.get("num_queries", 3)
        self.merge_strategy = self.config.get("merge_strategy", "union")  # union, intersection
        self.dedup = self.config.get("dedup", True)

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostRetrievalOutput:
        """执行多查询合并

        Args:
            input_data: 输入数据
            service: 记忆服务代理
            llm: LLM 生成器（用于生成改写查询）

        Returns:
            PostRetrievalOutput: 合并后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        original_items = self._convert_to_items(memory_data)

        if service is None or llm is None:
            # 如果没有服务或 LLM，返回原始结果
            return PostRetrievalOutput(
                memory_items=original_items,
                metadata={
                    "action": "merge.multi_query",
                    "warning": "No service or LLM available",
                },
            )

        question = input_data.data.get("question", "")
        if not question:
            return PostRetrievalOutput(
                memory_items=original_items,
                metadata={"action": "merge.multi_query", "warning": "No question provided"},
            )

        # 生成多个查询变体
        print(f"[DEBUG] MultiQuery starting with question: {question}")
        queries = self._generate_queries(question, llm)
        print(f"[DEBUG] MultiQuery total generated queries: {len(queries)}")

        # 对每个查询执行检索
        all_results = [original_items]  # 包含原始结果
        print(f"[DEBUG] MultiQuery original results: {len(original_items)} items")

        for i, query in enumerate(queries):
            try:
                print(f"[DEBUG] MultiQuery executing query {i + 1}/{len(queries)}: {query}")
                results = self._retrieve_with_query(query, service, input_data)
                print(f"[DEBUG] MultiQuery query {i + 1} returned {len(results)} items")
                all_results.append(results)
            except Exception as e:  # noqa: BLE001
                # 如果单个查询失败，跳过
                print(f"[DEBUG] MultiQuery query {i + 1} failed: {type(e).__name__}: {e}")
                continue

        # 合并所有结果
        print(
            f"[DEBUG] MultiQuery merging {len(all_results)} result sets using '{self.merge_strategy}' strategy"
        )
        merged_items = self._merge_all_results(all_results)
        print(f"[DEBUG] MultiQuery merged total: {len(merged_items)} items")

        return PostRetrievalOutput(
            memory_items=merged_items,
            metadata={
                "action": "merge.multi_query",
                "num_queries": len(queries),
                "merge_strategy": self.merge_strategy,
                "total_results": len(merged_items),
            },
        )

    def _generate_queries(self, question: str, llm: Any) -> list[str]:
        """生成多个查询变体

        Args:
            question: 原始问题
            llm: LLM 实例

        Returns:
            查询列表（不包含原始问题）
        """
        queries = []

        # 使用 LLM 生成查询改写
        try:
            prompt = f"""Rewrite the following question in {self.num_queries - 1} different ways. Keep the meaning the same but use different words.

Original question: {question}

Rules:
- Output ONLY the rewritten questions, one per line
- NO explanations, labels, or formatting
- NO ** or markdown
- Each line starts with a number and period (e.g., "1. ")

Example:
1. What programming languages has James used?
2. Which coding languages is James familiar with?

Now rewrite this question:"""

            response = llm.generate(prompt)
            print(f"[DEBUG] MultiQuery LLM Response:\n{response}")

            # 解析响应 - 改进的逻辑
            lines = response.strip().split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 移除编号前缀（1. 2. - * 等）
                import re

                # 匹配 "1." "2." "1)" "-" "*" 等开头
                cleaned = re.sub(r"^[\d\-\*]+[\.\)]\s*", "", line)
                # 移除 markdown 格式
                cleaned = re.sub(r"\*\*[^*]+\*\*:\s*", "", cleaned)
                # 移除引号
                cleaned = cleaned.strip("\"'")

                if cleaned and len(cleaned) > 10:  # 至少10个字符才是有效查询
                    queries.append(cleaned)

            # 限制数量
            queries = queries[: self.num_queries - 1]
            print(f"[DEBUG] MultiQuery Generated {len(queries)} variants: {queries}")
        except Exception as e:  # noqa: BLE001
            # 如果生成失败，返回空列表
            print(f"[DEBUG] MultiQuery generation failed: {type(e).__name__}: {e}")

        return queries

    def _retrieve_with_query(
        self, query: str, service: Any, input_data: PostRetrievalInput
    ) -> list[MemoryItem]:
        """使用给定查询检索记忆

        Args:
            query: 查询文本
            service: 记忆服务
            input_data: 原始输入数据

        Returns:
            检索结果列表
        """
        try:
            # 使用 service proxy 的 search 方法重新检索
            # service 是 _ServiceProxy 实例，提供 search() 和 retrieve() 方法
            top_k = input_data.config.get("top_k", 10)

            # 根据服务类型选择合适的检索方法
            try:
                # 优先使用 search 方法（语义检索）
                results = service.search(query=query, top_k=top_k)
            except Exception:
                # 如果 search 失败，尝试 retrieve（图检索）
                try:
                    results = service.retrieve(query=query, top_k=top_k)
                except Exception:  # noqa: BLE001
                    return []

            # 转换为 MemoryItem 格式
            items = []
            for idx, result in enumerate(results):
                item = MemoryItem(
                    text=result.get("content", ""),
                    score=result.get("score"),
                    metadata=result.get("metadata", {}),
                    original_index=idx,
                )
                items.append(item)

            return items
        except Exception:  # noqa: BLE001
            # 如果检索失败，返回空列表（降级处理）
            return []

    def _merge_all_results(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """合并所有查询的结果

        Args:
            all_results: 所有查询结果的列表

        Returns:
            合并后的结果
        """
        if self.merge_strategy == "union":
            return self._merge_union(all_results)
        if self.merge_strategy == "intersection":
            return self._merge_intersection(all_results)
        # 默认使用 union
        return self._merge_union(all_results)

    def _merge_union(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """Union 合并策略

        Args:
            all_results: 所有查询结果

        Returns:
            合并后的结果（去重）
        """
        if not self.dedup:
            # 不去重，直接拼接
            merged = []
            for results in all_results:
                merged.extend(results)
            return merged

        # 去重（基于 text）
        seen_texts = set()
        merged = []

        for results in all_results:
            for item in results:
                if item.text not in seen_texts:
                    merged.append(item)
                    seen_texts.add(item.text)

        return merged

    def _merge_intersection(self, all_results: list[list[MemoryItem]]) -> list[MemoryItem]:
        """Intersection 合并策略

        Args:
            all_results: 所有查询结果

        Returns:
            交集结果
        """
        if not all_results:
            return []

        # 提取第一个查询的文本集合
        intersection = {item.text for item in all_results[0]}

        # 与后续查询的结果求交集
        for results in all_results[1:]:
            result_texts = {item.text for item in results}
            intersection &= result_texts

        # 构建最终结果（保持第一个查询的顺序）
        merged = []
        for item in all_results[0]:
            if item.text in intersection:
                merged.append(item)

        return merged
