"""
Forgetting Curve Action - Ebbinghaus-based Memory Decay
========================================================

Papers: MemoryBank
Strategy Type: decay_eviction
Trigger Mechanism: temporal (time-based) + threshold (score-based)

Implements Ebbinghaus forgetting curve to decay memory strength over time.
Memories below threshold are evicted.
"""

import math
import time
from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class ForgettingCurveAction(BasePostInsertAction):
    """Ebbinghaus forgetting curve action for memory decay.

    Implementation logic (based on MemoryBank):
    1. Calculate memory strength using Ebbinghaus formula: R = e^(-t/S)
    2. Memories with strength below threshold are forgotten
    3. Access count affects stability parameter S

    Config Parameters:
        forget_threshold (float): Strength threshold below which memories are forgotten (default: 0.1)
        stability_base (float): Base stability parameter (default: 1.0)
        stability_growth (float): Stability growth per access (default: 0.5)
        only_on_session_end (bool): Execute only at session end (default: True)
    """

    STRATEGY_TYPE = "decay_eviction"
    TRIGGER_MECHANISM = "temporal"
    AVAILABLE_ACTIONS = ["DELETE", "NOOP"]

    def _init_action(self) -> None:
        """Initialize forgetting curve action configuration."""
        self.forget_threshold = self._get_config("forget_threshold", 0.1)
        self.stability_base = self._get_config("stability_base", 1.0)
        self.stability_growth = self._get_config("stability_growth", 0.5)
        self.only_on_session_end = self._get_config("only_on_session_end", True)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute forgetting curve action.

        Args:
            input_data: Input data with session context
            service: Memory service (must support metadata operations)
            llm: LLM client (unused)

        Returns:
            PostInsertOutput with forgetting statistics
        """
        # Check if we should execute
        if self.only_on_session_end and not input_data.is_session_end:
            return PostInsertOutput(
                success=True,
                action="forgetting_curve",
                details={
                    "skipped": True,
                    "reason": "not_session_end",
                    "message": "Forgetting only runs at session end",
                },
            )

        try:
            # Get all memories with metadata
            all_memories = self._get_all_memories(service)
            current_time = time.time()

            forgotten_count = 0
            remaining_count = 0

            for memory in all_memories:
                # Calculate memory strength
                strength = self._calculate_strength(memory, current_time)

                if strength < self.forget_threshold:
                    # Forget this memory
                    try:
                        service.delete(memory.get("id"))
                        forgotten_count += 1
                    except Exception:
                        pass
                else:
                    remaining_count += 1

            return PostInsertOutput(
                success=True,
                action="forgetting_curve",
                details={
                    "strategy_type": self.STRATEGY_TYPE,
                    "trigger_mechanism": self.TRIGGER_MECHANISM,
                    "forgotten_count": forgotten_count,
                    "remaining_count": remaining_count,
                    "threshold": self.forget_threshold,
                },
            )

        except Exception as e:
            return PostInsertOutput(
                success=False,
                action="forgetting_curve",
                details={"error": str(e)},
            )

    def _get_all_memories(self, service: Any) -> list[dict[str, Any]]:
        """Get all memories from service."""
        if hasattr(service, "get_all"):
            return service.get_all()
        if hasattr(service, "retrieve"):
            # Fallback: retrieve with high top_k
            return service.retrieve(query="", top_k=10000)
        return []

    def _calculate_strength(self, memory: dict[str, Any], current_time: float) -> float:
        """Calculate memory strength using Ebbinghaus formula.

        R = e^(-t/S) where:
        - t = time since last access
        - S = stability (increases with access count)
        """
        metadata = memory.get("metadata", {})

        # Get last access time
        last_access = metadata.get("last_access", metadata.get("created_at", current_time))
        if isinstance(last_access, str):
            try:
                from datetime import datetime

                last_access = datetime.fromisoformat(last_access).timestamp()
            except Exception:
                last_access = current_time

        # Get access count for stability
        access_count = metadata.get("access_count", 1)

        # Calculate stability: S = base + growth * access_count
        stability = self.stability_base + self.stability_growth * access_count

        # Time elapsed in hours
        time_elapsed = (current_time - last_access) / 3600.0

        # Ebbinghaus formula: R = e^(-t/S)
        return math.exp(-time_elapsed / stability)
