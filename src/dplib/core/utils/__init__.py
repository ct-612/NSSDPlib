"""Shared utility helpers used across the core library."""

from .math_utils import (
    logsumexp,
    softmax,
    stable_mean,
    stable_variance,
    clamp_probabilities,
)
from .random import (
    create_rng,
    reseed_rng,
    RNGPool,
    split_rng,
    sample_noise,
)
from .config import (
    RuntimeConfig,
    get_config,
    configure,
)
from .serialization import (
    serialize_to_json,
    deserialize_from_json,
    mask_sensitive_data,
    VersionedPayload,
)
from .logging import (
    get_logger,
    configure_logging,
)
from .param_validation import (
    ensure,
    ensure_type,
    validate_arguments,
    ParamValidationError,
)
from .performance import (
    Timer,
    time_function,
    benchmark,
    memory_profile,
)

__all__ = [
    "logsumexp",
    "softmax",
    "stable_mean",
    "stable_variance",
    "clamp_probabilities",
    "create_rng",
    "reseed_rng",
    "split_rng",
    "sample_noise",
    "RNGPool",
    "RuntimeConfig",
    "get_config",
    "configure",
    "serialize_to_json",
    "deserialize_from_json",
    "mask_sensitive_data",
    "VersionedPayload",
    "get_logger",
    "configure_logging",
    "ensure",
    "ensure_type",
    "validate_arguments",
    "ParamValidationError",
    "Timer",
    "time_function",
    "benchmark",
    "memory_profile",
]
