"""
Piecewise LDP mechanism placeholder for bounded scalar inputs.

Responsibilities
  - Provide a compatible LDP mechanism interface for piecewise perturbation.
  - Clip inputs to the interval [-1, 1] before randomization.
  - Emit bounded outputs suitable for downstream aggregation.

Usage Context
  - Use as a stand-in when an approximate piecewise mechanism is acceptable.
  - Intended for normalized scalar inputs in [-1, 1].

Limitations
  - Implements a simplified approximation of the piecewise mechanism.
  - Does not sample from the exact distribution described in the literature.
"""
# 说明：基于 Kairouz 等人的 piecewise 连续型 LDP 机制（近似占位实现），用于对区间内实值数据添加局部噪声。
# 职责：
# - 提供兼容 BaseLDPMechanism 的连续型 LDP 机制骨架
# - 在 [-1, 1] 区间内进行裁剪并注入与 epsilon 相关的均匀噪声
# - 保留序列化与反序列化接口以便与机制注册表和工厂集成

from __future__ import annotations

from typing import Any, Mapping, Optional

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.types import EncodedValue


class PiecewiseMechanism(BaseLDPMechanism):
    """
    Approximate piecewise mechanism for bounded scalar inputs.

    - Configuration
      - epsilon: Privacy budget controlling the perturbation scale.
      - identifier: Optional stable identifier for reports and serialization.
      - rng: Optional random generator used for sampling.
      - name: Optional human-readable name override.

    - Behavior
      - Clips inputs to [-1, 1] and adds scaled uniform noise.
      - Clips the perturbed outputs back to [-1, 1].

    - Usage Notes
      - Inputs should be scaled to [-1, 1] before use.
      - This implementation is an approximation, not the exact piecewise sampler.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化近似 piecewise 机制，仅依赖 epsilon 并沿用基类的 LDP 校验与随机数生成配置
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Clip to [-1, 1], add uniform noise scaled by epsilon, and clip back."""
        # 将输入先投影到 [-1, 1] 区间，然后添加与 epsilon 反比缩放的均匀噪声并再次裁剪
        arr = np.asarray(value, dtype=float)
        clipped = np.clip(arr, -1.0, 1.0)
        noise = self._rng.uniform(-1.0, 1.0, size=clipped.shape)
        # 叠加缩放后的噪声并强制将结果限制在 [-1, 1] 输出域内
        # 防止 epsilon 为 0 导致除零错误，使用 1e-9 作为最小分母
        perturbed = np.clip(clipped + noise / max(self.epsilon, 1e-9), -1.0, 1.0)
        if np.isscalar(value):
            return float(perturbed.item())
        return perturbed

    def serialize(self) -> Mapping[str, Any]:
        # 使用基类序列化逻辑，当前机制自身无额外参数需要持久化
        base = super().serialize()
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "PiecewiseMechanism":
        # 从序列化快照重建机制实例，恢复标识符与 meta 等内部状态
        inst = cls(
            epsilon=float(data["epsilon"]),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
