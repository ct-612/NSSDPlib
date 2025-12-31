"""Entry point for the sklearn ML backend."""

from __future__ import annotations

__all__: list[str] = []

try:
    from .callbacks import Callback, CallbackRunner
    from .estimator_wrappers import SklearnEstimatorWrapper

    __all__.extend(["Callback", "CallbackRunner", "SklearnEstimatorWrapper"])
except Exception:  # pragma: no cover - optional until implemented
    Callback = None  # type: ignore
    CallbackRunner = None  # type: ignore
    SklearnEstimatorWrapper = None  # type: ignore
