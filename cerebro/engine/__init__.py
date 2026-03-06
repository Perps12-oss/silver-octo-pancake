# cerebro/engine/__init__.py
"""
Engine layer: scan pipeline, discovery, hashing, grouping, decision, deletion, reporting.
Stable entrypoint for scan execution: cerebro.engine.pipeline.scan_engine.ScanEngine
"""

from cerebro.engine.pipeline.scan_engine import ScanEngine
from cerebro.engine.pipeline.fast_pipeline import FastPipeline, FastFileInfo

__all__ = ["ScanEngine", "FastPipeline", "FastFileInfo"]
