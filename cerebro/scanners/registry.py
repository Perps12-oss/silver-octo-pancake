# cerebro/scanners/registry.py
"""
Scanner registry (Batch 5).
Core strategies: simple, advanced, turbo.
Ultra and quantum remain in core; register here for optional use.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

# Core scanner tier names
CORE_TIERS = ("simple", "advanced", "turbo")

# tier -> factory(config) -> scanner with .scan(roots) and optionally .cancel()
_SCANNER_REGISTRY: Dict[str, Optional[Callable[..., Any]]] = {}


def _register_core() -> None:
    """Register core strategies. Simple = use ScanEngine (None)."""
    _SCANNER_REGISTRY["simple"] = None  # Worker uses ScanEngine

    def _advanced_factory(config: Any = None) -> Any:
        from cerebro.core.scanners import AdvancedScanner
        return AdvancedScanner()

    _SCANNER_REGISTRY["advanced"] = _advanced_factory

    def _turbo_factory(config: Any = None) -> Any:
        from cerebro.core.scanner_adapter import create_optimized_scanner
        return create_optimized_scanner(None)

    _SCANNER_REGISTRY["turbo"] = _turbo_factory


# One-time init
_register_core()


def get_scanner(tier: str) -> Optional[Callable[..., Any]]:
    """
    Return factory for the given tier, or None.
    None means use default (ScanEngine) path.
    """
    t = (tier or "simple").strip().lower()
    return _SCANNER_REGISTRY.get(t)


def register_scanner(tier: str, factory: Optional[Callable[..., Any]]) -> None:
    """Register a scanner factory for a tier (e.g. ultra, quantum from extensions)."""
    _SCANNER_REGISTRY[(tier or "").strip().lower()] = factory


def list_tiers() -> tuple:
    """Return registered tier names (core + any registered)."""
    return tuple(_SCANNER_REGISTRY.keys())


__all__ = ["CORE_TIERS", "get_scanner", "register_scanner", "list_tiers"]
