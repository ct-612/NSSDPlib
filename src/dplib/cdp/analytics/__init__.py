"""Entry point for CDP analytics components."""

from __future__ import annotations

from .queries import (
    PrivateCountQuery,
    PrivateHistogramQuery,
    PrivateMeanQuery,
    PrivateRangeQuery,
    PrivateSumQuery,
    PrivateVarianceQuery,
    QueryEngine,
)
from .reporting import (
    ErrorMetrics,
    PrivacyAnnotation,
    PrivacyBudgetSnapshot,
    PrivacyReport,
    PrivacyUsageRecord,
    QueryUtilityRecord,
    UtilityCurve,
    UtilityReport,
)
from .synthetic_data import (
    BayesianNetworkGenerator,
    CopulaGenerator,
    DPSyntheticGAN,
    MarginalGenerator,
    SyntheticDataGenerator,
    SyntheticGeneratorConfig,
    create_generator,
)

__all__ = [
    # Queries
    "PrivateCountQuery",
    "PrivateHistogramQuery",
    "PrivateMeanQuery",
    "PrivateRangeQuery",
    "PrivateSumQuery",
    "PrivateVarianceQuery",
    "QueryEngine",
    # Reporting
    "PrivacyAnnotation",
    "PrivacyBudgetSnapshot",
    "PrivacyReport",
    "PrivacyUsageRecord",
    "ErrorMetrics",
    "QueryUtilityRecord",
    "UtilityCurve",
    "UtilityReport",
    # Synthetic data
    "SyntheticGeneratorConfig",
    "SyntheticDataGenerator",
    "create_generator",
    "MarginalGenerator",
    "BayesianNetworkGenerator",
    "DPSyntheticGAN",
    "CopulaGenerator",
]
