"""Entry point for the CDP ML subsystem."""

from __future__ import annotations

__all__: list[str] = []

# Exceptions
try:
    from .exceptions import (
        BackendNotAvailable,
        EvaluationError,
        InvalidConfig,
        MLBaseError,
        TrainingError,
    )

    __all__.extend(
        [
            "MLBaseError",
            "BackendNotAvailable",
            "InvalidConfig",
            "TrainingError",
            "EvaluationError",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    MLBaseError = None  # type: ignore
    BackendNotAvailable = None  # type: ignore
    InvalidConfig = None  # type: ignore
    TrainingError = None  # type: ignore
    EvaluationError = None  # type: ignore


# Types
try:
    from .types import EvalResult, MetricSpec, PrivacySummary, TrainBatch, TrainResult

    __all__.extend(
        [
            "TrainBatch",
            "TrainResult",
            "EvalResult",
            "MetricSpec",
            "PrivacySummary",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    TrainBatch = None  # type: ignore
    TrainResult = None  # type: ignore
    EvalResult = None  # type: ignore
    MetricSpec = None  # type: ignore
    PrivacySummary = None  # type: ignore


# Configurations
try:
    from .config import AccountingConfig, DPConfig, MLConfig, ModelConfig, TrainingConfig

    __all__.extend(
        [
            "ModelConfig",
            "TrainingConfig",
            "DPConfig",
            "AccountingConfig",
            "MLConfig",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    ModelConfig = None  # type: ignore
    TrainingConfig = None  # type: ignore
    DPConfig = None  # type: ignore
    AccountingConfig = None  # type: ignore
    MLConfig = None  # type: ignore


# Utilities
try:
    from .utils import checkpoint_path, json_read, json_write, resolve_device, seed_everything

    __all__.extend(
        [
            "seed_everything",
            "resolve_device",
            "checkpoint_path",
            "json_read",
            "json_write",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    seed_everything = None  # type: ignore
    resolve_device = None  # type: ignore
    checkpoint_path = None  # type: ignore
    json_read = None  # type: ignore
    json_write = None  # type: ignore


# Backends
try:
    from .backends import BackendCapabilities, BackendSpec, detect_available_backends, get_backend

    __all__.extend(
        [
            "BackendCapabilities",
            "BackendSpec",
            "detect_available_backends",
            "get_backend",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    BackendCapabilities = None  # type: ignore
    BackendSpec = None  # type: ignore
    detect_available_backends = None  # type: ignore
    get_backend = None  # type: ignore
