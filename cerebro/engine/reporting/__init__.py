# cerebro/engine/reporting/__init__.py
"""
Reporting helpers — core trust feature (engine home).
- write_json_report: scan + delete plan as structured JSON for auditing.
- write_cleanup_scripts: bash / PowerShell scripts for reproducible cleanup.
"""

from .json_report import write_json_report
from .script_report import write_cleanup_scripts

__all__ = ["write_json_report", "write_cleanup_scripts"]
