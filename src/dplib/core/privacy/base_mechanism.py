"""
Core abstractions shared by every mechanism implementation.

Responsibilities:
    * common parameter validation and RNG management
    * consistent calibration lifecycle
    * serialization helpers
    * purpose specific exceptions
"""
# 说明：定义本库所有机制共享的抽象基类与通用工具。
# 职责：
# - 通用参数校验与随机数生成器（RNG）管理
# - 统一的校准生命周期
# - 序列化辅助工具
# - 特定用途的异常类型

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple, Type
import json
import numbers
import numpy as np


# Exceptions -----------------------------------------------------------------
# 机制相关异常类型。
class MechanismError(Exception):
    """Base exception for mechanism errors."""


class ValidationError(MechanismError):
    """Raised when input parameters are invalid."""


class CalibrationError(MechanismError):
    """Raised when calibration fails or is inconsistent."""


class NotCalibratedError(MechanismError):
    """Raised when an operation requires prior calibration."""


# Helper for RNG --------------------------------------------------------------
# 统一的随机数生成器工厂：支持 None、现成的 Generator、或任意可播种对象。
def _make_rng(seed: Optional[Any]) -> np.random.Generator:
    """Create a fresh numpy Generator from diverse seed types."""
    if seed is None:
        return np.random.default_rng()
    if isinstance(seed, np.random.Generator):
        return seed
    return np.random.default_rng(seed)


