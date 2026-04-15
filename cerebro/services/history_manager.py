# cerebro/services/history_manager.py
"""Compatibility facade for v2 deletion history manager."""

from __future__ import annotations

from cerebro.v2.core.deletion_history_db import get_default_history_manager


def get_history_manager():
    """Return the v2 sqlite deletion history manager."""
    return get_default_history_manager()
