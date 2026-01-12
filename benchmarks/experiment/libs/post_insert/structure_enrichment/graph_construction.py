"""
Graph Construction Action - Knowledge Graph Building
=====================================================

Papers: HippoRAG
Strategy Type: structure_enrichment
Trigger Mechanism: semantic (entity extraction + relation linking)

Builds knowledge graph structure by:
- Extracting entities from memories
- Creating relation edges between entities
"""

from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class GraphConstructionAction(BasePostInsertAction):
    """Knowledge graph construction action.

    Implementation logic (based on HippoRAG):
    1. Extract entities from newly inserted memories
    2. Use LLM to identify relations between entities
    3. Build knowledge graph with entity nodes and relation edges

    Config Parameters:
        extraction_prompt (str): LLM prompt for entity extraction
        relation_prompt (str): LLM prompt for relation identification
        entity_types (list): Types of entities to extract (default: ["person", "location", "event"])
        only_on_session_end (bool): Execute only at session end (default: False)
    """

    STRATEGY_TYPE = "structure_enrichment"
    TRIGGER_MECHANISM = "semantic"
    AVAILABLE_ACTIONS = ["ADD_NODE", "ADD_EDGE", "NOOP"]

    def _init_action(self) -> None:
        """Initialize graph construction action configuration."""
        self.only_on_session_end = self._get_config("only_on_session_end", False)
        self.entity_types = self._get_config("entity_types", ["person", "location", "event"])
        self.extraction_prompt = self._get_config(
            "extraction_prompt",
            """从以下文本中提取实体（人物、地点、事件等）：
文本：{text}
请输出 JSON 格式：[{{"entity": "...", "type": "..."}}]""",
        )
        self.relation_prompt = self._get_config(
            "relation_prompt",
            """分析以下实体之间的关系：
实体列表：{entities}
请输出 JSON 格式：[{{"source": "...", "target": "...", "relation": "..."}}]""",
        )

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute graph construction action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service (must support graph operations)
            llm: LLM client for entity/relation extraction

        Returns:
            PostInsertOutput with graph construction statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="graph_construction",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                },
            )

        if llm is None:
            return PostInsertOutput(
                success=False,
                action="graph_construction",
                details={"error": "LLM client required for entity extraction"},
            )

        # Check if service supports graph operations
        if not hasattr(service, "add_entity") and not hasattr(service, "add_node"):
            return PostInsertOutput(
                success=False,
                action="graph_construction",
                details={"error": "Service does not support graph operations"},
            )

        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="graph_construction",
                details={
                    "skipped": True,
                    "reason": "no_entries",
                },
            )

        entities_added = 0
        relations_added = 0

        for entry in entries:
            try:
                text = entry.get("text", "")
                if not text:
                    continue

                # Extract entities
                entities = self._extract_entities(llm, text)

                # Add entity nodes
                for entity in entities:
                    try:
                        if hasattr(service, "add_entity"):
                            service.add_entity(entity["entity"], entity.get("type", "unknown"))
                        elif hasattr(service, "add_node"):
                            service.add_node(
                                entity["entity"], {"type": entity.get("type", "unknown")}
                            )
                        entities_added += 1
                    except Exception:
                        pass

                # Extract and add relations
                if len(entities) >= 2:
                    relations = self._extract_relations(llm, entities)
                    for rel in relations:
                        try:
                            if hasattr(service, "add_relation"):
                                service.add_relation(rel["source"], rel["target"], rel["relation"])
                            elif hasattr(service, "add_edge"):
                                service.add_edge(
                                    rel["source"], rel["target"], {"relation": rel["relation"]}
                                )
                            relations_added += 1
                        except Exception:
                            pass

            except Exception as e:
                print(f"[DEBUG graph_construction] entry_failed id={entry.get('id')} error={e}")

        return PostInsertOutput(
            success=True,
            action="graph_construction",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "entities_added": entities_added,
                "relations_added": relations_added,
                "processed_entries": len(entries),
            },
        )

    def _extract_entities(self, llm: Any, text: str) -> list[dict[str, Any]]:
        """Extract entities from text using LLM."""
        import json

        prompt = self.extraction_prompt.replace("{text}", text)

        try:
            if hasattr(llm, "generate_json"):
                return llm.generate_json(prompt, default=[])
            response = llm.generate(prompt)
            return json.loads(response) if isinstance(response, str) else response
        except Exception:
            return []

    def _extract_relations(self, llm: Any, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract relations between entities using LLM."""
        import json

        entities_text = ", ".join([e.get("entity", "") for e in entities])
        prompt = self.relation_prompt.replace("{entities}", entities_text)

        try:
            if hasattr(llm, "generate_json"):
                return llm.generate_json(prompt, default=[])
            response = llm.generate(prompt)
            return json.loads(response) if isinstance(response, str) else response
        except Exception:
            return []
