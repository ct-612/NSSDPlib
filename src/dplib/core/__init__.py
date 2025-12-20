"""Entry point for the core library components."""

from __future__ import annotations

__all__: list[str] = []

# Data
try:
    from .data import (
        BaseDomain,
        BucketizedDomain,
        ContinuousDomain,
        DataValidationError,
        Dataset,
        DatasetError,
        DiscreteDomain,
        DomainError,
        Schema,
        SchemaField,
        SchemaValidator,
    )

    __all__.extend(
        [
            "BaseDomain",
            "BucketizedDomain",
            "ContinuousDomain",
            "DataValidationError",
            "Dataset",
            "DatasetError",
            "DiscreteDomain",
            "DomainError",
            "Schema",
            "SchemaField",
            "SchemaValidator",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    BaseDomain = None  # type: ignore
    BucketizedDomain = None  # type: ignore
    ContinuousDomain = None  # type: ignore
    DataValidationError = None  # type: ignore
    Dataset = None  # type: ignore
    DatasetError = None  # type: ignore
    DiscreteDomain = None  # type: ignore
    DomainError = None  # type: ignore
    Schema = None  # type: ignore
    SchemaField = None  # type: ignore
    SchemaValidator = None  # type: ignore


# Privacy
try:
    from .privacy import (
        BaseMechanism,
        BudgetExceededError,
        BudgetTracker,
        CalibrationError,
        MechanismError,
        MechanismType,
        NotCalibratedError,
        PrivacyAccountant,
        PrivacyBudget,
        PrivacyEvent,
        PrivacyGuarantee,
        PrivacyModel,
        ValidationError,
    )

    __all__.extend(
        [
            "BaseMechanism",
            "BudgetExceededError",
            "BudgetTracker",
            "CalibrationError",
            "MechanismError",
            "MechanismType",
            "NotCalibratedError",
            "PrivacyAccountant",
            "PrivacyBudget",
            "PrivacyEvent",
            "PrivacyGuarantee",
            "PrivacyModel",
            "ValidationError",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    BaseMechanism = None  # type: ignore
    BudgetExceededError = None  # type: ignore
    BudgetTracker = None  # type: ignore
    CalibrationError = None  # type: ignore
    MechanismError = None  # type: ignore
    MechanismType = None  # type: ignore
    NotCalibratedError = None  # type: ignore
    PrivacyAccountant = None  # type: ignore
    PrivacyBudget = None  # type: ignore
    PrivacyEvent = None  # type: ignore
    PrivacyGuarantee = None  # type: ignore
    PrivacyModel = None  # type: ignore
    ValidationError = None  # type: ignore


# Utils
try:
    from .utils import (
        ParamValidationError,
        RuntimeConfig,
        configure,
        get_config,
        get_logger,
    )

    __all__.extend(
        [
            "ParamValidationError",
            "RuntimeConfig",
            "configure",
            "get_config",
            "get_logger",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    ParamValidationError = None  # type: ignore
    RuntimeConfig = None  # type: ignore
    configure = None  # type: ignore
    get_config = None  # type: ignore
    get_logger = None  # type: ignore
