"""
ML error hierarchy for the CDP ML base layer.

Responsibilities
  - Define shared exception types for ML configuration and runtime failures.
  - Provide a specialized error for missing optional backends.
  - Normalize error messaging used across ML utilities and training flows.

Usage Context
  - Raised by ML configuration validation, backend discovery, and training loops.

Limitations
  - Exceptions only carry message text and optional context attributes.
"""
# 说明：CDP ML 基础层的异常体系，统一配置、训练、评估与后端缺失的错误类型。
# 职责：
# - MLBaseError：ML 子模块统一基类异常
# - BackendNotAvailable：可选后端缺失或不可用时的异常
# - InvalidConfig/TrainingError/EvaluationError：配置与训练/评估阶段的专用异常

from __future__ import annotations

from typing import Optional, Sequence, Union


class MLBaseError(RuntimeError):
    """
    Base error type for ML subsystem failures.

    - Configuration
      - No additional fields beyond the error message.

    - Behavior
      - Serves as the common ancestor for ML-specific exceptions.

    - Usage Notes
      - Catch to handle ML errors without mixing with core errors.
    """


class BackendNotAvailable(MLBaseError):
    """
    Raised when a requested ML backend is missing or unavailable.

    - Configuration
      - backend: The backend identifier that failed to load.
      - extras: Optional extras hint for installation.

    - Behavior
      - Formats a human-friendly message with an optional install hint.

    - Usage Notes
      - Use for optional dependencies such as torch or tensorflow.
    """

    def __init__(
        self,
        backend: str,
        *,
        extras: Optional[Union[Sequence[str], str]] = None,
        message: Optional[str] = None,
    ) -> None:
        # 构造包含可选依赖提示信息的错误消息，便于用户快速定位安装方式
        extras_text = None
        if extras:
            if isinstance(extras, str):
                extras_text = extras
            else:
                extras_text = ",".join(extras)
        hint = f" Install with `pip install dplib[{extras_text}]`." if extras_text else ""
        final_message = message or f"backend '{backend}' is not available."
        super().__init__(f"{final_message}{hint}")
        self.backend = backend
        self.extras = extras_text


class InvalidConfig(MLBaseError):
    """
    Raised when ML configuration cannot be parsed or validated.

    - Configuration
      - No additional fields beyond the error message.

    - Behavior
      - Indicates configuration issues detected in ML setup.

    - Usage Notes
      - Prefer ParamValidationError for argument-level validation.
    """


class TrainingError(MLBaseError):
    """
    Raised when ML training fails during execution.

    - Configuration
      - No additional fields beyond the error message.

    - Behavior
      - Captures training runtime failures or backend errors.

    - Usage Notes
      - Use to separate training failures from evaluation failures.
    """


class EvaluationError(MLBaseError):
    """
    Raised when ML evaluation fails during execution.

    - Configuration
      - No additional fields beyond the error message.

    - Behavior
      - Captures evaluation runtime failures or metric errors.

    - Usage Notes
      - Use to separate evaluation failures from training failures.
    """
