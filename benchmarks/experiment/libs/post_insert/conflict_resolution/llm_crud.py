"""
LLM CRUD Action - LLM-based Memory Conflict Resolution
=======================================================

Papers: Mem0, Mem0ᵍ
Strategy Type: conflict_resolution
Trigger Mechanism: retrieval (similarity-based)

Detects memory conflicts via semantic similarity retrieval,
uses LLM to decide ADD/UPDATE/DELETE/NOOP operations.
"""

import json
from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class LLMCRUDAction(BasePostInsertAction):
    """LLM-based CRUD decision action for conflict resolution.

    Implementation logic (based on Mem0):
    1. Retrieve similar existing memories
    2. Use LLM to decide operation: ADD/UPDATE/DELETE/NOOP
    3. Execute the decided operation

    Config Parameters:
        decision_prompt (str): LLM prompt template for CRUD decision
        top_k (int): Number of similar memories to retrieve (default: 5)
        debug_summary_only (bool): Only show summary debug lines (default: False)
    """

    STRATEGY_TYPE = "conflict_resolution"
    TRIGGER_MECHANISM = "retrieval"
    AVAILABLE_ACTIONS = ["ADD", "UPDATE", "DELETE", "NOOP"]

    def _init_action(self) -> None:
        """Initialize LLM CRUD action configuration."""
        self.top_k = self._get_config("top_k", 5)
        self.debug_summary_only = bool(self._get_config("debug_summary_only", False))
        self.decision_prompt = self._get_config(
            "decision_prompt",
            """分析新记忆与现有记忆的关系，决定操作类型。
新记忆：{new_memory}
现有相似记忆：{existing_memories}
请输出 JSON：{{"action": "ADD|UPDATE|DELETE|NOOP", "target_id": "...", "reason": "..."}}""",
        )

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute LLM CRUD decision action.

        Args:
            input_data: Input data with newly inserted memories
            service: Memory service for retrieval and CRUD operations
            llm: LLM client for decision making

        Returns:
            PostInsertOutput with CRUD operation statistics
        """
        if llm is None:
            return PostInsertOutput(
                success=False,
                action="llm_crud",
                details={"error": "LLM client required for CRUD decision"},
            )

        # Extract complete entries from insert stats
        entries = input_data.insert_stats.get("entries", [])
        if not entries:
            return PostInsertOutput(
                success=True,
                action="llm_crud",
                details={"message": "No entries to process"},
            )

        operations = {"ADD": 0, "UPDATE": 0, "DELETE": 0, "NOOP": 0}

        for new_memory in entries:
            try:
                if "embedding" not in new_memory:
                    continue

                # Retrieve similar memories
                similar_memories = self._retrieve_similar_memories(service, new_memory, self.top_k)

                # Use LLM to make decision
                decision = self._make_crud_decision(llm, new_memory, similar_memories)

                # Execute the decision
                self._execute_crud_operation(service, decision, new_memory)
                operations[decision["action"]] += 1

            except Exception as e:
                if not self.debug_summary_only:
                    print(
                        f"[DEBUG LLM_CRUD] decision_failed id={new_memory.get('id', 'unknown')} error={e}"
                    )

        return PostInsertOutput(
            success=True,
            action="llm_crud",
            details={
                "strategy_type": self.STRATEGY_TYPE,
                "trigger_mechanism": self.TRIGGER_MECHANISM,
                "operations": operations,
                "processed_entries": len(entries),
            },
        )

    def _retrieve_similar_memories(
        self, service: Any, new_memory: dict[str, Any], top_k: int
    ) -> list[dict[str, Any]]:
        """Retrieve similar existing memories."""
        if "embedding" not in new_memory:
            return []

        results = service.retrieve(vector=new_memory["embedding"], top_k=top_k)

        # Normalize ID fields
        normalized = []
        for r in results:
            rid = r.get("id") or r.get("entry_id") or r.get("node_id")
            if rid is not None:
                r["id"] = rid
            normalized.append(r)

        # Filter out the new memory itself
        new_id = new_memory.get("id")
        if new_id is not None:
            normalized = [r for r in normalized if r.get("id") != new_id]
        return normalized

    def _make_crud_decision(
        self, llm: Any, new_memory: dict[str, Any], similar_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Use LLM to make CRUD decision."""
        # Format existing memories
        existing_text = (
            "\n".join(
                [
                    f"{i + 1}. [{mem.get('id', 'unknown')}] {mem.get('text', '')}"
                    for i, mem in enumerate(similar_memories)
                ]
            )
            if similar_memories
            else "无"
        )

        # Generate decision prompt
        prompt = self.decision_prompt.replace("{new_memory}", new_memory.get("text", "")).replace(
            "{existing_memories}", existing_text
        )

        # Call LLM
        try:
            if hasattr(llm, "generate_json"):
                response = llm.generate_json(
                    prompt,
                    default={"action": "ADD", "to_delete": [], "reason": "insufficient evidence"},
                )
            else:
                response = llm.generate(prompt)
        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG LLM_CRUD] LLM call failed: {e}")
            raise

        # Parse response
        try:
            if isinstance(response, dict):
                decision = response
            else:
                if not isinstance(response, str):
                    response = json.dumps(response, ensure_ascii=False)
                try:
                    decision = json.loads(response)
                except json.JSONDecodeError:
                    extracted = self._extract_json_block(response)
                    decision = json.loads(extracted)

            # Validate and normalize decision
            action = decision.get("action")
            if action not in self.AVAILABLE_ACTIONS:
                action = "ADD"
            decision["action"] = action

            # Normalize to_delete field
            if "to_delete" in decision and isinstance(decision["to_delete"], list):
                pass
            elif decision.get("target_id"):
                decision["to_delete"] = [decision["target_id"]]
            else:
                decision["to_delete"] = []

            # Validate IDs against similar memories
            valid_ids = {m.get("id") for m in similar_memories if m.get("id")}
            normalized_to_delete = [
                tid for tid in decision["to_delete"] if tid and str(tid).strip() in valid_ids
            ]
            decision["to_delete"] = normalized_to_delete

            if decision["action"] in ["UPDATE", "DELETE"] and not decision["to_delete"]:
                decision["action"] = "NOOP"

            return decision

        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG LLM_CRUD] Parse error: {e}")
            return {"action": "ADD", "to_delete": [], "reason": "Parse error"}

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Extract first JSON object from text."""
        import re

        text = str(text).strip()
        # Try ```json ... ``` blocks
        m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if m:
            return m.group(1)

        # Extract first balanced braces
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

    def _execute_crud_operation(
        self, service: Any, decision: dict[str, Any], new_memory: dict[str, Any]
    ) -> None:
        """Execute CRUD operation based on decision."""
        action = decision["action"]

        if action == "ADD":
            return  # Keep new memory, do nothing

        if action == "UPDATE":
            # Delete old memories, keep new one
            for tid in decision.get("to_delete", []):
                try:
                    tid = str(tid).strip()
                    service.delete(tid)
                except Exception as e:
                    if not self.debug_summary_only:
                        print(f"[WARN LLM_CRUD] delete_failed action=UPDATE id={tid} error={e}")

        elif action == "DELETE":
            # Delete old memories, keep new one
            for tid in decision.get("to_delete", []):
                try:
                    tid = str(tid).strip()
                    service.delete(tid)
                except Exception as e:
                    if not self.debug_summary_only:
                        print(f"[WARN LLM_CRUD] delete_failed action=DELETE id={tid} error={e}")

        elif action == "NOOP":
            # Delete the new memory (redundant)
            try:
                nm_id = str(new_memory.get("id", "")).strip()
                if nm_id:
                    service.delete(nm_id)
            except Exception as e:
                if not self.debug_summary_only:
                    print(f"[WARN LLM_CRUD] delete_failed action=NOOP id={nm_id} error={e}")
