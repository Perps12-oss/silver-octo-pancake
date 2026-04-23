"""Discriminated UI actions for scan shell orchestration (dispatch entry)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Union


@dataclass(frozen=True)
class ActionScanCompleted:
    groups: List[Any]
    mode: str = "files"


@dataclass(frozen=True)
class ActionOpenGroup:
    group_id: int
    groups: List[Any]


@dataclass(frozen=True)
class ActionScanHistoryCleared:
    pass


@dataclass(frozen=True)
class ActionOpenSession:
    session: Any


@dataclass(frozen=True)
class ActionNavigateResults:
    """Switch to Results tab (history pick, etc.)."""

    pass


ScanUiAction = Union[
    ActionScanCompleted,
    ActionOpenGroup,
    ActionScanHistoryCleared,
    ActionOpenSession,
    ActionNavigateResults,
]


__all__ = [
    "ActionNavigateResults",
    "ActionOpenGroup",
    "ActionOpenSession",
    "ActionScanCompleted",
    "ActionScanHistoryCleared",
    "ScanUiAction",
]
