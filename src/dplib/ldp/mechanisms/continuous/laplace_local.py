"""Local Laplace mechanism for bounded real values under LDP."""
# 说明：在有界区间内为实值数据添加拉普拉斯噪声的本地差分隐私机制。
# 职责：
# - 校验并存储输入裁剪区间 clip_range 与基于 epsilon 的噪声尺度 scale
# - 对输入值进行区间裁剪后添加 Laplace 噪声以实现局部随机化保护，支持标量与数组输入
# - 提供带裁剪区间和 scale 的序列化与反序列化接口以便在不同组件或进程间重建机制配置

from __future__ import annotations

from typing import Any, Mapping, Optional, Tuple, Union

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class LocalLaplaceMechanism(BaseLDPMechanism):
    """Adds Laplace noise to clipped values in [a, b] with scale (b-a)/epsilon."""

    def __init__(
        self,
        epsilon: float,
        *,
        clip_range: Tuple[float, float],
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化局部 Laplace 机制，检查裁剪区间合法性并基于区间宽度和 epsilon 推导噪声尺度
        a, b = clip_range
        if a >= b:
            raise ParamValidationError("clip_range must satisfy a < b")
        self.clip_range = (float(a), float(b))
        self.scale = (self.clip_range[1] - self.clip_range[0]) / float(epsilon)
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)

    def _clip(self, value: EncodedValue) -> EncodedValue:
        # 将输入值裁剪到 [a, b] 区间内以限制局部敏感度并避免极端值放大噪声影响
        return np.clip(value, self.clip_range[0], self.clip_range[1])

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Clip to [a, b] then add Laplace noise with scale (b-a)/epsilon."""
        # 对裁剪后的值添加以 scale 为尺度的零均值 Laplace 噪声，保持与输入相同形状
        clipped = self._clip(value)
        noise = self._rng.laplace(loc=0.0, scale=self.scale, size=None if np.isscalar(clipped) else np.shape(clipped))
        return clipped + noise

    def serialize(self) -> Mapping[str, Any]:
        # 在基类序列化结果基础上附加裁剪区间与当前噪声尺度 scale
        base = super().serialize()
        base.update({"clip_range": self.clip_range, "scale": self.scale})
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "LocalLaplaceMechanism":
        # 从序列化字典重建 LocalLaplaceMechanism 实例并恢复元数据与校准状态
        inst = cls(
            epsilon=float(data["epsilon"]),
            clip_range=tuple(data["clip_range"]),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
