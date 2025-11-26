"""
Staircase mechanism delivering pure differential privacy with discrete noise.

Responsibilities:
    * calibrate staircase parameters from epsilon, sensitivity, and gamma
    * sample symmetric staircase noise with geometric tails and fractional offsets
    * maintain serialization hooks for reproducibility
"""
# 说明：阶梯机制实现。
# 职责：
# - 基于 epsilon、sensitivity 与 gamma 标定阶梯分布
# - 生成具有几何尾部与分段偏移的对称噪声
# - 支持序列化/反序列化，便于重现

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from dplib.core.privacy.base_mechanism import BaseMechanism, CalibrationError, MechanismError, ValidationError


class StaircaseMechanism(BaseMechanism):
    """Pure-DP staircase mechanism."""

    def __init__(
        self,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
        gamma: float = 0.5,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化阶梯机制：设置 ε / 敏感度 / γ，并为后续校准的 decay / success_prob 预留状态
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)
        self._validate_gamma(gamma)
        self.sensitivity = float(sensitivity)
        self.gamma = float(gamma)
        self.decay: Optional[float] = None
        self.success_prob: Optional[float] = None

    @staticmethod
    def _validate_gamma(gamma: float) -> None:
        # 校验 γ 合法性：必须为数值且位于 [0, 1] 区间
        if not isinstance(gamma, (float, int)):
            raise ValidationError("gamma must be numeric")
        if gamma < 0.0 or gamma > 1.0:
            raise ValidationError("gamma must be in [0, 1]")

    # pylint: disable=arguments-differ
    def _calibrate_parameters(
        self,
        *,
        sensitivity: Optional[float],
        gamma: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        # 依据 ε、敏感度与（可选）γ 计算几何衰减因子与成功概率，并在 meta 中标记分布
        del kwargs
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
            self.sensitivity = float(sensitivity)
        if gamma is not None:
            self._validate_gamma(gamma)
            self.gamma = float(gamma)
        rate = self.epsilon / self.sensitivity
        self.decay = math.exp(-rate)
        self.success_prob = 1.0 - self.decay
        if not (0.0 < self.success_prob < 1.0):
            raise MechanismError("invalid calibration for staircase mechanism")
        self._meta["distribution"] = "staircase"

    def _sample_noise(self, size: Optional[tuple[int, ...]]) -> np.ndarray:
        # 生成阶梯噪声：几何步长 + 以 γ 概率添加偏移，再乘以随机符号与敏感度
        """Sample staircase noise with optional fractional offset gamma."""
        if self.success_prob is None or self.decay is None:
            raise CalibrationError("staircase mechanism not calibrated")
        # 几何步长 + 以 gamma 概率添加偏移，形成阶梯状分布
        magnitude = self._rng.geometric(self.success_prob, size=size) - 1
        offset_mask = self._rng.random(size=size) < self.gamma
        offset = np.where(offset_mask, self.gamma, 0.0)
        sign = self._rng.integers(0, 2, size=size)
        sign = np.where(sign == 0, -1.0, 1.0)
        return sign * (magnitude + offset) * self.sensitivity

    def randomise(self, value: Any) -> Any:
        # 对输入值添加阶梯分布噪声，并通过 _restore_numeric_like 保持标量/数组语义
        """Add staircase-distributed noise to numeric inputs."""
        self.require_calibrated()
        arr, was_scalar = self._coerce_numeric(value)
        size = None if was_scalar else arr.shape
        noise = self._sample_noise(size)
        result = arr + noise
        return self._restore_numeric_like(value, result, was_scalar)

    def serialize(self) -> Dict[str, Any]:
        # 在基类序列化结果基础上附加敏感度、γ 与校准参数，便于重建机制
        base = super().serialize()
        base.update(
            {
                "sensitivity": self.sensitivity,
                "gamma": self.gamma,
                "decay": self.decay,
                "success_prob": self.success_prob,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "StaircaseMechanism":
        # 从序列化字典恢复阶梯机制，包括校准状态与噪声参数
        inst = cls(
            epsilon=data.get("epsilon"),
            sensitivity=data.get("sensitivity", 1.0),
            gamma=data.get("gamma", 0.5),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.decay = data.get("decay")
        inst.success_prob = data.get("success_prob")
        return inst
