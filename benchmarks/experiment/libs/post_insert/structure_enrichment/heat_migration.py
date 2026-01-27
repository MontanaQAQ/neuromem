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
            service: Memory service (must support retrieve/update operations)
            llm: LLM client for multi-summary and profile extraction

        Returns:
            PostInsertOutput with migration statistics
        """
        try:
            total_migrated = 0
            details = {}

            # ===== Step 1: STM→MTM Migration (Algorithm 1) =====
            stm_migrated = self._migrate_stm_to_mtm(service, llm)
            total_migrated += stm_migrated

            if stm_migrated > 0:
                details["stm_to_mtm"] = {
                    "count": stm_migrated,
                    "multi_summary_enabled": self.upgrade_transform == "multi_summary",
                }

            # ===== Step 2: MTM→LPM Profile Extraction (Algorithm 2) =====
            if self.enable_profile_extraction or self.enable_knowledge_extraction:
                extracted = self._extract_mtm_to_lpm(service, llm)

                if extracted > 0:
                    details["mtm_to_lpm"] = {
                        "extracted_sessions": extracted,
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

    def _migrate_stm_to_mtm(self, service: Any, llm: Any | None) -> int:
        """Migrate overflow memories from STM to MTM.

        Args:
            service: Memory service
            llm: LLM for multi-summary generation

        Returns:
            Number of memories migrated
        """
        try:
            # 检索所有 tier=0 (STM) 的记忆
            stm_memories = self._get_tier_memories(service, tier=0)

            if len(stm_memories) <= self.stm_capacity:
                return 0  # 未溢出，无需迁移

            # 计算需要迁移的数量
            overflow_count = len(stm_memories) - self.stm_capacity

            # 按时间戳排序，迁移最旧的记忆（FIFO）
            sorted_memories = sorted(
                stm_memories, key=lambda x: x.get("metadata", {}).get("timestamp", 0)
            )

            to_migrate = sorted_memories[:overflow_count]
            migrated_count = 0

            for memory in to_migrate:
                try:
                    memory_id = memory.get("id")
                    if not memory_id:
                        continue

                    # 更新 tier 到 1 (MTM)
                    metadata = memory.get("metadata", {}).copy()
                    metadata["tier"] = 1
                    metadata["migrated_from_stm"] = True

                    # 如果启用 multi_summary，生成摘要
                    if self.upgrade_transform == "multi_summary" and llm:
                        summary = self._generate_multi_summary(memory, llm)
                        if summary:
                            metadata["multi_summary"] = summary

                    # 更新记忆
                    success = service.update(entry_id=memory_id, metadata=metadata)
                    if success:
                        migrated_count += 1

                except Exception as e:
                    print(f"[WARN heat_migration] Failed to migrate {memory.get('id')}: {e}")
                    continue

            return migrated_count

        except Exception as e:
            print(f"[ERROR heat_migration] STM→MTM migration failed: {e}")
            return 0

    def _extract_mtm_to_lpm(self, service: Any, llm: Any | None) -> int:
        """Extract high-heat MTM sessions to LPM.

        Args:
            service: Memory service
            llm: LLM for profile/knowledge extraction

        Returns:
            Number of sessions extracted
        """
        try:
            # 检索所有 tier=1 (MTM) 的记忆
            mtm_memories = self._get_tier_memories(service, tier=1)

            if not mtm_memories or not llm:
                return 0

            # 筛选 heat >= threshold 的记忆
            high_heat_memories = [
                m
                for m in mtm_memories
                if m.get("metadata", {}).get("heat", 0) >= self.heat_threshold
            ]

            if not high_heat_memories:
                return 0

            extracted_count = 0

            for memory in high_heat_memories:
                try:
                    memory_id = memory.get("id")
                    if not memory_id:
                        continue

                    metadata = memory.get("metadata", {}).copy()

                    # 提取 profile 和 knowledge
                    if self.enable_profile_extraction:
                        profile = self._extract_profile(memory, llm)
                        if profile:
                            metadata["extracted_profile"] = profile

                    if self.enable_knowledge_extraction:
                        knowledge = self._extract_knowledge(memory, llm)
                        if knowledge:
                            metadata["extracted_knowledge"] = knowledge

                    # 更新 tier 到 2 (LPM)
                    metadata["tier"] = 2
                    metadata["migrated_from_mtm"] = True

                    # 重置 heat（如果配置了）
                    if self.reset_heat_after_extraction:
                        metadata["heat"] = 0

                    # 更新记忆
                    success = service.update(entry_id=memory_id, metadata=metadata)
                    if success:
                        extracted_count += 1

                except Exception as e:
                    print(f"[WARN heat_migration] Failed to extract {memory.get('id')}: {e}")
                    continue

            return extracted_count

        except Exception as e:
            print(f"[ERROR heat_migration] MTM→LPM extraction failed: {e}")
            return 0

    def _get_tier_memories(self, service: Any, tier: int) -> list[dict[str, Any]]:
        """Retrieve all memories from a specific tier.

        Args:
            service: Memory service
            tier: Tier number (0=STM, 1=MTM, 2=LPM)

        Returns:
            List of memory dictionaries
        """
        try:
            # 尝试直接检索该 tier 的所有记忆
            # 注意：这里使用一个大的 top_k 来获取所有记忆
            # 实际应用中可能需要服务层提供专门的 get_by_tier 方法
            all_results = service.retrieve(top_k=10000)  # 大数值获取所有

            # 过滤出指定 tier 的记忆
            return [r for r in all_results if r.get("metadata", {}).get("tier") == tier]

        except Exception as e:
            print(f"[WARN heat_migration] Failed to get tier {tier} memories: {e}")
            return []

    def _generate_multi_summary(self, memory: dict[str, Any], llm: Any) -> str:
        """Generate multi-perspective summary for STM→MTM migration.

        Args:
            memory: Memory dictionary
            llm: LLM client

        Returns:
            Generated summary
        """
        try:
            content = memory.get("text") or memory.get("content", "")

            prompt = f"""Generate a concise multi-perspective summary of the following memory:

Memory: {content}

Provide a summary that captures:
1. Main topic/theme
2. Key entities mentioned
3. Important facts or events

Summary (3-5 sentences):"""

            summary = llm.generate(prompt)
            return summary.strip()

        except Exception:
            return ""

    def _extract_profile(self, memory: dict[str, Any], llm: Any) -> str:
        """Extract user profile from high-heat memory.

        Args:
            memory: Memory dictionary
            llm: LLM client

        Returns:
            Extracted profile
        """
        try:
            content = memory.get("text") or memory.get("content", "")

            prompt = f"""Extract user profile information from the following memory:

Memory: {content}

Identify:
- User preferences
- User habits
- User characteristics
- Recurring patterns

Profile (brief):"""

            profile = llm.generate(prompt)
            return profile.strip()

        except Exception:
            return ""

    def _extract_knowledge(self, memory: dict[str, Any], llm: Any) -> str:
        """Extract factual knowledge from high-heat memory.

        Args:
            memory: Memory dictionary
            llm: LLM client

        Returns:
            Extracted knowledge
        """
        try:
            content = memory.get("text") or memory.get("content", "")

            prompt = f"""Extract factual knowledge from the following memory:

Memory: {content}

Identify:
- Facts and information
- Relationships between entities
- Important concepts

Knowledge (brief):"""

            knowledge = llm.generate(prompt)
            return knowledge.strip()

        except Exception:
            return ""
