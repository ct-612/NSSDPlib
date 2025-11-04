# src\dplib\cdp\mechanisms\gaussian.py
from __future__ import annotations
import numpy as np
from typing import Optional
from dplib.core.privacy.base_mechanism import BaseMechanism, MechanismError


class GaussianMechanism(BaseMechanism):
    """
    - 这是一个用于 (ε, δ) 差分隐私的高斯噪声机制。

    - 噪声标准差公式:
        - sigma = sensitivity * sqrt(2 * ln(1.25/delta)) / epsilon

    - 注意：
        - 此校准公式要求 delta 必须大于 0 
        - 该类遵循 BaseMechanism 约定：在调用 randomise() 前需先调用 calibrate() 
    """

    def __init__(
        self,
        epsilon: float = 1.0,
        delta: float = 1e-5,
        sensitivity: float = 1.0,
        rng: Optional[np.random.Generator] = None,
    ):
        # let BaseMechanism validate epsilon/delta and set RNG
        super().__init__(epsilon=epsilon, delta=delta, rng=rng)

        if sensitivity <= 0:
            raise MechanismError("Sensitivity must be positive")
        if delta < 0:
            raise MechanismError("Delta must be non-negative")

        self.sensitivity = sensitivity
        self.delta = float(delta)
        self.sigma: Optional[float] = None

    def calibrate(self, sensitivity: Optional[float] = None, delta: Optional[float] = None):
        """
        - 校准函数：
            - 可选覆盖 sensitivity 或 delta
            - 计算噪声标准差 sigma
        - 目的是在使用 randomise() 前准备机制参数。
        """
        if sensitivity is not None:
            if sensitivity <= 0:
                raise MechanismError("Sensitivity must be positive")
            self.sensitivity = sensitivity

        if delta is not None:
            if delta < 0:
                raise MechanismError("Delta must be non-negative")
            self.delta = float(delta)

        if self.delta <= 0:
            raise MechanismError("delta must be > 0 for Gaussian calibration")

        # common (non-tight) formula for (epsilon, delta)-DP Gaussian noise
        self.sigma = self.sensitivity * np.sqrt(2.0 * np.log(1.25 / self.delta)) / self.epsilon
        self._calibrated = True

    def randomise(self, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise MechanismError("Value must be numeric")
        self.require_calibrated()
        noise = self._rng.normal(0.0, self.sigma)
        return float(value + noise)

    def serialize(self) -> dict:
        base = super().serialize()
        base.update({"mechanism": "gaussian", "sensitivity": self.sensitivity, "delta": self.delta, "sigma": self.sigma})
        return base

    @classmethod
    def deserialize(cls, data: dict) -> "GaussianMechanism":
        eps = data.get("epsilon")
        delta = data.get("delta", 1e-5)
        sensitivity = data.get("sensitivity", 1.0)
        inst = cls(epsilon=eps, delta=delta, sensitivity=sensitivity)
        # restore meta and calibrated flag; sigma may be present
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.sigma = data.get("sigma", inst.sigma)
        return inst
