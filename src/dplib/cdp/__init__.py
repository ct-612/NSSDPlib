"""Entry point for the Centralised Differential Privacy (CDP) package."""

from __future__ import annotations

__all__: list[str] = []

# Mechanisms
try:
    from .mechanisms import (
        MECHANISM_REGISTRY,
        create_mechanism,
        ensure_mechanism_supports_model,
        get_mechanism_class,
        normalize_mechanism,
        registered_mechanisms_snapshot,
    )

    __all__.extend(
        [
            "MECHANISM_REGISTRY",
            "create_mechanism",
            "ensure_mechanism_supports_model",
            "get_mechanism_class",
            "normalize_mechanism",
            "registered_mechanisms_snapshot",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    MECHANISM_REGISTRY = None  # type: ignore
    create_mechanism = None  # type: ignore
    ensure_mechanism_supports_model = None  # type: ignore
    get_mechanism_class = None  # type: ignore
    normalize_mechanism = None  # type: ignore
    registered_mechanisms_snapshot = None  # type: ignore


# Composition / accounting
try:
    from .composition import (
        AccountingMethod,
        Allocation,
        BudgetScheduler,
        CDPPrivacyAccountant,
        MomentAccountant,
    )

    __all__.extend(
        [
            "AccountingMethod",
            "Allocation",
            "BudgetScheduler",
            "CDPPrivacyAccountant",
            "MomentAccountant",
        ]
    )
except Exception:  # pragma: no cover - optional until implemented
    AccountingMethod = None  # type: ignore
    Allocation = None  # type: ignore
    BudgetScheduler = None  # type: ignore
    CDPPrivacyAccountant = None  # type: ignore
    MomentAccountant = None  # type: ignore
