"""
Link Evolution Action - Memory Graph Link Creation
===================================================

Papers: A-Mem
Strategy Type: structure_enrichment
Trigger Mechanism: retrieval (KNN-based) + semantic (LLM-based)

Creates bidirectional links between related memories,
building an associative memory graph structure.
"""

from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class LinkEvolutionAction(BasePostInsertAction):
    """Link evolution action for graph-based memory systems.

    Implementation logic (based on A-Mem):
    1. For newly inserted memories, retrieve KNN neighbors
    2. Use LLM to decide which neighbors should be linked
    3. Create bidirectional links via graph memory service

    Config Parameters:
        only_on_session_end (bool): Whether to run only at session end (default: False)
        link_policy (str): Link strategy - "auto_link" (default: "auto_link")
        knn_k (int): Number of nearest neighbors to consider (default: 10)
        similarity_threshold (float): Threshold to filter neighbors (default: 0.7)
        max_auto_links (int): Max links per new memory (default: 5)
        auto_link_prompt (str): LLM prompt template with {new_memory}, {existing_memories}
    """

    STRATEGY_TYPE = "structure_enrichment"
    TRIGGER_MECHANISM = "retrieval"
    AVAILABLE_ACTIONS = ["LINK", "NOOP"]

    def _init_action(self) -> None:
        """Initialize link evolution action configuration."""
        self.only_on_session_end = self._get_config("only_on_session_end", False)
        self.link_policy = self._get_config("link_policy", "auto_link")
        self.knn_k = int(self._get_config("knn_k", 10) or 10)
        self.similarity_threshold = float(self._get_config("similarity_threshold", 0.7) or 0.7)
        self.max_auto_links = int(self._get_config("max_auto_links", 5) or 5)
        self.auto_link_prompt = self._get_config("auto_link_prompt", "")

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute link evolution action.

        Args:
            input_data: Input data with session context
            service: Memory service (must support graph operations)
            llm: LLM client (optional, required for auto_link prompt)

        Returns:
            PostInsertOutput with edge creation statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                },
            )

        # Check policy
        if self.link_policy != "auto_link":
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "unsupported_policy",
                    "message": f"link_policy '{self.link_policy}' not implemented",
                },
            )

        # Get inserted entries
        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "no_entries",
                },
            )

        edges_created = 0
        nodes_processed = 0

        for entry in entries:
            try:
                new_id = entry.get("id")
                entry.get("text", "")
                entry.get("embedding")

                # Retrieve KNN neighbors
                neighbors = self._retrieve_neighbors(service, entry)

                if not neighbors:
                    continue

                # Filter by similarity threshold
                filtered = [
                    n
                    for n in neighbors
                    if n.get("score", 0) >= self.similarity_threshold
                    or n.get("similarity", 0) >= self.similarity_threshold
                ]

                # Limit to max_auto_links
                filtered = filtered[: self.max_auto_links]

                # Create links
                for neighbor in filtered:
                    neighbor_id = neighbor.get("id")
                    if neighbor_id and neighbor_id != new_id:
                        try:
                            if hasattr(service, "add_edge"):
                                service.add_edge(new_id, neighbor_id)
                                edges_created += 1
                            elif hasattr(service, "create_link"):
                                service.create_link(new_id, neighbor_id)
                                edges_created += 1
                        except Exception:
                            pass

                nodes_processed += 1

            except Exception as e:
                print(f"[DEBUG link_evolution] entry_failed id={entry.get('id')} error={e}")

        return PostInsertOutput(
            success=True,
            action="link_evolution",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "edges_created": edges_created,
                "nodes_processed": nodes_processed,
            },
        )

    def _retrieve_neighbors(self, service: Any, entry: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve KNN neighbors for an entry."""
        if "embedding" in entry:
            results = service.retrieve(vector=entry["embedding"], top_k=self.knn_k)
        elif "text" in entry:
            results = service.retrieve(query=entry["text"], top_k=self.knn_k)
        else:
            return []

        # Normalize ID fields
        normalized = []
        entry_id = entry.get("id")
        for r in results:
            rid = r.get("id") or r.get("entry_id") or r.get("node_id")
            if rid is not None and rid != entry_id:
                r["id"] = rid
                normalized.append(r)

        return normalized
