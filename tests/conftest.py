"""Shared pytest configuration and path setup for test modules."""

import sys
from pathlib import Path

import pytest
import numpy as np
import random
import os

# Ensure repo root and src/ are on sys.path for all tests
_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
for p in (str(_ROOT), str(_SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)
