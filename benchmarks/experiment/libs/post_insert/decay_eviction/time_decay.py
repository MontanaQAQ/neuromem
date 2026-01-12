"""
Time Decay Action - Time-based Memory Eviction
===============================================

Papers: LD-Agent
Strategy Type: decay_eviction
Trigger Mechanism: temporal (time-based)

Evicts memories based on time since creation/access.
Simpler than forgetting curve, pure time-based decay.
"""

import time
from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class TimeDecayAction(BasePostInsertAction):
    """Time-based memory decay action.

    Implementation logic (based on LD-Agent):
    1. Check time since last access for each memory
    2. Evict memories older than max_age threshold
    3. Optionally weight by importance score

    Config Parameters:
        max_age_hours (float): Maximum age in hours before eviction (default: 24.0)
        importance_weight (bool): Weight decay by importance score (default: False)
        only_on_session_end (bool): Execute only at session end (default: True)
    """

    STRATEGY_TYPE = "decay_eviction"
    TRIGGER_MECHANISM = "temporal"
    AVAILABLE_ACTIONS = ["DELETE", "NOOP"]

    def _init_action(self) -> None:
        """Initialize time decay action configuration."""
        self.max_age_hours = self._get_config("max_age_hours", 24.0)
        self.importance_weight = self._get_config("importance_weight", False)
        self.only_on_session_end = self._get_config("only_on_session_end", True)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute time decay action.

        Args:
            input_data: Input data with session context
            service: Memory service
            llm: LLM client (unused)

        Returns:
            PostInsertOutput with eviction statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="time_decay",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                    "message": "Time decay only runs at session end",
                },
            )

        try:
            # Get all memories
            all_memories = self._get_all_memories(service)
            current_time = time.time()
            max_age_seconds = self.max_age_hours * 3600.0

            evicted_count = 0
            remaining_count = 0

            for memory in all_memories:
                age = self._get_memory_age(memory, current_time)

                # Apply importance weighting if enabled
                effective_max_age = max_age_seconds
                if self.importance_weight:
                    importance = memory.get("metadata", {}).get("importance", 1.0)
                    effective_max_age *= importance

                if age > effective_max_age:
                    try:
                        service.delete(memory.get("id"))
                        evicted_count += 1
                    except Exception:
                        pass
                else:
                    remaining_count += 1

            return PostInsertOutput(
                success=True,
                action="time_decay",
                details={
                    "strategy_type": self.STRATEGY_TYPE,
                    "trigger_mechanism": self.TRIGGER_MECHANISM,
                    "evicted_count": evicted_count,
                    "remaining_count": remaining_count,
                    "max_age_hours": self.max_age_hours,
                },
            )

        except Exception as e:
            return PostInsertOutput(
                success=False,
                action="time_decay",
                details={"error": str(e)},
            )

    def _get_all_memories(self, service: Any) -> list[dict[str, Any]]:
        """Get all memories from service."""
        if hasattr(service, "get_all"):
            return service.get_all()
        if hasattr(service, "retrieve"):
            return service.retrieve(query="", top_k=10000)
        return []

    def _get_memory_age(self, memory: dict[str, Any], current_time: float) -> float:
        """Get age of memory in seconds."""
        metadata = memory.get("metadata", {})

        # Try last_access first, then created_at
        timestamp = metadata.get("last_access", metadata.get("created_at"))

        if timestamp is None:
            return 0.0

        if isinstance(timestamp, str):
            try:
                from datetime import datetime

                timestamp = datetime.fromisoformat(timestamp).timestamp()
            except Exception:
                return 0.0

        return current_time - timestamp
