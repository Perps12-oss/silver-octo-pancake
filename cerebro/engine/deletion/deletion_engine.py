# cerebro/engine/deletion/deletion_engine.py
"""
Single entrypoint for deletion execution (Gate A).
Uses domain DeletionPolicy/DeletionRequest; delegates to core DeletionEngine for filesystem ops.
"""

from __future__ import annotations

from cerebro.core.deletion import (
    DeletionEngine,
    DeletionPolicy,
    DeletionRequest,
    SingleDeletionResult,
    BatchDeletionResult,
)

__all__ = [
    "DeletionEngine",
    "DeletionPolicy",
    "DeletionRequest",
    "SingleDeletionResult",
    "BatchDeletionResult",
]
