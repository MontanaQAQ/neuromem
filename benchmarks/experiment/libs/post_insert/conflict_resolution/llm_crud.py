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
        # JSON输出需要足够的tokens，默认128（比QA的32大很多）
        self.llm_max_tokens = self._get_config("llm_max_tokens", 128)
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
                # 确保 ID 是简单类型（字符串/数字），避免字典/列表导致后续 unhashable 错误
                if isinstance(rid, (dict, list)):
                    rid = str(rid)
                r["id"] = rid
            normalized.append(r)

        # Filter out the new memory itself
        new_id = new_memory.get("id")
        if new_id is not None:
            # 同样处理 new_id
            if isinstance(new_id, (dict, list)):
                new_id = str(new_id)
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

        # Call LLM (覆盖max_tokens确保JSON输出完整)
        try:
            if hasattr(llm, "generate_json"):
                response = llm.generate_json(
                    prompt,
                    default={"action": "ADD", "to_delete": [], "reason": "parse_failed"},
                    max_tokens=self.llm_max_tokens,
                )
            else:
                response = llm.generate(prompt, max_tokens=self.llm_max_tokens)
        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG LLM_CRUD] LLM call failed: {e}")
                print(f"[DEBUG LLM_CRUD] Prompt: {prompt[:200]}...")
                print(
                    f"[DEBUG LLM_CRUD] Response type: {type(response).__name__ if 'response' in locals() else 'N/A'}"
                )
            raise

        # Parse response - 增强解析，支持多种格式
        try:
            return self._parse_llm_response(response, similar_memories)
        except Exception as e:
            if not self.debug_summary_only:
                print(f"[DEBUG LLM_CRUD] Parse error: {e}, response={str(response)[:200]}")
            # Fallback: 尝试从文本中提取action关键字
            return self._fallback_extract_action(response, similar_memories)

    def _parse_llm_response(
        self, response: Any, similar_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Parse LLM response with multiple fallback strategies."""

        # Strategy 1: 直接是dict
        if isinstance(response, dict):
            return self._normalize_decision(response, similar_memories)

        # 转换为字符串
        if not isinstance(response, str):
            response = json.dumps(response, ensure_ascii=False)

        response = response.strip()

        # Strategy 2: 直接JSON解析
        try:
            decision = json.loads(response)
            return self._normalize_decision(decision, similar_memories)
        except json.JSONDecodeError:
            pass

        # Strategy 3: 提取```json块
        try:
            extracted = self._extract_json_block(response)
            decision = json.loads(extracted)
            return self._normalize_decision(decision, similar_memories)
        except (json.JSONDecodeError, Exception):
            pass

        # Strategy 4: 修复常见JSON错误后重试
        try:
            fixed = self._fix_json_string(response)
            decision = json.loads(fixed)
            return self._normalize_decision(decision, similar_memories)
        except (json.JSONDecodeError, Exception):
            pass

        # Strategy 5: 从文本中提取action关键字
        return self._fallback_extract_action(response, similar_memories)

    def _fix_json_string(self, text: str) -> str:
        """Fix common JSON formatting errors from small LLMs."""
        import re

        # 提取第一个{...}块
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

        json_str = text[start:end] if end > start else text

        # 修复常见错误
        # 1. 单引号 -> 双引号
        json_str = re.sub(r"'([^']*)'", r'"\1"', json_str)
        # 2. 无引号的key -> 加引号
        json_str = re.sub(r"(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str)
        # 3. 移除尾部逗号
        return re.sub(r",\s*([}\]])", r"\1", json_str)

    def _fallback_extract_action(
        self, response: Any, similar_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Fallback: extract action keyword from text when JSON parsing fails."""

        text = str(response).upper()

        # 提取有效ID列表
        valid_ids = []
        for m in similar_memories:
            mid = m.get("id")
            if mid is not None:
                if isinstance(mid, (dict, list)):
                    mid = str(mid)
                valid_ids.append(str(mid))

        # 按优先级检测action关键字
        if (
            "NOOP" in text
            or "NO_OP" in text
            or "NO-OP" in text
            or "NO CHANGE" in text
            or "DUPLICATE" in text
        ):
            return {"action": "NOOP", "to_delete": [], "reason": "detected_from_text"}

        if "DELETE" in text:
            # 尝试提取要删除的ID
            to_delete = [vid for vid in valid_ids if vid in str(response)]
            return {"action": "DELETE", "to_delete": to_delete, "reason": "detected_from_text"}

        if "UPDATE" in text:
            to_delete = [vid for vid in valid_ids if vid in str(response)]
            return {"action": "UPDATE", "to_delete": to_delete, "reason": "detected_from_text"}

        # 默认策略：保守地ADD（保留新记忆）
        # 理由：删除有用信息的代价 > 保留重复信息的代价
        # 相似 ≠ 重复，不能仅凭检索到相似记忆就删除新记忆
        return {"action": "ADD", "to_delete": [], "reason": "default_add_conservative"}

    def _normalize_decision(
        self, decision: dict[str, Any], similar_memories: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Normalize and validate decision dict."""
        # Validate action
        action = decision.get("action", "").upper()
        if action not in self.AVAILABLE_ACTIONS:
            # 尝试从event字段获取（兼容mem0格式）
            action = decision.get("event", "").upper()
        if action not in self.AVAILABLE_ACTIONS:
            action = "ADD"
        decision["action"] = action

        # Normalize to_delete field
        if "to_delete" in decision and isinstance(decision["to_delete"], list):
            pass
        elif decision.get("target_id"):
            decision["to_delete"] = [decision["target_id"]]
        elif decision.get("id") and action in ["UPDATE", "DELETE"]:
            decision["to_delete"] = [decision["id"]]
        else:
            decision["to_delete"] = []

        # Validate IDs against similar memories
        valid_ids = set()
        for m in similar_memories:
            mid = m.get("id")
            if mid is not None:
                if isinstance(mid, (dict, list)):
                    mid = str(mid)
                valid_ids.add(str(mid))

        normalized_to_delete = [
            tid for tid in decision["to_delete"] if tid and str(tid).strip() in valid_ids
        ]
        decision["to_delete"] = normalized_to_delete

        # 如果UPDATE/DELETE但没有有效的to_delete，改为NOOP
        if decision["action"] in ["UPDATE", "DELETE"] and not decision["to_delete"]:
            decision["action"] = "NOOP"

        return decision

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
