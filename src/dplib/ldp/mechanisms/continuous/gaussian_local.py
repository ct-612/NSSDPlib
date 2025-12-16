"""Local Gaussian mechanism for bounded real values under LDP."""
# 说明：实现对有界实值数据添加高斯噪声的本地差分隐私机制。
# 职责：
# - 校验并存储输入的裁剪区间 clip_range 以及满足 (epsilon, delta)-DP 的噪声尺度 sigma
# - 在裁剪后的值上添加零均值高斯噪声，统一支持标量与 numpy 数组等多种输入形态
# - 提供包含裁剪区间和 sigma 的序列化/反序列化接口，便于跨组件共享机制配置

from __future__ import annotations

import math
from typing import Any, Mapping, Optional, Tuple

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class LocalGaussianMechanism(BaseLDPMechanism):
    """
    Adds Gaussian noise to clipped values in [a, b] to satisfy (epsilon, delta)-differential privacy.

    The amount of noise (sigma) is calibrated using the standard formula for the Gaussian mechanism,
    requiring both epsilon and delta to be specified.
    """

    def __init__(
        self,
        epsilon: float,
        delta: float,
        *,
        clip_range: Tuple[float, float],
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化本地高斯机制，检查参数合法性并计算满足(epsilon, delta)-DP的噪声标准差sigma
        a, b = clip_range
        if a >= b:
            raise ParamValidationError("clip_range must satisfy a < b")
        if not (0 < delta < 1):
            raise ParamValidationError("delta must be in the range (0, 1)")

        self.clip_range = (float(a), float(b))
        
        # 使用校准后的公式计算sigma，以满足(epsilon, delta)-DP
        sensitivity = self.clip_range[1] - self.clip_range[0]
        self.sigma = (sensitivity * math.sqrt(2 * math.log(1.25 / delta))) / max(epsilon, 1e-9)
        super().__init__(epsilon=epsilon, delta=delta, identifier=identifier, rng=rng, name=name)

    def _clip(self, value: EncodedValue) -> EncodedValue:
        # 将输入值裁剪到 [a, b] 区间内以控制数值范围并避免极端值放大噪声影响
        return np.clip(value, self.clip_range[0], self.clip_range[1])

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Clip to [a, b] then add calibrated Gaussian noise."""
        # 在裁剪后的值上按设定的 sigma 添加零均值高斯噪声，标量和数组输入均按形状生成噪声
        clipped = self._clip(value)
        noise = self._rng.normal(loc=0.0, scale=self.sigma, size=None if np.isscalar(clipped) else np.shape(clipped))
        return clipped + noise

    def serialize(self) -> Mapping[str, Any]:
        # 在基类序列化结果的基础上附加裁剪区间与 sigma 参数
        base = super().serialize()
        base.update({"clip_range": self.clip_range, "sigma": self.sigma})
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "LocalGaussianMechanism":
        # 从序列化字典重建 LocalGaussianMechanism 实例，并恢复元数据与校准状态标记
        inst = cls(
            epsilon=float(data["epsilon"]),
            delta=float(data.get("delta", 0.0)),
            clip_range=tuple(data["clip_range"]),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
