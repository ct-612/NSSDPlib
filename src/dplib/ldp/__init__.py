"""Entry point for the Local Differential Privacy (LDP) subsystem."""

from __future__ import annotations

from .types import EncodedValue, Estimate, LDPBudgetSummary, LDPReport, LDPToCDPEvent, LocalPrivacyUsage

__all__ = [
    "EncodedValue",
    "Estimate",
    "LDPBudgetSummary",
    "LDPReport",
    "LDPToCDPEvent",
    "LocalPrivacyUsage",
]

# Mechanisms
try:
    from .mechanisms.base import BaseLDPMechanism  # type: ignore
    from .mechanisms.mechanism_factory import (  # type: ignore
        create_default_grr,
        create_default_oue,
        create_mechanism,
    )
    from .mechanisms.mechanism_registry import (  # type: ignore
        MECHANISM_REGISTRY,
        ensure_mechanism_supports_model,
        get_mechanism_class,
        normalize_mechanism,
        registered_mechanisms_snapshot,
    )

    __all__.extend(
        [
            "BaseLDPMechanism",
            "MECHANISM_REGISTRY",
            "normalize_mechanism",
            "get_mechanism_class",
            "ensure_mechanism_supports_model",
            "registered_mechanisms_snapshot",
            "create_mechanism",
            "create_default_grr",
            "create_default_oue",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    BaseLDPMechanism = None  # type: ignore
    MECHANISM_REGISTRY = None  # type: ignore
    normalize_mechanism = None  # type: ignore
    get_mechanism_class = None  # type: ignore
    ensure_mechanism_supports_model = None  # type: ignore
    registered_mechanisms_snapshot = None  # type: ignore
    create_mechanism = None  # type: ignore
    create_default_grr = None  # type: ignore
    create_default_oue = None  # type: ignore


# Encoders
try:
    from .encoders.base import BaseEncoder  # type: ignore
    from .encoders.encoder_factory import EncoderFactory  # type: ignore

    __all__.extend(["BaseEncoder", "EncoderFactory"])
except Exception:  # pragma: no cover - optional until implemented
    BaseEncoder = None  # type: ignore
    EncoderFactory = None  # type: ignore


# Aggregators
try:
    from .aggregators.base import BaseAggregator  # type: ignore
    from .aggregators.aggregator_factory import AggregatorFactory  # type: ignore

    __all__.extend(["BaseAggregator", "AggregatorFactory"])
except Exception:  # pragma: no cover - optional until implemented
    BaseAggregator = None  # type: ignore
    AggregatorFactory = None  # type: ignore


# Composition / accounting
try:
    from .composition.privacy_accountant import LDPPrivacyAccountant  # type: ignore

    __all__.extend(["LDPPrivacyAccountant"])
except Exception:  # pragma: no cover - optional until implemented
    LDPPrivacyAccountant = None  # type: ignore


# Applications
try:
    from .applications.base import BaseLDPApplication  # type: ignore
    from .applications.application_factory import (  # type: ignore
        ApplicationFactory,
        create_application,
        get_application_class,
        register_application,
    )

    __all__.extend(
        [
            "BaseLDPApplication",
            "ApplicationFactory",
            "register_application",
            "get_application_class",
            "create_application",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    BaseLDPApplication = None  # type: ignore
    ApplicationFactory = None  # type: ignore
    register_application = None  # type: ignore
    get_application_class = None  # type: ignore
    create_application = None  # type: ignore
