from __future__ import annotations

from .compress import CompressAction
from .fact_extract import FactExtractAction
from .triplet_extract import TripleExtractAction

__all__ = [
    "FactExtractAction",
    "TripleExtractAction",
    "CompressAction",
]
