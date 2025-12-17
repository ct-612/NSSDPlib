"""LDP aggregation layer entrypoint."""

from __future__ import annotations

from .aggregator_factory import (
    AggregatorFactory,
    create_aggregator,
    get_aggregator_class,
    register_aggregator,
)
from .base import BaseAggregator, StatelessAggregator
from .consistency import ConsistencyPostProcessor
from .frequency import FrequencyAggregator
from .mean import MeanAggregator
from .quantile import QuantileAggregator
from .user_level import UserLevelAggregator
from .variance import VarianceAggregator

__all__ = [
    "BaseAggregator",
    "StatelessAggregator",
    "FrequencyAggregator",
    "MeanAggregator",
    "VarianceAggregator",
    "QuantileAggregator",
    "UserLevelAggregator",
    "ConsistencyPostProcessor",
    "register_aggregator",
    "get_aggregator_class",
    "create_aggregator",
    "AggregatorFactory",
]
