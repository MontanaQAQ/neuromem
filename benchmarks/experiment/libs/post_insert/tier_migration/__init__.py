"""
Tier Migration Strategies
=========================

Papers: MemoryOS
Strategy Type: tier_migration
Trigger Mechanism: threshold (heat-based) / hybrid (capacity + heat)

Implements hierarchical memory migration:
- STM → MTM: FIFO overflow migration
- MTM → LPM: Heat-based profile extraction
"""

from .heat_migration import HeatMigrationAction

__all__ = ["HeatMigrationAction"]
