# src/dplib/core/privacy/base_mechanism.py
"""
Base mechanism abstraction for NSSDPlib.

Provides:
- standard interface for mechanisms: calibrate, randomise, serialize/deserialize
- common parameter validation
- simple RNG support
- specific exceptions for mechanism lifecycle and validation
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import numbers
import json
import numpy as np


# Exceptions
class MechanismError(Exception):
    """Base exception for mechanism errors."""


class ValidationError(MechanismError):
    """Raised when input parameters are invalid."""


class CalibrationError(MechanismError):
    """Raised when calibration fails or invalid."""


class NotCalibratedError(MechanismError):
    """Raised when an operation requires prior calibration."""


# Helper for RNG
def _make_rng(seed: Optional[Any]) -> np.random.Generator:
    """
    - 根据不同的种子类型创建numpy生成器。
    - 可接受None、整数、SeedSequence或已有的生成器对象。
    """
    if seed is None:
        return np.random.default_rng()
    if isinstance(seed, np.random.Generator):
        return seed
    return np.random.default_rng(seed)


class BaseMechanism(ABC):
    """
    - 抽象基类。子类需实现 calibrate 和 randomise 方法。

    - 生命周期：
        1. __init__ -> 创建机制实例（不需 calibrate）
        2. calibrate(...) -> 计算噪声参数，设置 self._calibrated = True
        3. randomise(value) -> 在 calibrated 状态下对值添加噪声并返回

    - 子类应调用 super().__init__(...) 以获得基本验证与 rng 支持。
    """

    def __init__(
        self,
        epsilon: float,
        delta: float = 0.0,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        """
        - 公共构造器。

        - Args:
            - epsilon: 隐私预算 ε，必须为正数。
            - delta: 隐私参数 δ，必须 >= 0。
            - rng: 随机数种子 / np.random.Generator / SeedSequence / int / None。
            - name: 可选机制名称（用于序列化/日志）。
        """
        self._validate_epsilon(epsilon)
        self._validate_delta(delta)

        self.epsilon: float = float(epsilon)
        self.delta: float = float(delta)
        self.name: str = name or self.__class__.__name__
        self._rng: np.random.Generator = _make_rng(rng)
        self._calibrated: bool = False
        # 子类可在 calibrate 时写入具体噪声参数，例如 self.scale, self.sensitivity 等
        self._meta: Dict[str, Any] = {}

    # ------------------------
    # Validation helpers
    # ------------------------
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
        if not isinstance(sensitivity, numbers.Real) or sensitivity < 0:
            raise ValidationError("sensitivity must be a non-negative real number")

    @staticmethod
    def _validate_value(value: Any) -> None:
        # 最小验证：数值或可转换为 numpy 数组
        if isinstance(value, (str, bytes)):
            return
        try:
            _ = np.asarray(value)
        except Exception:
            raise ValidationError("value must be numeric or array-like")

    # ------------------------
    # Abstract API
    # ------------------------
    @abstractmethod
    def calibrate(self, sensitivity: float, **kwargs) -> None:
        """
        - 根据敏感度与其它参数计算噪声参数并进入已校准状态。
        - 子类必须设置 self._calibrated = True。
        """
        raise NotImplementedError

    @abstractmethod
    def randomise(self, value: Any) -> Any:
        """
        - 对输入 value 添加噪声并返回。必须在 calibrate() 之后调用。
        - 子类可直接使用 self._rng 来生成随机数。
        """
        raise NotImplementedError

    # alias
    def add_noise(self, value: Any) -> Any:
        """- 别名，便于兼容其他实现。"""
        return self.randomise(value)

    # ------------------------
    # Serialization
    # ------------------------
    def serialize(self) -> Dict[str, Any]:
        """
        - 将机制的可重建状态序列化为字典。
        - 子类应在返回字典时包含任何必要的构造参数和校准参数。

        - 默认包含:
          - class: 全类名
          - name, epsilon, delta, calibrated(bool)
          - meta: 子类可附加任意元数据（需可 JSON 序列化）

        - 子类若需要，可 override 并调用 super().serialize() 然后扩展返回值。
        """
        base = {
            "class": f"{self.__class__.__module__}.{self.__class__.__qualname__}",
            "name": self.name,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "calibrated": bool(self._calibrated),
            "meta": self._meta,
        }
        return base

    @classmethod
    def deserialize(cls: Type["BaseMechanism"], data: Dict[str, Any]) -> "BaseMechanism":
        """
        - 从序列化字典重建机制实例。
        - 默认实现尝试使用 (epsilon, delta, rng=None, name=...) 构造实例，
        然后将 meta 恢复到 instance._meta 并在校准标记为 True 时留下未校准状态。
        - 子类若有特殊参数（例如 domain），必须 override 并在自己的实现中处理。

        - 注意：
            - deserialize 不会自动调用 calibrate。
            - 若需要可以由调用者负责或子类实现。
        """
        if "epsilon" not in data:
            raise ValidationError("serialized data missing 'epsilon' field")

        epsilon = data.get("epsilon")
        delta = data.get("delta", 0.0)
        name = data.get("name", None)
        # 这里不尝试还原 RNG；使用默认 RNG
        instance = cls(epsilon=epsilon, delta=delta, rng=None, name=name)
        instance._meta = dict(data.get("meta", {}))
        # 保留 calibrated 标记但不执行 calibrate
        instance._calibrated = bool(data.get("calibrated", False))
        return instance

    def to_json(self) -> str:
        """便捷方法：将 serialize() 的结果转为 JSON 字符串。"""
        return json.dumps(self.serialize(), default=str)

    @classmethod
    def from_json(cls: Type["BaseMechanism"], text: str) -> "BaseMechanism":
        data = json.loads(text)
        return cls.deserialize(data)

    # ------------------------
    # Utilities
    # ------------------------
    def require_calibrated(self) -> None:
        if not self._calibrated:
            raise NotCalibratedError("mechanism not calibrated; call calibrate() first")

    def reseed(self, seed: Optional[Any]) -> None:
        """重新设置 RNG。"""
        self._rng = _make_rng(seed)

    # ------------------------
    # Representation
    # ------------------------
    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name={self.name} "
            f"eps={self.epsilon} delta={self.delta} calibrated={self._calibrated}>"
        )
