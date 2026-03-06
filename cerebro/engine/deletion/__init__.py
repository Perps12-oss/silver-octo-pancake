# cerebro/engine/deletion/__init__.py
"""
Deletion engine entrypoint (Gate A).
Authoritative execution: move to trash or permanent delete via domain policy.
"""

from .deletion_engine import (
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
