"""
Vector-valued mechanism applying element-wise noise.

Responsibilities:
    * calibrate per-dimension noise using L1/L2 sensitivity
    * support Laplace (pure DP) or Gaussian (approximate DP) noise
    * preserve input shape for numpy arrays and Python sequences
"""
# 说明：向量值机制。
# 职责：
# - 基于 L1/L2 敏感度逐元素校准噪声
# - 支持 Laplace（纯 DP）与 Gaussian（近似 DP）两种分布
# - 保持输入形状与容器类型

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from dplib.core.privacy.base_mechanism import BaseMechanism, CalibrationError, MechanismError, ValidationError
from dplib.core.utils.random import sample_noise


class VectorMechanism(BaseMechanism):
    """Vector-valued mechanism with configurable noise distribution."""

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        sensitivity: float = 1.0,
        *,
        distribution: str = "gaussian",
        norm: str = "l2",
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化向量机制：设置 ε/δ、敏感度以及噪声分布与范数类型，并预留标定参数 scale/sigma
        super().__init__(epsilon=epsilon, delta=delta, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)
        self.sensitivity = float(sensitivity)
        self.distribution = distribution.lower()
        self.norm = norm.lower()
        self.scale: Optional[float] = None
        self.sigma: Optional[float] = None
        self._validate_configuration()

    def _validate_configuration(self) -> None:
        # 校验配置合法性：分布必须是 laplace/gaussian，范数必须是 l1/l2
        if self.distribution not in {"laplace", "gaussian"}:
            raise ValidationError("distribution must be 'laplace' or 'gaussian'")
        if self.norm not in {"l1", "l2"}:
            raise ValidationError("norm must be 'l1' or 'l2'")

    # pylint: disable=arguments-differ
    def _calibrate_parameters(
        self,
        *,
        sensitivity: Optional[float],
        delta: Optional[float] = None,
        distribution: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # 根据更新后的敏感度/δ/分布类型计算噪声幅度：Laplace 使用 scale，Gaussian 使用 sigma
        del kwargs
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
            self.sensitivity = float(sensitivity)
        if distribution is not None:
            self.distribution = distribution.lower()
        if delta is not None:
            self._validate_delta(delta)
            self.delta = float(delta)

        self._validate_configuration()

        if self.distribution == "laplace":
            self.scale = self.sensitivity / self.epsilon
            self.sigma = None
        else:
            if self.delta <= 0 or self.delta >= 1:
                raise MechanismError("delta must be in (0,1) for Gaussian vector mechanism")
            self.sigma = self.sensitivity * math.sqrt(2.0 * math.log(1.25 / self.delta)) / self.epsilon
            self.scale = None
        self._meta["distribution"] = self.distribution
        self._meta["norm"] = self.norm

    def randomise(self, value: Any) -> Any:
        # 对输入每个坐标添加独立噪声（Laplace 或 Gaussian），并保持标量/数组/序列的形状与类型
        """Add independent noise to each coordinate."""
        self.require_calibrated()
        arr, was_scalar = self._coerce_numeric(value)
        size = None if was_scalar else arr.shape
        if self.distribution == "laplace":
            if self.scale is None:
                raise CalibrationError("Vector mechanism missing Laplace scale; call calibrate()")
            noise = sample_noise(self._rng, "laplace", scale=self.scale, size=size)
        else:
            if self.sigma is None:
                raise CalibrationError("Vector mechanism missing Gaussian sigma; call calibrate()")
            noise = sample_noise(self._rng, "gaussian", scale=self.sigma, size=size)
        result = arr + noise
        return self._restore_numeric_like(value, result, was_scalar)

    def serialize(self) -> Dict[str, Any]:
        # 在基类序列化结果上补充向量机制特有的敏感度、分布、范数及标定参数
        base = super().serialize()
        base.update(
            {
                "sensitivity": self.sensitivity,
                "distribution": self.distribution,
                "norm": self.norm,
                "scale": self.scale,
                "sigma": self.sigma,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "VectorMechanism":
        # 从字典中重建向量机制实例并恢复标定状态与噪声幅度参数
        inst = cls(
            epsilon=data.get("epsilon"),
            delta=data.get("delta", 1e-5),
            sensitivity=data.get("sensitivity", 1.0),
            distribution=data.get("distribution", "gaussian"),
            norm=data.get("norm", "l2"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.scale = data.get("scale")
        inst.sigma = data.get("sigma")
        return inst
