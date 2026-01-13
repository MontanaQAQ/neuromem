"""
PostInsert Action Registry
===========================

Central registry for all PostInsert action strategies.

Strategy Types:
- conflict_resolution: Mem0, Mem0ᵍ, TiM, MemGPT (LLM CRUD / semantic consolidation)
- decay_eviction: MemoryBank, LD-Agent (forgetting curve / time decay)
- structure_enrichment: A-Mem, HippoRAG, MemoryOS (link evolution / graph construction / heat migration)
"""

from .base import BasePostInsertAction

# New strategy-based imports
from .conflict_resolution import LLMCRUDAction, SemanticConsolidationAction
from .decay_eviction import ForgettingCurveAction, TimeDecayAction

# Legacy imports - REMOVED (code moved to backup_legacy_actions/ for archive only)
# Old action classes are no longer imported or registered
# Use new strategy-based actions: conflict_resolution.*, decay_eviction.*, structure_enrichment.*
# Keep NoneAction at top level (like other action modules)
from .none_action import NoneAction
from .structure_enrichment import GraphConstructionAction, HeatMigrationAction
from .structure_enrichment import LinkEvolutionAction as NewLinkEvolutionAction


class PostInsertActionRegistry:
    """Registry for PostInsert action strategies.

    This registry maintains a mapping from action names to action classes,
    enabling dynamic action selection based on configuration.

    Usage:
        >>> registry = PostInsertActionRegistry()
        >>> action_class = registry.get("distillation")
        >>> action = action_class(config)
    """

    _actions: dict[str, type[BasePostInsertAction]] = {}

    @classmethod
    def register(cls, name: str, action_class: type[BasePostInsertAction]) -> None:
        """Register an action class.

        Args:
            name: Action name (e.g., "none", "distillation")
            action_class: Action class (must inherit from BasePostInsertAction)

        Raises:
            ValueError: If action_class is not a subclass of BasePostInsertAction
        """
        if not issubclass(action_class, BasePostInsertAction):
            raise ValueError(
                f"Action class must inherit from BasePostInsertAction, got {action_class}"
            )

        cls._actions[name] = action_class

    @classmethod
    def get(cls, name: str) -> type[BasePostInsertAction]:
        """Get action class by name.

        Args:
            name: Action name

        Returns:
            Action class

        Raises:
            ValueError: If action name is not registered
        """
        if name not in cls._actions:
            available = ", ".join(cls._actions.keys())
            raise ValueError(f"Unknown action: {name}. Available actions: {available}")

        return cls._actions[name]

    @classmethod
    def list_actions(cls) -> list[str]:
        """List all registered action names.

        Returns:
            List of action names
        """
        return list(cls._actions.keys())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if an action is registered.

        Args:
            name: Action name

        Returns:
            True if registered, False otherwise
        """
        return name in cls._actions


# ========================= Register All Actions =========================

# [A] Passthrough - No post-processing
PostInsertActionRegistry.register("none", NoneAction)

# ========================= Strategy-Based Registration =========================

# [1] Conflict Resolution (Mem0, Mem0ᵍ, TiM, MemGPT)
PostInsertActionRegistry.register("conflict_resolution.llm_crud", LLMCRUDAction)
PostInsertActionRegistry.register(
    "conflict_resolution.semantic_consolidation", SemanticConsolidationAction
)

# [2] Decay Eviction (MemoryBank, LD-Agent)
PostInsertActionRegistry.register("decay_eviction.forgetting_curve", ForgettingCurveAction)
PostInsertActionRegistry.register("decay_eviction.time_decay", TimeDecayAction)

# [3] Structure Enrichment (A-Mem, HippoRAG, MemoryOS)
PostInsertActionRegistry.register("structure_enrichment.link_evolution", NewLinkEvolutionAction)
PostInsertActionRegistry.register(
    "structure_enrichment.graph_construction", GraphConstructionAction
)
PostInsertActionRegistry.register("structure_enrichment.heat_migration", HeatMigrationAction)

# ========================= Helper Functions =========================


def get_action(name: str, config: dict) -> BasePostInsertAction:
    """Convenience function to get and instantiate an action.

    Args:
        name: Action name
        config: Action configuration

    Returns:
        Instantiated action object

    Example:
        >>> action = get_action("distillation", {"similarity_threshold": 0.9})
        >>> result = action.execute(input_data, service, llm)
    """
    action_class = PostInsertActionRegistry.get(name)
    return action_class(config)
