"""
Sklearn estimator wrappers for the CDP ML backend.

Responsibilities
  - Provide a thin wrapper around sklearn estimators for fit/predict/score.
  - Normalize handling of sample_weight, class_weight, and random_state.
  - Capture optional DP settings for downstream consumers.

Usage Context
  - Used by ML models that rely on sklearn as a backend.

Limitations
  - Does not alter estimator training behavior for DP settings.
"""
# 说明：sklearn 估计器的轻量包装层，统一训练与推理接口并记录基础配置。
# 职责：
# - 规范 fit/predict/score 调用，安全传递 sample_weight 与 class_weight
# - 在初始化阶段尝试设置 random_state 与 class_weight
# - 记录 DP 配置供上层逻辑读取，但不改变训练行为

from __future__ import annotations

import inspect
from typing import Any, Mapping, Optional

from dplib.core.utils.logging import get_logger
from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError

logger = get_logger(__name__)


def _supports_argument(func: Any, name: str) -> bool:
    """Check whether a callable accepts a named argument."""
    # 使用签名检查方法是否接受指定参数名，无法检查时默认不传递
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    return name in signature.parameters


def _filter_kwargs(func: Any, values: Mapping[str, Any]) -> dict[str, Any]:
    """Filter kwargs to those supported by the callable signature."""
    # 根据函数签名过滤可用参数，避免向 sklearn 方法传入未知参数
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return {}
    return {key: value for key, value in values.items() if key in signature.parameters}


def _set_param_if_supported(estimator: Any, name: str, value: Any) -> bool:
    """Set an estimator parameter if it is supported."""
    # 若估计器支持指定参数则进行设置，返回是否设置成功
    if value is None:
        return False
    if hasattr(estimator, "get_params") and hasattr(estimator, "set_params"):
        params = estimator.get_params(deep=False)
        if name in params:
            estimator.set_params(**{name: value})
            return True
    if hasattr(estimator, name):
        setattr(estimator, name, value)
        return True
    return False


class SklearnEstimatorWrapper:
    """
    Thin wrapper for sklearn estimators with normalized argument handling.

    - Configuration
      - estimator: The sklearn estimator instance to wrap.
      - class_weight: Optional class weight mapping or strategy.
      - random_state: Optional seed to set on the estimator.
      - dp_enabled: Whether DP settings are recorded.
      - dp_params: Optional DP configuration mapping.

    - Behavior
      - Filters kwargs based on estimator signatures.
      - Passes sample_weight and class_weight when supported.
      - Leaves estimator training behavior unchanged.

    - Usage Notes
      - Use with any estimator exposing fit/predict/score methods.
    """
    # sklearn 估计器包装类，用于统一训练与评估调用并处理常见参数

    def __init__(
        self,
        estimator: Any,
        *,
        class_weight: Optional[Any] = None,
        random_state: Optional[int] = None,
        dp_enabled: bool = False,
        dp_params: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Initialize the wrapper and normalize estimator settings."""
        # 校验估计器基础接口并缓存配置参数
        if estimator is None:
            raise ParamValidationError("estimator must be provided")
        ensure(hasattr(estimator, "fit"), "estimator must implement fit")
        ensure(hasattr(estimator, "predict"), "estimator must implement predict")
        ensure(hasattr(estimator, "score"), "estimator must implement score")
        if random_state is not None:
            ensure_type(random_state, (int,), label="random_state")
        self.estimator = estimator
        self.class_weight = class_weight
        self.random_state = random_state
        self.dp_enabled = bool(dp_enabled)
        self.dp_params = dict(dp_params) if dp_params is not None else {}
        self.metadata = dict(metadata) if metadata is not None else {}

        if _set_param_if_supported(self.estimator, "random_state", self.random_state):
            logger.debug("Set random_state on sklearn estimator.")
        if self.class_weight is not None and _set_param_if_supported(self.estimator, "class_weight", self.class_weight):
            logger.debug("Set class_weight on sklearn estimator.")
        if self.dp_enabled:
            logger.info("DP settings recorded in wrapper; estimator behavior is unchanged.")

    def fit(
        self,
        features: Any,
        labels: Any,
        *,
        sample_weight: Optional[Any] = None,
        class_weight: Optional[Any] = None,
        **kwargs: Any,
    ) -> "SklearnEstimatorWrapper":
        """Fit the wrapped estimator with normalized arguments."""
        # 统一处理样本权重与类别权重，并过滤不支持的关键字参数
        fit_kwargs = _filter_kwargs(self.estimator.fit, kwargs)
        if sample_weight is not None and _supports_argument(self.estimator.fit, "sample_weight"):
            fit_kwargs["sample_weight"] = sample_weight
        effective_class_weight = class_weight if class_weight is not None else self.class_weight
        if effective_class_weight is not None and _supports_argument(self.estimator.fit, "class_weight"):
            fit_kwargs["class_weight"] = effective_class_weight
        self.estimator.fit(features, labels, **fit_kwargs)
        return self

    def predict(self, features: Any, **kwargs: Any) -> Any:
        """Predict using the wrapped estimator."""
        # 过滤 predict 的可用参数，避免向 sklearn 传入未知参数
        predict_kwargs = _filter_kwargs(self.estimator.predict, kwargs)
        return self.estimator.predict(features, **predict_kwargs)

    def score(
        self,
        features: Any,
        labels: Any,
        *,
        sample_weight: Optional[Any] = None,
        **kwargs: Any,
    ) -> float:
        """Score the wrapped estimator with optional sample weights."""
        # 过滤 score 的可用参数并按需传递 sample_weight
        score_kwargs = _filter_kwargs(self.estimator.score, kwargs)
        if sample_weight is not None and _supports_argument(self.estimator.score, "sample_weight"):
            score_kwargs["sample_weight"] = sample_weight
        return float(self.estimator.score(features, labels, **score_kwargs))
