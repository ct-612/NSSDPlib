"""
Gaussian mechanism for approximate differential privacy.

Responsibilities:
    * calibrate sigma from epsilon, delta, and sensitivity
    * add Gaussian noise to scalars and arrays
    * persist calibration metadata for reproducibility
"""
# 说明：实现近似差分隐私 (ε, δ)-DP 的高斯机制。
# 职责：
# - 基于 epsilon、delta、sensitivity 标定噪声标准差 sigma
# - 对标量与数组逐元素加入独立同分布高斯噪声
# - 持久化校准元数据以确保可复现

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from dplib.core.privacy.base_mechanism import (
    BaseMechanism,
    CalibrationError,
    ValidationError,
)
from dplib.core.utils.random import sample_noise


class GaussianMechanism(BaseMechanism):
    """Gaussian mechanism with the common 1.25 calibration constant."""

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        sensitivity: float = 1.0,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化公共参数并注入 RNG 与可选名称
        super().__init__(epsilon=epsilon, delta=delta, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)
        if delta <= 0:
            raise ValidationError("delta must be strictly positive for Gaussian mechanism")
        self.sensitivity = float(sensitivity)
        self.delta = float(delta)
        self.sigma: Optional[float] = None

    def _calibrate_parameters(
        self,
        *,
        sensitivity: Optional[float],
        delta: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        """Update sensitivity/delta as needed and compute sigma for the noise."""
        # 该方法由基类 calibrate() 调用，执行具体校准逻辑
        del kwargs  # 忽略未使用的可变参数
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
            self.sensitivity = float(sensitivity)  # 若传入新敏感度则更新
        if delta is not None:
            self._validate_delta(delta)  # 使用基类校验 δ∈[0,∞)
            self.delta = float(delta)
        if self.delta <= 0 or self.delta >= 1:
            # 二次防御：高斯机制要求 δ 位于 (0,1)
            raise ValidationError("delta must be in (0,1) for Gaussian calibration")
        # 计算高斯噪声标准差 σ，采用常用校准常数 1.25
        # σ = (Δf * sqrt(2 * ln(1.25/δ))) / ε
        self.sigma = self.sensitivity * math.sqrt(2.0 * math.log(1.25 / self.delta)) / self.epsilon
        self._meta["distribution"] = "gaussian"

    def randomise(self, value: Any) -> Any:
        """Inject i.i.d. Gaussian noise into scalars, vectors, or numpy arrays."""
        # 加噪入口：确保校准完成并按输入形状采样 i.i.d. 高斯噪声后相加
        self.require_calibrated()  # 未校准将抛出异常
        if self.sigma is None:
            # 防御式：理论上 require_calibrated 后应已有 sigma
            raise CalibrationError("Gaussian mechanism missing sigma; call calibrate()")
        arr, was_scalar = self._coerce_numeric(value)  # 统一为 ndarray，并记录是否原为标量
        # 标量输入 -> size=None 采样一个数；数组输入 -> 与形状一致逐元素采样
        size = None if was_scalar else arr.shape
        noise = sample_noise(self._rng, "gaussian", scale=self.sigma, size=size)
        result = arr + noise
        return self._restore_numeric_like(value, result, was_scalar)  # 还原为与原输入等价的标量/数组类型

    def serialize(self) -> Dict[str, Any]:
        """Capture Gaussian-specific parameters for reproducibility."""
        # 在基类序列化结果上，补充高斯机制特有参数，便于跨进程复现
        base = super().serialize()
        base.update({"sensitivity": self.sensitivity, "delta": self.delta, "sigma": self.sigma})
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "GaussianMechanism":
        """Reinstantiate a Gaussian mechanism, including prior calibration metadata."""
        # 根据保存的数据重建实例；rng 明确置为 None，避免跨环境 RNG 状态不一致
        inst = cls(
            epsilon=data.get("epsilon"),
            delta=data.get("delta", 1e-5),
            sensitivity=data.get("sensitivity", 1.0),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.sigma = data.get("sigma")
        return inst
