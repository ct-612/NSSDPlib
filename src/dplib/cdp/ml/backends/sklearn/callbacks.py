"""
Callback utilities for sklearn-style training loops.

Responsibilities
  - Define a minimal callback interface for training lifecycle events.
  - Provide a runner that emits callback events around fit/partial_fit.
  - Normalize optional arguments when invoking estimator methods.

Usage Context
  - Used by sklearn backends to integrate training callbacks.

Limitations
  - Emits one step per epoch when using partial_fit.
  - Falls back to a single fit when partial_fit is unavailable.
"""
# 说明：sklearn 风格训练回调工具，提供基础回调接口与运行器。
# 职责：
# - Callback：定义训练生命周期的基础回调方法
# - CallbackRunner：围绕 fit/partial_fit 发出事件并处理常见参数
# - 安全传递 sample_weight 与 classes 等可选参数

from __future__ import annotations

import inspect
from typing import Any, Iterable, Mapping, Optional, Sequence

from dplib.core.utils.logging import get_logger
from dplib.core.utils.param_validation import ensure, ensure_type

logger = get_logger(__name__)


def _supports_argument(func: Any, name: str) -> bool:
    """Check whether a callable accepts a named argument."""
    # 使用签名检查方法是否接受指定参数名，无法检查时默认不传递
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False
    return name in signature.parameters


class Callback:
    """
    Base callback interface for training lifecycle events.

    - Configuration
      - No required configuration fields.

    - Behavior
      - Provides no-op hooks for subclasses to override.

    - Usage Notes
      - Extend and override the relevant lifecycle methods.
    """
    # 训练回调接口基类，默认空实现以便子类选择性覆盖

    def on_train_start(self, context: Mapping[str, Any]) -> None:
        """Handle the start of training."""
        # 默认空实现，留给子类覆盖
        return None

    def on_epoch_start(self, context: Mapping[str, Any]) -> None:
        """Handle the start of an epoch."""
        # 默认空实现，留给子类覆盖
        return None

    def on_step_end(self, context: Mapping[str, Any]) -> None:
        """Handle the end of a step."""
        # 默认空实现，留给子类覆盖
        return None

    def on_epoch_end(self, context: Mapping[str, Any]) -> None:
        """Handle the end of an epoch."""
        # 默认空实现，留给子类覆盖
        return None

    def on_train_end(self, context: Mapping[str, Any]) -> None:
        """Handle the end of training."""
        # 默认空实现，留给子类覆盖
        return None


class CallbackRunner:
    """
    Execute training loops while emitting callback events.

    - Configuration
      - callbacks: Iterable of Callback instances.

    - Behavior
      - Uses partial_fit when available, emitting one step per epoch.
      - Falls back to a single fit when partial_fit is unavailable.

    - Usage Notes
      - Provide classes when using partial_fit for classifiers.
    """
    # 训练回调运行器，围绕 fit/partial_fit 触发生命周期事件

    def __init__(self, callbacks: Optional[Iterable[Callback]] = None) -> None:
        """Create a callback runner with optional callbacks."""
        # 初始化回调列表，缺省时使用空列表
        self.callbacks = list(callbacks) if callbacks is not None else []

    def run(
        self,
        estimator: Any,
        features: Any,
        labels: Any,
        *,
        epochs: int = 1,
        sample_weight: Optional[Any] = None,
        classes: Optional[Sequence[Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """Run training with callbacks around fit or partial_fit."""
        # 执行训练并在关键阶段触发回调事件
        ensure_type(epochs, (int,), label="epochs")
        ensure(epochs > 0, "epochs must be > 0")
        context: dict[str, Any] = {
            "estimator": estimator,
            "epochs": epochs,
            "metadata": dict(metadata) if metadata is not None else {},
        }
        for callback in self.callbacks:
            callback.on_train_start(context)

        if hasattr(estimator, "partial_fit") and callable(getattr(estimator, "partial_fit")):
            for epoch in range(epochs):
                context["epoch"] = epoch
                for callback in self.callbacks:
                    callback.on_epoch_start(context)
                self._call_partial_fit(estimator, features, labels, sample_weight=sample_weight, classes=classes)
                context["step"] = epoch
                for callback in self.callbacks:
                    callback.on_step_end(context)
                for callback in self.callbacks:
                    callback.on_epoch_end(context)
            context["epochs_run"] = epochs
        else:
            if epochs > 1:
                logger.info("Estimator lacks partial_fit; running a single fit for %d requested epochs.", epochs)
            context["epoch"] = 0
            for callback in self.callbacks:
                callback.on_epoch_start(context)
            self._call_fit(estimator, features, labels, sample_weight=sample_weight)
            context["step"] = 0
            for callback in self.callbacks:
                callback.on_step_end(context)
            for callback in self.callbacks:
                callback.on_epoch_end(context)
            context["epochs_run"] = 1

        for callback in self.callbacks:
            callback.on_train_end(context)
        return estimator

    def _call_fit(
        self,
        estimator: Any,
        features: Any,
        labels: Any,
        *,
        sample_weight: Optional[Any] = None,
    ) -> None:
        """Call estimator.fit with supported arguments."""
        # 调用 fit 时仅传递估计器可接受的可选参数
        fit_kwargs: dict[str, Any] = {}
        if sample_weight is not None and _supports_argument(estimator.fit, "sample_weight"):
            fit_kwargs["sample_weight"] = sample_weight
        estimator.fit(features, labels, **fit_kwargs)

    def _call_partial_fit(
        self,
        estimator: Any,
        features: Any,
        labels: Any,
        *,
        sample_weight: Optional[Any] = None,
        classes: Optional[Sequence[Any]] = None,
    ) -> None:
        """Call estimator.partial_fit with supported arguments."""
        # 调用 partial_fit 时按需传递 classes 与 sample_weight
        fit_kwargs: dict[str, Any] = {}
        if sample_weight is not None and _supports_argument(estimator.partial_fit, "sample_weight"):
            fit_kwargs["sample_weight"] = sample_weight
        if classes is not None and _supports_argument(estimator.partial_fit, "classes"):
            fit_kwargs["classes"] = classes
        estimator.partial_fit(features, labels, **fit_kwargs)
