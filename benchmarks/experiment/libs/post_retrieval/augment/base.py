"""Augment Action - 结果增强

使用场景: MemoryBank, MemoryOS

功能: 在检索结果中添加额外的上下文信息（如 persona, traits, summary 等）
"""

from typing import Any

from ..base import BasePostRetrievalAction, PostRetrievalInput, PostRetrievalOutput


class AugmentAction(BasePostRetrievalAction):
    """结果增强策略

    在检索结果前后添加额外的上下文信息，如：
    - persona: 用户个性化信息
    - traits: 用户特征
    - summary: 记忆摘要
    - metadata: 元数据信息
    """

    def _init_action(self) -> None:
        """初始化配置"""
        self.augment_type = self.config.get("augment_type", "persona")
        self.position = self.config.get("position", "before")  # before, after, both
        self.separator = self.config.get("separator", "\n\n---\n\n")

    def execute(
        self,
        input_data: PostRetrievalInput,
        service: Any,
        llm: Any | None = None,
    ) -> PostRetrievalOutput:
        """增强检索结果

        Args:
            input_data: 输入数据
            service: 记忆服务代理（用于获取 persona 等信息）
            llm: LLM 生成器（未使用）

        Returns:
            PostRetrievalOutput: 增强后的结果
        """
        memory_data = input_data.data.get("memory_data", [])
        items = self._convert_to_items(memory_data)

        if not items:
            return PostRetrievalOutput(memory_items=items, metadata={"action": "augment"})

        # 获取增强内容
        augment_content = self._get_augment_content(input_data, service)

        if not augment_content:
            # 如果没有增强内容，返回原始结果
            return PostRetrievalOutput(
                memory_items=items,
                metadata={"action": "augment", "warning": "No augment content available"},
            )

        # 根据位置添加增强内容
        if self.position == "before":
            # 在第一个条目前添加
            if items:
                items[0].text = augment_content + self.separator + items[0].text
        elif self.position == "after":
            # 在最后一个条目后添加
            if items:
                items[-1].text = items[-1].text + self.separator + augment_content
        elif self.position == "both" and items:
            # 前后都添加
            items[0].text = augment_content + self.separator + items[0].text
            items[-1].text = items[-1].text + self.separator + augment_content

        return PostRetrievalOutput(
            memory_items=items,
            metadata={
                "action": "augment",
                "augment_type": self.augment_type,
                "position": self.position,
            },
        )

    def _get_augment_content(self, input_data: PostRetrievalInput, service: Any | None) -> str:
        """获取增强内容

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            增强内容文本
        """
        if self.augment_type == "persona":
            return self._get_persona(input_data, service)
        if self.augment_type == "traits":
            return self._get_traits(input_data, service)
        if self.augment_type == "summary":
            return self._get_summary(input_data, service)
        if self.augment_type == "metadata":
            return self._get_metadata(input_data)
        return ""

    def _get_persona(self, input_data: PostRetrievalInput, service: Any | None) -> str:
        """获取 persona 信息

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            Persona 文本
        """
        # 注意：service 在这里可能是 None（从 memory_data 提取）或 _ServiceProxy
        try:
            # 从已检索的记忆中提取实体和关键信息
            memory_data = input_data.data.get("memory_data", [])
            if not memory_data:
                return ""

            # 提取所有记忆文本中的实体和主题
            entities = set()
            topics = set()
            relations = []

            for item in memory_data[:5]:  # 只看前5条最相关的记忆
                # 支持 content 和 text 字段
                content = item.get("content") or item.get("text", "")
                metadata = item.get("metadata", {})

                # 从三元组中提取实体（如果有）
                if "subject" in metadata and metadata["subject"]:
                    entities.add(str(metadata["subject"]))
                if "object" in metadata and metadata["object"]:
                    entities.add(str(metadata["object"]))
                if "predicate" in metadata and metadata["predicate"]:
                    relations.append(str(metadata["predicate"]))

                # 从内容中提取可能的主题关键词（简化版）
                # 实际应用中可以用 NER 或关键词提取
                if content:
                    words = content.split()
                    for word in words:
                        # 简单启发式：长且首字母大写的词
                        cleaned = word.strip(".,!?;:()")
                        if len(cleaned) > 3 and cleaned[0].isupper() and cleaned.isalpha():
                            topics.add(cleaned)

            # 构建 persona 摘要
            persona_parts = []
            if entities:
                entity_list = sorted(entities)[:5]  # 最多5个
                persona_parts.append(f"Key Entities: {', '.join(entity_list)}")
            if relations:
                # 统计最常见的关系
                from collections import Counter

                common_relations = [r for r, _ in Counter(relations).most_common(3)]
                if common_relations:
                    persona_parts.append(f"Common Relations: {', '.join(common_relations)}")
            if topics:
                topic_list = sorted(topics)[:5]  # 最多5个
                persona_parts.append(f"Topics: {', '.join(topic_list)}")

            if persona_parts:
                return "=== Context Summary ===\n" + "\n".join(persona_parts)

            return ""
        except Exception:  # noqa: BLE001
            # 调试：打印错误信息
            # print(f"[DEBUG] _get_persona error: {e}")
            return ""

    def _get_traits(self, input_data: PostRetrievalInput, service: Any | None) -> str:
        """获取 traits 信息

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            Traits 文本
        """
        try:
            # 从已检索的记忆中提取用户特征信息
            memory_data = input_data.data.get("memory_data", [])
            if not memory_data:
                return ""

            traits = set()
            preferences = set()
            behaviors = set()

            # 从记忆的 metadata 中提取 traits 相关字段
            for item in memory_data[:10]:  # 分析前10条记忆
                metadata = item.get("metadata", {})

                # 1. 直接从 metadata 提取 traits 字段
                if "traits" in metadata and metadata["traits"]:
                    if isinstance(metadata["traits"], list):
                        traits.update(str(t) for t in metadata["traits"])
                    else:
                        traits.add(str(metadata["traits"]))

                # 2. 提取用户偏好信息
                if "preference" in metadata and metadata["preference"]:
                    preferences.add(str(metadata["preference"]))
                elif "tag" in metadata and metadata["tag"]:
                    # 标签也可能包含偏好信息
                    if isinstance(metadata["tag"], list):
                        preferences.update(
                            str(t)
                            for t in metadata["tag"]
                            if "like" in str(t).lower() or "prefer" in str(t).lower()
                        )
                    else:
                        tag_str = str(metadata["tag"])
                        if "like" in tag_str.lower() or "prefer" in tag_str.lower():
                            preferences.add(tag_str)

                # 3. 从记忆内容中提取行为模式关键词
                content = item.get("content") or item.get("text", "")
                if content:
                    # 常见的行为模式词
                    behavior_keywords = [
                        "often",
                        "always",
                        "usually",
                        "frequently",
                        "tends to",
                        "习惯",
                        "经常",
                        "总是",
                        "通常",
                    ]
                    content_lower = content.lower()
                    for keyword in behavior_keywords:
                        if keyword in content_lower:
                            # 提取包含该关键词的短语（简化版）
                            words = content.split()
                            for i, word in enumerate(words):
                                if keyword in word.lower() and i < len(words) - 1:
                                    # 提取后续2-3个词作为行为描述
                                    behavior_phrase = " ".join(words[i : min(i + 3, len(words))])
                                    if len(behavior_phrase) < 50:  # 避免过长
                                        behaviors.add(behavior_phrase)
                                    break

            # 构建 traits 摘要
            trait_parts = []
            if traits:
                trait_list = sorted(traits)[:5]  # 最多5个
                trait_parts.append(f"User Traits: {', '.join(trait_list)}")
            if preferences:
                pref_list = sorted(preferences)[:5]  # 最多5个
                trait_parts.append(f"Preferences: {', '.join(pref_list)}")
            if behaviors:
                behavior_list = sorted(behaviors)[:3]  # 最多3个
                trait_parts.append(f"Behaviors: {', '.join(behavior_list)}")

            if trait_parts:
                return "=== User Traits ===\n" + "\n".join(trait_parts)

            return ""
        except Exception:  # noqa: BLE001
            # 调试：打印错误信息
            # print(f"[DEBUG] _get_traits error: {e}")
            return ""

    def _get_summary(self, input_data: PostRetrievalInput, service: Any | None) -> str:
        """获取记忆摘要

        Args:
            input_data: 输入数据
            service: 记忆服务

        Returns:
            摘要文本
        """
        try:
            # 从已检索的记忆中生成简要摘要
            memory_data = input_data.data.get("memory_data", [])
            if not memory_data:
                return ""

            total_items = len(memory_data)

            # 统计不同 tier 的记忆数量
            tier_counts = {}
            for item in memory_data:
                metadata = item.get("metadata", {})
                tier = metadata.get("tier", "unknown")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

            summary_parts = [
                "=== Memory Summary ===",
                f"Total memories retrieved: {total_items}",
            ]

            # 添加分层统计
            if tier_counts:
                tier_info = []
                for tier in sorted(tier_counts.keys(), key=lambda x: (x != 0, x)):
                    count = tier_counts[tier]
                    if tier == 0:
                        tier_info.append(f"Recent (tier 0): {count}")
                    elif tier == "unknown":
                        tier_info.append(f"Unknown tier: {count}")
                    else:
                        tier_info.append(f"Tier {tier}: {count}")

                if tier_info:
                    summary_parts.extend(tier_info)

            return "\n".join(summary_parts)
        except Exception:  # noqa: BLE001
            # 调试：打印错误
            # print(f"[DEBUG] _get_summary error: {e}")
            return ""

    def _get_metadata(self, input_data: PostRetrievalInput) -> str:
        """从 data 获取元数据信息

        Args:
            input_data: 输入数据

        Returns:
            元数据文本
        """
        metadata = input_data.data.get("metadata", {})
        if not metadata:
            return ""

        # 格式化元数据
        lines = ["=== Metadata ==="]
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")

        return "\n".join(lines)
