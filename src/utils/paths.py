"""Project path constants.

Provides PROJECT_ROOT as a single anchor for resolving paths to data files,
config, and other repo-relative resources. This decouples runtime behavior
from the caller's cwd, so main.py works regardless of how it's launched.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
