"""
Decay Eviction Strategies
=========================

Papers: MemoryBank, LD-Agent
Strategy Type: decay_eviction
Trigger Mechanism: temporal (time-based) / threshold (score-based)

Implements memory forgetting based on:
- Ebbinghaus forgetting curve (MemoryBank)
- Time-based decay (LD-Agent)
"""

from .forgetting_curve import ForgettingCurveAction
from .time_decay import TimeDecayAction

__all__ = ["ForgettingCurveAction", "TimeDecayAction"]
