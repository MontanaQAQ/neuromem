"""
Semantic Consolidation Action - LLM-based Memory Merging
=========================================================

Papers: TiM, MemGPT
Strategy Type: conflict_resolution
Trigger Mechanism: retrieval (similarity-based) + threshold (min count)

Consolidates semantically similar memories into merged summaries,
reducing redundancy while preserving information.
"""

from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class SemanticConsolidationAction(BasePostInsertAction):
    """Semantic consolidation action for memory deduplication.

    Implementation logic (based on TiM):
    1. Retrieve memories similar to newly inserted ones
    2. If count exceeds threshold, use LLM to merge
    3. Delete old memories and insert merged result

    Config Parameters:
        retrieve_count (int): Number of similar memories to retrieve (default: 10)
        min_merge_count (int): Minimum count to trigger merge (default: 3)
        merge_prompt (str): LLM prompt template for merging
        merge_summary_only (bool): Merge summaries instead of full text (for SeCom)
    """

    STRATEGY_TYPE = "conflict_resolution"
    TRIGGER_MECHANISM = "retrieval"
    AVAILABLE_ACTIONS = ["MERGE", "NOOP"]

    def _init_action(self) -> None:
        """Initialize semantic consolidation action configuration."""
        self.retrieve_count = self._get_config("retrieve_count", 10)
        self.min_merge_count = self._get_config("min_merge_count", 3)
        self.merge_prompt = self._get_config(
            "merge_prompt",
            "请将以下多条相似记忆合并为一条简洁的记忆：\n{memories}\n合并后的记忆：",
        )
        self.merge_summary_only = self._get_config("merge_summary_only", False)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute semantic consolidation action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service for retrieval and CRUD operations
            llm: LLM client for memory merging

        Returns:
            PostInsertOutput with merge statistics
        """
        if llm is None:
            return PostInsertOutput(
                success=False,
                action="semantic_consolidation",
                details={"error": "LLM client required for semantic consolidation"},
            )

        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="semantic_consolidation",
                details={"message": "No entries to process"},
            )

        merged_count = 0
        deleted_count = 0

        for entry in entries:
            try:
                # Retrieve similar memories
                similar_memories = self._retrieve_similar_memories(
                    service, entry, self.retrieve_count
                )

                # TiM: Only merge if count exceeds threshold
                if len(similar_memories) >= self.min_merge_count:
                    # Use LLM to merge memories
                    merged_summary = self._merge_memories(llm, similar_memories)

                    # Delete old memories
                    for mem in similar_memories:
                        service.delete(mem["id"])
                        deleted_count += 1

                    # Prepare merged entry
                    if self.merge_summary_only:
                        # SeCom mode: merge original texts, store summary in metadata
                        merged_texts = [
                            mem.get("text", "") for mem in similar_memories if mem.get("text")
                        ]
                        merged_text = "\n\n---\n\n".join(merged_texts)
                        merged_metadata = {
                            "merged_from": [m["id"] for m in similar_memories],
                            "summary": merged_summary,
                            "segment_count": len(similar_memories),
                        }
                    else:
                        # Default: merged summary becomes the text
                        merged_text = merged_summary
                        merged_metadata = {"merged_from": [m["id"] for m in similar_memories]}

                    # Insert merged memory
                    merged_embedding = (
                        similar_memories[0].get("embedding") if similar_memories else None
                    )
                    service.insert(
                        entry=merged_text,
                        vector=merged_embedding,
                        metadata=merged_metadata,
                    )
                    merged_count += 1

            except Exception as e:
                details = input_data.data.setdefault("errors", [])
                details.append(
                    {
                        "entry_id": entry.get("id", "unknown"),
                        "action": "semantic_consolidation",
                        "error": str(e),
                    }
                )

        return PostInsertOutput(
            success=True,
            action="semantic_consolidation",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "merged_count": merged_count,
                "deleted_count": deleted_count,
                "processed_entries": len(entries),
            },
        )

    def _retrieve_similar_memories(
        self, service: Any, entry: dict[str, Any], count: int
    ) -> list[dict[str, Any]]:
        """Retrieve similar memories for an entry."""
        if "embedding" not in entry:
            return []

        results = service.retrieve(vector=entry["embedding"], top_k=count)

        # Normalize and filter
        normalized = []
        entry_id = entry.get("id")
        for r in results:
            rid = r.get("id") or r.get("entry_id") or r.get("node_id")
            if rid is not None and rid != entry_id:
                r["id"] = rid
                normalized.append(r)

        return normalized

    def _merge_memories(self, llm: Any, memories: list[dict[str, Any]]) -> str:
        """Use LLM to merge multiple memories into one."""
        # Format memories for prompt
        memories_text = "\n".join(
            [f"{i + 1}. {mem.get('text', '')}" for i, mem in enumerate(memories)]
        )

        prompt = self.merge_prompt.replace("{memories}", memories_text)

        # Call LLM
        if hasattr(llm, "generate"):
            return llm.generate(prompt)
        return str(llm(prompt))
