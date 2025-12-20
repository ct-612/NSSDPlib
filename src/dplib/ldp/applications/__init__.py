"""LDP applications entry point."""

from __future__ import annotations

from .base import BaseLDPApplication
from .heavy_hitters import HeavyHittersApplication
from .frequency_estimation import FrequencyEstimationApplication
from .range_queries import RangeQueriesApplication
from .marginals import MarginalsApplication
from .key_value import KeyValueApplication
from .sequence_analysis import SequenceAnalysisApplication
from .application_factory import ApplicationFactory, create_application, get_application_class, register_application

__all__ = [
    "BaseLDPApplication",
    "HeavyHittersApplication",
    "FrequencyEstimationApplication",
    "RangeQueriesApplication",
    "MarginalsApplication",
    "KeyValueApplication",
    "SequenceAnalysisApplication",
    "ApplicationFactory",
    "register_application",
    "get_application_class",
    "create_application",
]
