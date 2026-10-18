"""Pytest configuration: make the local config package importable.

The project uses a `config` package (config/settings.py) and a `src/`-layout package
(src/amd_hardware_advisor/). This conftest inserts both on sys.path so tests can import
`config.settings` and `amd_hardware_advisor` without installing the package first.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

for path in (PROJECT_ROOT / "src", PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
