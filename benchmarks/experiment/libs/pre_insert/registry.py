"""PreInsert Action 注册表

职责/Responsibilities:
- 统一管理 PreInsert 阶段的算子(Action)注册与获取
- 确立「规范名称」与「兼容别名」策略，避免命名漂移

规范命名（Canonical Names）:
 - none
 - enrich.keyword
 - enrich.summarize
 - enrich.segment_compress
 - enrich.entity
 - rewrite.fact_extract
 - rewrite.triplet_extract

兼容别名（Aliases）保持向后兼容，例如：
- enrichment.* / decomposition.* / rewrite.* / tri_embed / none.pass

注意：为兼容历史配置，保留 transform.* / extract.* / enrichment.* / decomposition.* 等别名。
"""

from .base import BasePreInsertAction
from .enrich import (
    EntityExtractAction,
    KeywordExtractAction,
    SegmentDenoiseAction,
    SummarizeAction,
)
from .none_action import NoneAction
from .rewrite import (
    FactExtractAction,
    TripleExtractAction,
)


class PreInsertActionRegistry:
    """PreInsert Action 注册表

    使用策略模式管理所有 Action，支持动态注册和获取。
    """

    _actions: dict[str, type[BasePreInsertAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePreInsertAction]) -> None:
        """注册一个 Action

        Args:
            name: Action 名称（支持点分隔的层级名，如 "decomposition.entity"）
            action_class: Action 类
        """
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePreInsertAction]:
        """获取 Action 类

        Args:
            name: Action 名称

        Returns:
            Action 类

        Raises:
            ValueError: 如果 Action 未注册
        """
        if name not in cls._actions:
            raise ValueError(
                f"Unknown PreInsert action: '{name}'. "
                f"Available actions: {list(cls._actions.keys())}"
            )
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """列出所有已注册的 Action

        Returns:
            Action 名称列表
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查 Action 是否已注册

        Args:
            name: Action 名称

        Returns:
            是否已注册
        """
        return name in cls._actions


def _register_builtin_actions():
    """注册所有内置 Action

    先注册规范名称（canonical），再补充兼容别名（aliases）。
    """
    # 1) 规范名称（canonical）—— none/enrich/rewrite 三类
    PreInsertActionRegistry.register("none", NoneAction)
    PreInsertActionRegistry.register("enrich.keyword", KeywordExtractAction)
    PreInsertActionRegistry.register("enrich.summarize", SummarizeAction)
    PreInsertActionRegistry.register("enrich.segment_compress", SegmentDenoiseAction)
    PreInsertActionRegistry.register("enrich.entity", EntityExtractAction)
    PreInsertActionRegistry.register("rewrite.fact_extract", FactExtractAction)
    PreInsertActionRegistry.register("rewrite.triplet_extract", TripleExtractAction)

    # 2) 兼容别名（aliases）—— 保留历史/替代命名以免配置失效
    # 旧/替代：none.*
    PreInsertActionRegistry.register("none.pass", NoneAction)
    PreInsertActionRegistry.register("none.noop", NoneAction)

    # 旧命名空间：enrichment/decomposition（保持兼容）
    PreInsertActionRegistry.register("enrichment.keyword", KeywordExtractAction)
    PreInsertActionRegistry.register("enrichment.summarize", SummarizeAction)
    PreInsertActionRegistry.register("decomposition.entity", EntityExtractAction)
    PreInsertActionRegistry.register("decomposition.fact", FactExtractAction)
    PreInsertActionRegistry.register("decomposition.triple", TripleExtractAction)
    PreInsertActionRegistry.register("decomposition.segment_denoise", SegmentDenoiseAction)

    # 历史 transform/extract 命名（保持兼容）
    PreInsertActionRegistry.register("transform.segment_compress", SegmentDenoiseAction)
    PreInsertActionRegistry.register("transform.segment_denoise", SegmentDenoiseAction)
    # 旧 enrich 名保持兼容
    PreInsertActionRegistry.register("enrich.segment_denoise", SegmentDenoiseAction)
    PreInsertActionRegistry.register("transform.summarize", SummarizeAction)
    PreInsertActionRegistry.register("extract.keyword", KeywordExtractAction)
    PreInsertActionRegistry.register("extract.entity", EntityExtractAction)
    PreInsertActionRegistry.register("extract.fact", FactExtractAction)
    PreInsertActionRegistry.register("extract.triple", TripleExtractAction)
    # 历史 rewrite 名保持兼容
    PreInsertActionRegistry.register("rewrite.fact", FactExtractAction)
    PreInsertActionRegistry.register("rewrite.triple", TripleExtractAction)

    # 额外别名
    PreInsertActionRegistry.register("enrich.segment_compress", SegmentDenoiseAction)

    # 额外别名：更贴近语义的命名（不改类名，仅作为注册别名）
    # - KeywordExtractAction 也可理解为 Note 抽取
    PreInsertActionRegistry.register("extract.note", KeywordExtractAction)

    # 历史遗留别名
    PreInsertActionRegistry.register("tri_embed", TripleExtractAction)


# 自动注册所有内置 Action
_register_builtin_actions()
