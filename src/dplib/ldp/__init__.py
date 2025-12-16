"""Entry point for the Local Differential Privacy (LDP) subsystem in NSSDPlib.

Exposes core types along with encoder, mechanism, aggregator, composition,
and application entry points for downstream consumers.
"""

from __future__ import annotations

from .types import EncodedValue, Estimate, LDPReport

__all__ = ["EncodedValue", "Estimate", "LDPReport"]

# Mechanisms
try:
    from .mechanisms.base import BaseLDPMechanism  # type: ignore
    from .mechanisms import (  # type: ignore
        GRRMechanism,
        OUEMechanism,
        OLHMechanism,
        RAPPORMechanism,
        UnaryRandomizer,
        LocalLaplaceMechanism,
        LocalGaussianMechanism,
        PiecewiseMechanism,
        DuchiMechanism,
        MECHANISM_REGISTRY,
        normalize_mechanism,
        get_mechanism_class,
        ensure_mechanism_supports_model,
        registered_mechanisms_snapshot,
        create_mechanism,
        create_default_grr,
        create_default_oue,
    )

    __all__.extend(
        [
            "BaseLDPMechanism",
            "GRRMechanism",
            "OUEMechanism",
            "OLHMechanism",
            "RAPPORMechanism",
            "UnaryRandomizer",
            "LocalLaplaceMechanism",
            "LocalGaussianMechanism",
            "PiecewiseMechanism",
            "DuchiMechanism",
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
    GRRMechanism = None  # type: ignore
    OUEMechanism = None  # type: ignore
    OLHMechanism = None  # type: ignore
    RAPPORMechanism = None  # type: ignore
    UnaryRandomizer = None  # type: ignore
    LocalLaplaceMechanism = None  # type: ignore
    LocalGaussianMechanism = None  # type: ignore
    PiecewiseMechanism = None  # type: ignore
    DuchiMechanism = None  # type: ignore
    MECHANISM_REGISTRY = None  # type: ignore
    normalize_mechanism = None  # type: ignore
    get_mechanism_class = None  # type: ignore
    ensure_mechanism_supports_model = None  # type: ignore
    registered_mechanisms_snapshot = None  # type: ignore
    create_mechanism = None  # type: ignore
    create_default_grr = None  # type: ignore
    create_default_oue = None  # type: ignore

try:
    from .mechanisms.mechanism_factory import LDPMechanismFactory  # type: ignore
    from .mechanisms.mechanism_registry import LDPMechanismRegistry  # type: ignore

    __all__.extend(["LDPMechanismFactory", "LDPMechanismRegistry"])
except Exception:  # pragma: no cover - optional until implemented
    LDPMechanismFactory = None  # type: ignore
    LDPMechanismRegistry = None  # type: ignore


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
    from .composition.basic import basic_composition  # type: ignore
    from .composition.sequential import sequential_composition  # type: ignore
    from .composition.parallel import parallel_composition  # type: ignore

    __all__.extend(
        [
            "LDPPrivacyAccountant",
            "basic_composition",
            "sequential_composition",
            "parallel_composition",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    LDPPrivacyAccountant = None  # type: ignore
    basic_composition = None  # type: ignore
    sequential_composition = None  # type: ignore
    parallel_composition = None  # type: ignore


# Applications
try:
    from .applications import (  # type: ignore
        heavy_hitters,
        frequency_estimation,
        range_queries,
        marginals,
        key_value,
        sequence_analysis,
    )

    __all__.extend(
        [
            "heavy_hitters",
            "frequency_estimation",
            "range_queries",
            "marginals",
            "key_value",
            "sequence_analysis",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    heavy_hitters = None  # type: ignore
    frequency_estimation = None  # type: ignore
    range_queries = None  # type: ignore
    marginals = None  # type: ignore
    key_value = None  # type: ignore
    sequence_analysis = None  # type: ignore