# Base abstraction ------------------------------------------------------------
# 所有机制的抽象基类：
#  - 负责 epsilon/delta 校验与 RNG 管理
#  - 约定统一的校准生命周期（calibrate/require_calibrated）
#  - 提供序列化/反序列化与 JSON 辅助
#  - 提供数值输入的类型与形状规整工具
class BaseMechanism(ABC):
    """Abstract base class for all mechanisms."""

    def __init__(
        self,
        epsilon: float,
        delta: float = 0.0,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 参数基本校验（类型与取值范围）
        self._validate_epsilon(epsilon)
        self._validate_delta(delta)

        # 规范化存储，并创建 RNG；初始化生命周期与元数据
        self.epsilon: float = float(epsilon)
        self.delta: float = float(delta)
        self.name: str = name or self.__class__.__name__
        self._rng: np.random.Generator = _make_rng(rng)
        self._calibrated: bool = False
        self._meta: Dict[str, Any] = {}

    # Validation helpers ------------------------------------------------------
    # 基础参数校验：确保为 Real 且满足正性/非负性约束。
    @staticmethod
    def _validate_epsilon(eps: float) -> None:
        if not isinstance(eps, numbers.Real) or eps <= 0:
            raise ValidationError("epsilon must be a positive real number")

    @staticmethod
    def _validate_delta(delta: float) -> None:
        if not isinstance(delta, numbers.Real) or delta < 0:
            raise ValidationError("delta must be a non-negative real number")

    @staticmethod
    def _validate_sensitivity(sensitivity: float) -> None:
        if not isinstance(sensitivity, numbers.Real) or sensitivity <= 0:
            raise ValidationError("sensitivity must be a positive real number")

    @staticmethod
    def _validate_value(value: Any) -> None:
        # 仅作存在性与可数组化的防御性检查；具体机制可覆盖更严格校验。
        if isinstance(value, (str, bytes)):
            return
        try:
            _ = np.asarray(value)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError("value must be numeric or array-like") from exc

    # Calibration lifecycle ---------------------------------------------------
    # 对外统一的校准入口：可选择性传入 sensitivity 或机制特定参数。
    # 成功后会将 _calibrated 置为 True，用于运行期保护。
    def calibrate(self, sensitivity: Optional[float] = None, **kwargs: Any) -> "BaseMechanism":
        """
        Common calibration entry point.
        - Args:
            - sensitivity: Optional numeric sensitivity override.
            - **kwargs: Mechanism specific calibration kwargs.
        - Returns:
            - self (allows chaining).
        """
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
        # 将已校准的参数委托给子类处理，仅在子类成功应用这些参数后才切换生命周期标志位。
        self._calibrate_parameters(sensitivity=sensitivity, **kwargs)
        self._calibrated = True
        return self

    @abstractmethod
    # 由子类决定如何将 ε、δ、敏感度映射到内部噪声参数。
    def _calibrate_parameters(self, *, sensitivity: Optional[float], **kwargs: Any) -> None:
        """Subclasses implement their own calibration logic."""

    @abstractmethod
    # 由子类实现具体的噪声添加逻辑。
    def randomise(self, value: Any) -> Any:
        """Add mechanism specific noise to the provided value."""

    # 语义别名，便于更自然的 API 使用。
    def add_noise(self, value: Any) -> Any:
        """Alias for randomise."""
        return self.randomise(value)

    # 清空校准标志，但不触碰具体机制内部参数（如已计算的 p/q 或尺度）。
    def reset_calibration(self) -> None:
        """Reset calibrated flag without touching mechanism specific parameters."""
        self._calibrated = False

    @property
    def calibrated(self) -> bool:   # 查询校准状态。
        return self._calibrated

    # Serialization -----------------------------------------------------------
    # 生成可 JSON 化的状态快照；子类可在此基础上扩展特定字段（如 domain、p、q）。
    def serialize(self) -> Dict[str, Any]:
        """Return a JSON serialisable snapshot of the mechanism."""
        return {
            "class": f"{self.__class__.__module__}.{self.__class__.__qualname__}",
            "mechanism": self.mechanism_id,
            "name": self.name,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "calibrated": bool(self._calibrated),
            "meta": dict(self._meta),
        }

    @classmethod
    def deserialize(cls: Type["BaseMechanism"], data: Dict[str, Any]) -> "BaseMechanism":
        """
        Generic reconstruction helper for subclasses whose constructor only requires epsilon/delta/rng/name.
        """
        if "epsilon" not in data:
            raise ValidationError("serialized data missing 'epsilon' field")

        epsilon = data.get("epsilon")
        delta = data.get("delta", 0.0)
        name = data.get("name", None)
        instance = cls(epsilon=epsilon, delta=delta, rng=None, name=name)
        instance._meta = dict(data.get("meta", {}))
        instance._calibrated = bool(data.get("calibrated", False))
        return instance

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.serialize(), default=str)

    @classmethod
    def from_json(cls: Type["BaseMechanism"], text: str) -> "BaseMechanism":
        data = json.loads(text)
        return cls.deserialize(data)

    # Utilities ---------------------------------------------------------------
    # 运行期保护：要求先完成 calibrate，否则抛出 NotCalibratedError。
    def require_calibrated(self) -> None:
        if not self._calibrated:
            raise NotCalibratedError("mechanism not calibrated; call calibrate() first")

    # 重置 RNG，使同一 seed 可复现实验；与 serialize/deserialize 配合用于行为一致性测试。
    def reseed(self, seed: Optional[Any]) -> None:
        """Replace RNG with a new generator constructed from `seed`."""
        self._rng = _make_rng(seed)

    @property
    def mechanism_id(self) -> str:
        """Stable identifier used in serialization/pipelines."""
        name = self.__class__.__name__
        lowered = name.lower()
        suffix = "mechanism"
        if lowered.endswith(suffix):
            return lowered[: -len(suffix)] or lowered
        return lowered

    # Shared numeric helpers --------------------------------------------------
    # 把任意数值/序列转为 np.ndarray[float]，同时记录是否源自标量，便于还原类型。
    @staticmethod
    def _coerce_numeric(value: Any) -> Tuple[np.ndarray, bool]:
        if isinstance(value, (str, bytes)):
            raise ValidationError("value must be numeric, sequence, or ndarray")
        try:
            arr = np.asarray(value, dtype=float)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValidationError("value must be numeric, sequence, or ndarray") from exc
        # 跟踪原始输入是否为标量，以便在后续恢复结果时能准确还原其类型。
        return arr, arr.ndim == 0

    # 按原输入类型“还原”数值结果：标量/ndarray/tuple/list。
    @staticmethod
    def _restore_numeric_like(original: Any, value: np.ndarray, was_scalar: bool) -> Any:
        if was_scalar:
            return float(value)
        if isinstance(original, np.ndarray):
            return value
        if isinstance(original, tuple):
            return tuple(value.tolist())
        if isinstance(original, list):
            return value.tolist()
        return value

    # Representation ----------------------------------------------------------
    # 便于调试与日志的简洁 __repr__，包含名称、(ε,δ) 与校准状态。
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name} "
            f"eps={self.epsilon} delta={self.delta} calibrated={self._calibrated}>"
        )
