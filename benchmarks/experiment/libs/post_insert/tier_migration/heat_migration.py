"""
Heat Migration Action - MemoryOS Layer Migration
=================================================

Papers: MemoryOS
Strategy Type: tier_migration
Trigger Mechanism: threshold (heat-based) + hybrid (capacity + heat)

Implements heat-based memory migration across layers:
- STM → MTM: Multi-summary generation on FIFO overflow
- MTM → LPM: Profile/Knowledge extraction when Heat ≥ threshold
"""

from typing import Any

from ..base import BasePostInsertAction, PostInsertInput, PostInsertOutput


class HeatMigrationAction(BasePostInsertAction):
    """Heat-based layer migration action for hierarchical memory systems.

    Implementation logic (MemoryOS Algorithm 1 & 2):
    1. STM→MTM: FIFO overflow triggers multi-summary generation
    2. MTM→LPM: Heat threshold triggers profile/knowledge extraction

    Config Parameters:
        migrate_policy (str): Migration policy (default: "heat")
        heat_threshold (float): Heat threshold for MTM→LPM (default: 5.0)
        stm_capacity (int): STM capacity for overflow detection (default: 20)
        upgrade_transform (str): "multi_summary" or "none" (default: "none")
        enable_profile_extraction (bool): Extract user profile (default: True)
        enable_knowledge_extraction (bool): Extract knowledge (default: True)
        reset_heat_after_extraction (bool): Reset heat after extraction (default: True)
    """

    STRATEGY_TYPE = "tier_migration"
    TRIGGER_MECHANISM = "threshold"
    AVAILABLE_ACTIONS = ["MIGRATE", "EXTRACT", "NOOP"]

    def _init_action(self) -> None:
        """Initialize heat migration action configuration."""
        self.migrate_policy = self._get_config("migrate_policy", "heat")
        self.heat_threshold = self._get_config("heat_threshold", 5.0)
        self.stm_capacity = self._get_config("stm_capacity", 20)
        self.upgrade_transform = self._get_config("upgrade_transform", "none")
        self.enable_profile_extraction = self._get_config("enable_profile_extraction", True)
        self.enable_knowledge_extraction = self._get_config("enable_knowledge_extraction", True)
        self.reset_heat_after_extraction = self._get_config("reset_heat_after_extraction", True)

    def execute(
        self,
        input_data: PostInsertInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostInsertOutput:
        """Execute heat-based layer migration action.

        Args:
            input_data: Input data with newly inserted memories
            service: HierarchicalMemoryService (must support MemoryOS methods)
            llm: LLM client for multi-summary and profile extraction

        Returns:
            PostInsertOutput with migration statistics
        """
        # Check if service supports MemoryOS methods
        if not hasattr(service, "_migrate_stm_to_mtm_batch"):
            return PostInsertOutput(
                success=False,
                action="heat_migration",
                details={
                    "error": "Service does not support MemoryOS migration (missing _migrate_stm_to_mtm_batch)"
                },
            )

        try:
            total_migrated = 0
            details = {}

            # ===== Step 1: STM→MTM Migration (Algorithm 1) =====
            stm_count = getattr(service, "_tier_counts", {}).get("stm", 0)

            if stm_count > self.stm_capacity:
                overflow_count = stm_count - self.stm_capacity

                stm_config = {
                    "enable_multi_summary": self.upgrade_transform == "multi_summary",
                    "llm_generator": llm,
                }

                migrated_stm = service._migrate_stm_to_mtm_batch(
                    count=overflow_count, config=stm_config
                )

                total_migrated += migrated_stm
                details["stm_to_mtm"] = {
                    "count": migrated_stm,
                    "multi_summary_enabled": self.upgrade_transform == "multi_summary",
                }

            # ===== Step 2: MTM→LPM Profile Extraction (Algorithm 2) =====
            if self.enable_profile_extraction or self.enable_knowledge_extraction:
                if not hasattr(service, "analyze_mtm_sessions_for_long_term"):
                    details["mtm_to_lpm"] = {
                        "error": "Service missing analyze_mtm_sessions_for_long_term method"
                    }
                else:
                    mtm_config = {
                        "llm_generator": llm,
                        "enable_heat_analysis": True,
                        "heat_threshold": self.heat_threshold,
                        "user_id": input_data.data.get("user_id", "default"),
                    }

                    extracted_count = service.analyze_mtm_sessions_for_long_term(config=mtm_config)

                    details["mtm_to_lpm"] = {
                        "extracted_sessions": extracted_count,
                        "heat_threshold": self.heat_threshold,
                        "profile_extraction_enabled": self.enable_profile_extraction,
                        "knowledge_extraction_enabled": self.enable_knowledge_extraction,
                    }

            return PostInsertOutput(
                success=True,
                action="heat_migration",
                details={
                    "strategy_type": self.STRATEGY_TYPE,
                    "trigger_mechanism": self.TRIGGER_MECHANISM,
                    "total_migrated": total_migrated,
                    "policy": self.migrate_policy,
                    **details,
                },
            )

        except Exception as e:
            import traceback

            return PostInsertOutput(
                success=False,
                action="heat_migration",
                details={"error": str(e), "traceback": traceback.format_exc()},
            )
