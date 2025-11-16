"""Core data abstractions shared across the core library."""

from .domain import (
    BaseDomain,
    DomainError,
    DomainInfo,
    DiscreteDomain,
    ContinuousDomain,
    BucketizedDomain,
)
from .dataset import (
    Dataset, 
    DatasetError, 
    DatasetMetadata,
    DataRecord,
)
from .transformers import (
    DataTransformer,
    ClippingTransformer,
    NormalizationTransformer,
    DiscretizerTransformer,
    OneHotEncoder,
    TransformerPipeline,
    TransformationError,
)
from .data_validation import (
    Schema,
    SchemaField,
    SchemaValidator,
    ValidationStrategy,
    DataValidationError,
    detect_missing,
)
from .statistics import (
    count, 
    summation, 
    mean, 
    variance, 
    histogram, 
    RunningStats,
)
from .sensitivity import (
    SensitivityError,
    count_global_sensitivity,
    sum_global_sensitivity,
    mean_global_sensitivity,
    local_sensitivity,
    SmoothSensitivityEstimate,
    smooth_sensitivity_mean,
)

__all__ = [
    "BaseDomain",
    "DomainError",
    "DomainInfo",
    "DiscreteDomain",
    "ContinuousDomain",
    "BucketizedDomain",
    "Dataset",
    "DatasetError",
    "DatasetMetadata",
    "DataRecord",
    "DataTransformer",
    "ClippingTransformer",
    "NormalizationTransformer",
    "DiscretizerTransformer",
    "OneHotEncoder",
    "TransformerPipeline",
    "TransformationError",
    "Schema",
    "SchemaField",
    "SchemaValidator",
    "ValidationStrategy",
    "DataValidationError",
    "detect_missing",
    "count",
    "summation",
    "mean",
    "variance",
    "histogram",
    "RunningStats",
    "SensitivityError",
    "count_global_sensitivity",
    "sum_global_sensitivity",
    "mean_global_sensitivity",
    "local_sensitivity",
    "SmoothSensitivityEstimate",
    "smooth_sensitivity_mean",
]
