"""Core privacy abstractions and shared exceptions."""
from .base_mechanism import (
    BaseMechanism,
    MechanismError,
    ValidationError,
    CalibrationError,
    NotCalibratedError,
)
from .privacy_accountant import (
    PrivacyAccountant,
    PrivacyBudget,
    PrivacyEvent,
    BudgetExceededError,
)
from .composition import (
    CompositionResult,
    CompositionRule,
    SequentialCompositionRule,
    ParallelCompositionRule,
    HigherOrderCompositionRule,
    CompositionError,
    normalize_privacy_event,
    normalize_privacy_events,
)
from .budget_tracker import (
    BudgetTracker,
    BudgetAlert,
    TrackedScope,
    BudgetTrackerError,
    ScopeNotRegisteredError,
)
__all__ = [
    "BaseMechanism",
    "MechanismError",
    "ValidationError",
    "CalibrationError",
    "NotCalibratedError",
    "PrivacyAccountant",
    "PrivacyBudget",
    "PrivacyEvent",
    "BudgetExceededError",
    "CompositionResult",
    "CompositionRule",
    "SequentialCompositionRule",
    "ParallelCompositionRule",
    "HigherOrderCompositionRule",
    "CompositionError",
    "normalize_privacy_event",
    "normalize_privacy_events",
    "BudgetTracker",
    "BudgetAlert",
    "TrackedScope",
    "BudgetTrackerError",
    "ScopeNotRegisteredError",
]
