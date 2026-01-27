"""
Link Evolution Action - Memory Graph Link Creation
===================================================

Papers: A-Mem
Strategy Type: structure_enrichment
Trigger Mechanism: retrieval (KNN-based) + semantic (LLM-based)

Creates bidirectional links between related memories,
building an associative memory graph structure.
"""

import json
from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class LinkEvolutionAction(BasePostInsertAction):
    """Link evolution action for graph-based memory systems.

    Implementation logic (based on A-Mem):
    1. For newly inserted memories, retrieve KNN neighbors
    2. Use LLM to decide which neighbors should be linked and how to evolve
    3. Execute actions: strengthen (create links + update tags) and update_neighbor (update neighbor metadata)

    Config Parameters:
        only_on_session_end (bool): Whether to run only at session end (default: False)
        link_policy (str): Link strategy - "auto_link" or "llm_link" (default: "llm_link")
        knn_k (int): Number of nearest neighbors to consider (default: 5)
        similarity_threshold (float): Threshold to filter neighbors for auto_link (default: 0.7)
        max_auto_links (int): Max links per new memory for auto_link (default: 5)
        evolution_system_prompt (str): LLM prompt template for evolution decision
        debug_summary_only (bool): Only show summary debug lines (default: False)
    """

    STRATEGY_TYPE = "structure_enrichment"
    TRIGGER_MECHANISM = "retrieval"
    AVAILABLE_ACTIONS = ["strengthen", "update_neighbor"]

    def _init_action(self) -> None:
        """Initialize link evolution action configuration."""
        self.only_on_session_end = self._get_config("only_on_session_end", False)
        self.link_policy = self._get_config("link_policy", "llm_link")
        self.knn_k = int(self._get_config("knn_k", 5) or 5)
        self.similarity_threshold = float(self._get_config("similarity_threshold", 0.7) or 0.7)
        self.max_auto_links = int(self._get_config("max_auto_links", 5) or 5)
        self.debug_summary_only = bool(self._get_config("debug_summary_only", False))

        # A-Mem evolution system prompt
        default_prompt = """You are an AI memory evolution agent responsible for managing and evolving a knowledge base.
Analyze the new memory note according to keywords and context, also with their several nearest neighbors memory.
Make decisions about its evolution.

The new memory context:
{context}
content: {content}
keywords: {keywords}

The nearest neighbors memories:
{nearest_neighbors_memories}

Based on this information, determine:
1. Should this memory be evolved? Consider its relationships with other memories.
2. What specific actions should be taken (strengthen, update_neighbor)?
   2.1 If choose to strengthen the connection, which memory should it be connected to? Can you give the updated tags of this memory?
   2.2 If choose to update_neighbor, you can update the context and tags of these memories based on the understanding of these memories. If the context and the tags are not updated, the new context and tags should be the same as the original ones. Generate the new context and tags in the sequential order of the input neighbors.
Tags should be determined by the content of these characteristic of these memories, which can be used to retrieve them later and categorize them.
Note that the length of new_tags_neighborhood must equal the number of input neighbors, and the length of new_context_neighborhood must equal the number of input neighbors.
The number of neighbors is {neighbor_number}.
Return your decision in JSON format with the following structure:
{{
    "should_evolve": true or false,
    "actions": ["strengthen", "update_neighbor"],
    "suggested_connections": [0, 1, 2],
    "tags_to_update": ["tag_1", "tag_n"],
    "new_context_neighborhood": ["new context", "new context"],
    "new_tags_neighborhood": [["tag_1", "tag_n"], ["tag_1", "tag_n"]]
}}"""
        self.evolution_system_prompt = self._get_config("evolution_system_prompt", default_prompt)

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
            llm: LLM client (required for llm_link policy)

        Returns:
            PostInsertOutput with edge creation and evolution statistics
        """
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="link_evolution",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                },
            )

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

        if self.link_policy == "llm_link":
            return self._execute_llm_link(entries, service, llm)
        if self.link_policy == "auto_link":
            return self._execute_auto_link(entries, service)

        return PostInsertOutput(
            success=False,
            action="link_evolution",
            details={
                "error": f"Unknown link_policy: {self.link_policy}",
            },
        )

    def _execute_llm_link(
        self,
        entries: list[dict],
        service: Any,
        llm: Any | None,
    ) -> PostInsertOutput:
        """Execute LLM-based link evolution (A-Mem style)."""
        if llm is None:
            return PostInsertOutput(
                success=False,
                action="link_evolution",
                details={"error": "LLM client required for llm_link policy"},
            )

        stats = {
            "evolved_memories": 0,
            "edges_created": 0,
            "neighbors_updated": 0,
            "actions": {"strengthen": 0, "update_neighbor": 0},
        }

        for entry in entries:
            try:
                neighbors = self._retrieve_neighbors(service, entry)
                if not neighbors:
                    continue

                decision = self._make_link_decision(llm, entry, neighbors)
                if not decision.get("should_evolve", False):
                    continue

                stats["evolved_memories"] += 1
                actions = decision.get("actions", [])

                if "strengthen" in actions:
                    edges = self._execute_strengthen(service, entry, neighbors, decision)
                    stats["edges_created"] += edges
                    stats["actions"]["strengthen"] += 1

                if "update_neighbor" in actions:
                    updated = self._execute_update_neighbor(service, neighbors, decision)
                    stats["neighbors_updated"] += updated
                    stats["actions"]["update_neighbor"] += 1

            except Exception as e:
                if not self.debug_summary_only:
                    print(f"[DEBUG link_evolution] llm_link_failed id={entry.get('id')} error={e}")

        return PostInsertOutput(
            success=True,
            action="link_evolution",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "policy": "llm_link",
                **stats,
            },
        )

    def _execute_auto_link(
        self,
        entries: list[dict],
        service: Any,
    ) -> PostInsertOutput:
        """Execute simple auto-link (fallback strategy)."""
        edges_created = 0
        nodes_processed = 0

        for entry in entries:
            try:
                new_id = entry.get("id")
                neighbors = self._retrieve_neighbors(service, entry)
                if not neighbors:
                    continue

                filtered = [
                    n
                    for n in neighbors
                    if n.get("score", 0) >= self.similarity_threshold
                    or n.get("similarity", 0) >= self.similarity_threshold
                ]
                filtered = filtered[: self.max_auto_links]

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
                if not self.debug_summary_only:
                    print(f"[DEBUG link_evolution] auto_link_failed id={entry.get('id')} error={e}")

        return PostInsertOutput(
            success=True,
            action="link_evolution",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "policy": "auto_link",
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

        normalized = []
        entry_id = entry.get("id")
        for r in results:
            rid = r.get("id") or r.get("entry_id") or r.get("node_id")
            if rid is not None and rid != entry_id:
                r["id"] = rid
                normalized.append(r)

        return normalized

    def _make_link_decision(
        self, llm: Any, entry: dict[str, Any], neighbors: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Use LLM to make link evolution decision (A-Mem style)."""
        neighbor_text = ""
        for i, n in enumerate(neighbors):
            neighbor_text += f"memory index: {i}\t"
            neighbor_text += f"memory content: {n.get('text', '')}\t"
            neighbor_text += f"memory context: {n.get('context', '')}\t"
            neighbor_text += f"memory keywords: {n.get('keywords', [])}\t"
            neighbor_text += f"memory tags: {n.get('tags', [])}\n"

        prompt = self.evolution_system_prompt.format(
            context=entry.get("context", ""),
            content=entry.get("text", ""),
            keywords=entry.get("keywords", []),
            nearest_neighbors_memories=neighbor_text,
            neighbor_number=len(neighbors),
        )

        try:
            if hasattr(llm, "generate_json"):
                response = llm.generate_json(
                    prompt,
                    default={
                        "should_evolve": False,
                        "actions": [],
                        "suggested_connections": [],
                        "tags_to_update": [],
                        "new_context_neighborhood": [],
                        "new_tags_neighborhood": [],
                    },
                )
            else:
                response = llm.generate(prompt)
        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG link_evolution] LLM call failed: {e}")
            raise

        try:
            if isinstance(response, dict):
                decision = response
            else:
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)

                response = response.strip()
                if not response.startswith("{"):
                    start_idx = response.find("{")
                    if start_idx != -1:
                        response = response[start_idx:]
                if not response.endswith("}"):
                    end_idx = response.rfind("}")
                    if end_idx != -1:
                        response = response[: end_idx + 1]

                try:
                    decision = json.loads(response)
                except json.JSONDecodeError:
                    extracted = self._extract_json_block(response)
                    decision = json.loads(extracted)

            if not isinstance(decision.get("should_evolve"), bool):
                decision["should_evolve"] = False

            for key in [
                "actions",
                "suggested_connections",
                "tags_to_update",
                "new_context_neighborhood",
                "new_tags_neighborhood",
            ]:
                if key not in decision or not isinstance(decision[key], list):
                    decision[key] = []

            valid_connections = [
                idx
                for idx in decision["suggested_connections"]
                if isinstance(idx, int) and 0 <= idx < len(neighbors)
            ]
            decision["suggested_connections"] = valid_connections

            return decision

        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG link_evolution] Parse error: {e}")
            return {
                "should_evolve": False,
                "actions": [],
                "suggested_connections": [],
                "tags_to_update": [],
                "new_context_neighborhood": [],
                "new_tags_neighborhood": [],
            }

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Extract first JSON object from text."""
        import re

        text = str(text).strip()
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1)

        start = text.find("{")
        if start == -1:
            return text

        depth = 0
        end = start
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end > start:
            return text[start:end]
        return text

    def _execute_strengthen(
        self,
        service: Any,
        entry: dict[str, Any],
        neighbors: list[dict[str, Any]],
        decision: dict[str, Any],
    ) -> int:
        """Execute strengthen action: create links and update tags."""
        edges_created = 0
        new_id = entry.get("id")

        for conn_idx in decision.get("suggested_connections", []):
            if 0 <= conn_idx < len(neighbors):
                neighbor_id = neighbors[conn_idx].get("id")
                if neighbor_id and neighbor_id != new_id:
                    try:
                        if hasattr(service, "add_edge"):
                            service.add_edge(new_id, neighbor_id)
                            edges_created += 1
                        elif hasattr(service, "create_link"):
                            service.create_link(new_id, neighbor_id)
                            edges_created += 1
                    except Exception as e:
                        if not self.debug_summary_only:
                            print(f"[WARN link_evolution] add_edge failed: {e}")

        tags_to_update = decision.get("tags_to_update", [])
        if tags_to_update and hasattr(service, "update"):
            try:
                service.update(new_id, {"tags": tags_to_update})
            except Exception as e:
                if not self.debug_summary_only:
                    print(f"[WARN link_evolution] update tags failed: {e}")

        return edges_created

    def _execute_update_neighbor(
        self,
        service: Any,
        neighbors: list[dict[str, Any]],
        decision: dict[str, Any],
    ) -> int:
        """Execute update_neighbor action: update context and tags of neighbors."""
        updated_count = 0
        new_context_list = decision.get("new_context_neighborhood", [])
        new_tags_list = decision.get("new_tags_neighborhood", [])

        max_updates = min(len(neighbors), len(new_context_list), len(new_tags_list))
        for i in range(max_updates):
            neighbor_id = neighbors[i].get("id")
            if not neighbor_id:
                continue

            new_context = new_context_list[i]
            new_tags = new_tags_list[i]

            if new_context == neighbors[i].get("context", "") and new_tags == neighbors[i].get(
                "tags", []
            ):
                continue

            try:
                if hasattr(service, "update"):
                    update_data = {}
                    if new_context:
                        update_data["context"] = new_context
                    if new_tags:
                        update_data["tags"] = new_tags

                    if update_data:
                        service.update(neighbor_id, update_data)
                        updated_count += 1
            except Exception as e:
                if not self.debug_summary_only:
                    print(f"[WARN link_evolution] update_neighbor failed id={neighbor_id}: {e}")

        return updated_count
