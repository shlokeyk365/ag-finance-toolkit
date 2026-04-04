"""Shared pytest configuration for local package imports.

The repo is exercised directly from the working tree during development, so
tests should be able to import ``agfin`` without requiring an editable install
first. This small bootstrap keeps the test environment predictable across
different local setups.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
