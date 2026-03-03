# PreRetrieval Action 注册表

from .base import BasePreRetrievalAction
from .embedding import EmbeddingAction
from .enhancement.decompose import DecomposeAction
from .enhancement.multi_embed import MultiEmbedAction
from .enhancement.route import RouteAction
from .none_action import NoneAction
from .optimize.expand import ExpandAction
from .optimize.keyword_extract import KeywordExtractAction
from .optimize.rewrite import RewriteAction
from .validate import ValidateAction


class PreRetrievalActionRegistry:
    """PreRetrieval Action 注册表

    提供Action的注册、获取和查询功能。
    """

    _actions: dict[str, type[BasePreRetrievalAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePreRetrievalAction]) -> None:
        """注册Action

        Args:
            name: Action名称（支持点号分隔的子类型，如 "optimize.keyword_extract"）
            action_class: Action类

        Raises:
            ValueError: Action名称已存在
        """
        if name in cls._actions:
            raise ValueError(f"Action '{name}' is already registered")
        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePreRetrievalAction]:
        """获取Action类

        Args:
            name: Action名称

        Returns:
            Action类

        Raises:
            ValueError: Action不存在
        """
        if name not in cls._actions:
            raise ValueError(
                f"Unknown action: {name}. Available actions: {', '.join(cls._actions.keys())}"
            )
        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """列出所有已注册的Action名称

        Returns:
            Action名称列表
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """检查Action是否已注册

        Args:
            name: Action名称

        Returns:
            是否已注册
        """
        return name in cls._actions


# ==================== 注册所有Action ====================

# 基础Actions
PreRetrievalActionRegistry.register("none", NoneAction)
PreRetrievalActionRegistry.register("embedding", EmbeddingAction)
PreRetrievalActionRegistry.register("validate", ValidateAction)

# Optimize子类型Actions
PreRetrievalActionRegistry.register("optimize.keyword_extract", KeywordExtractAction)
PreRetrievalActionRegistry.register("optimize.expand", ExpandAction)
PreRetrievalActionRegistry.register("optimize.rewrite", RewriteAction)

# Enhancement子类型Actions（查询增强）
PreRetrievalActionRegistry.register("enhancement.decompose", DecomposeAction)
PreRetrievalActionRegistry.register("enhancement.route", RouteAction)
PreRetrievalActionRegistry.register("enhancement.multi_embed", MultiEmbedAction)
