"""
Two-sided geometric mechanism for integer-valued queries.

Responsibilities:
    * calibrate discrete noise using epsilon and global sensitivity
    * add symmetric geometric noise to scalars or arrays while preserving shape
    * support serialization of calibration metadata
"""
# 说明：几何机制（离散拉普拉斯）。
# 职责：
# - 用 epsilon 和 sensitivity 标定衰减系数，生成对称几何噪声
# - 兼容标量、序列与 ndarray，加噪后保持形状
# - 序列化/反序列化校准元数据，便于重现

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from dplib.core.privacy.base_mechanism import BaseMechanism, CalibrationError, MechanismError


class GeometricMechanism(BaseMechanism):
    """Pure-DP geometric (discrete Laplace) mechanism."""

    def __init__(
        self,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化几何机制：设置 ε、全局敏感度，并准备校准后衰减系数、成功概率等内部状态
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)
        self.sensitivity = float(sensitivity)
        self.decay: Optional[float] = None
        self.success_prob: Optional[float] = None

    # pylint: disable=arguments-differ
    def _calibrate_parameters(self, *, sensitivity: Optional[float], **kwargs: Any) -> None:
        # 依据 ε 与（可选）敏感度计算几何噪声的衰减因子与成功概率，并写入元数据
        """Calibrate geometric noise decay from epsilon and sensitivity."""
        del kwargs
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
            self.sensitivity = float(sensitivity)
        rate = self.epsilon / self.sensitivity
        self.decay = math.exp(-rate)
        self.success_prob = 1.0 - self.decay
        if not (0.0 < self.success_prob < 1.0):
            raise MechanismError("invalid calibration for geometric mechanism")
        self._meta["distribution"] = "geometric"

    def _integer_preserving_restore(self, original: Any, value: np.ndarray, was_scalar: bool) -> Any:
        # 在恢复输出类型时尽量保持原始整数 dtype（数组/列表/元组/标量），避免因噪声导致类型退化
        """Restore output type while preserving integer dtype when possible."""
        original_dtype = None
        if not isinstance(original, (str, bytes)):
            try:
                original_dtype = np.asarray(original).dtype
            except Exception:  # pragma: no cover - defensive
                original_dtype = None

        restored = self._restore_numeric_like(original, value, was_scalar)
        if original_dtype is not None and np.issubdtype(original_dtype, np.integer):
            if isinstance(restored, np.ndarray):
                return np.rint(restored).astype(original_dtype)
            if isinstance(restored, list):
                return [int(round(x)) for x in restored]
            if isinstance(restored, tuple):
                return tuple(int(round(x)) for x in restored)
            if isinstance(restored, float):
                return int(round(restored))
        return restored

    def randomise(self, value: Any) -> Any:
        # 对输入添加对称几何噪声；要求机制已校准且成功概率已设置
        """Add symmetric geometric noise to the input."""
        self.require_calibrated()
        if self.success_prob is None:
            raise CalibrationError("Geometric mechanism not calibrated; missing success probability")

        arr, was_scalar = self._coerce_numeric(value)
        size = None if was_scalar else arr.shape
        magnitude = self._rng.geometric(self.success_prob, size=size) - 1
        sign = self._rng.integers(0, 2, size=size)
        sign = np.where(sign == 0, -1, 1)
        noise = sign * magnitude
        result = arr + noise
        return self._integer_preserving_restore(value, result, was_scalar)

    def serialize(self) -> Dict[str, Any]:
        # 在基类序列化结果基础上附加敏感度与几何噪声参数，便于重建机制
        base = super().serialize()
        base.update(
            {
                "sensitivity": self.sensitivity,
                "decay": self.decay,
                "success_prob": self.success_prob,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "GeometricMechanism":
        # 从序列化字典中恢复几何机制实例及其校准状态与参数
        inst = cls(
            epsilon=data.get("epsilon"),
            sensitivity=data.get("sensitivity", 1.0),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.decay = data.get("decay")
        inst.success_prob = data.get("success_prob")
        return inst
