# src\dplib\cdp\mechanisms\laplace.py
from __future__ import annotations
import math
from typing import Sequence, Any, Dict, Optional
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, MechanismError


class LaplaceMechanism(BaseMechanism):
    """
    - Laplace机制，用于差分隐私。
    """

    def __init__(self, epsilon: float = 1.0, sensitivity: float = 1.0, rng: np.random.Generator | None = None):
        super().__init__(epsilon=epsilon, rng=rng)
        if epsilon <= 0:
            raise MechanismError("Epsilon must be positive")
        if sensitivity <= 0:
            raise MechanismError("Sensitivity must be positive")
        self.epsilon = epsilon
        self.sensitivity = sensitivity
        self._rng = rng or np.random.default_rng()

    def calibrate(self, sensitivity: float):
        if sensitivity <= 0:
            raise MechanismError("Sensitivity must be positive")
        self.sensitivity = sensitivity
        self._calibrated = True

    def randomise(self, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise MechanismError("Value must be numeric")
        self.require_calibrated()
        scale = self.sensitivity / self.epsilon
        noise = self._rng.laplace(0.0, scale)
        return value + noise

    def serialize(self) -> Dict[str, Any]:
        """- 返回可序列化的配置"""
        base = super().serialize()
        base.update({"mechanism": "laplace", "epsilon": self.epsilon, "sensitivity": self.sensitivity})
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> LaplaceMechanism:
        eps = data.get("epsilon")
        sensitivity = data.get("sensitivity")
        inst = cls(epsilon=eps, sensitivity=sensitivity)
        # restore meta and calibrated flag;
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))    
        return inst