"""
Duchi mechanism for bounded scalar inputs under LDP.

Responsibilities
  - Clip inputs to the interval [-1, 1].
  - Randomize outputs to either -1 or 1 with input-dependent probabilities.
  - Support scalar and array-valued inputs.

Usage Context
  - Use for normalized real values in the range [-1, 1].
  - Intended for local perturbation with binary outputs.

Limitations
  - Outputs are restricted to -1 or 1.
  - Inputs outside [-1, 1] are clipped.
"""
# 说明：在区间 [-1, 1] 上对标量或数组输入应用 Duchi 等人提出的本地差分隐私机制，将值编码为 ±1。
# 职责：
# - 按 Duchi 机制公式将输入 x ∈ [-1, 1] 映射为输出为 ±1 的线性概率分布
# - 对输入进行 [-1, 1] 裁剪并同时支持标量与 numpy 数组形式的批量处理
# - 复用基类的序列化/反序列化与元数据机制以便在不同组件之间传递配置

from __future__ import annotations

import math
from typing import Any, Mapping, Optional

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.types import EncodedValue


class DuchiMechanism(BaseLDPMechanism):
    """
    Duchi mechanism for scalar inputs mapped to {-1, 1}.

    - Configuration
      - epsilon: Privacy budget controlling the output probabilities.
      - identifier: Optional stable identifier for reports and serialization.
      - rng: Optional random generator used for sampling.
      - name: Optional human-readable name override.

    - Behavior
      - Clips inputs to [-1, 1] and samples outputs in {-1, 1}.
      - Uses probabilities linear in the clipped input value.

    - Usage Notes
      - Inputs should be scaled to [-1, 1] before use.
      - Supports both scalar values and numpy arrays.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化 Duchi 机制并缓存 exp(epsilon)，后续概率计算时避免重复开销
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)
        self._exp_eps = math.exp(self.epsilon)

    def _clip(self, value: EncodedValue) -> EncodedValue:
        # 将输入值裁剪到 [-1, 1] 区间以满足 Duchi 机制的理论前提
        return np.clip(value, -1.0, 1.0)

    def _p_positive(self, x: float) -> float:
        # 来源于标准 Duchi 机制的概率公式推导
        return (self._exp_eps * (1 + x) + (1 - x)) / (2 * (self._exp_eps + 1))

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Output ±1 according to probability linear in clipped x."""
        # 基于裁剪后的 x 计算输出为 +1 的概率并对标量或数组进行符号随机采样
        clipped = self._clip(value)
        if np.isscalar(clipped):
            p = self._p_positive(float(clipped))
            return 1.0 if self._rng.random() < p else -1.0
        clipped_arr = np.asarray(clipped, dtype=float)
        probs = np.vectorize(self._p_positive, otypes=[float])(clipped_arr)
        draws = self._rng.random(size=clipped_arr.shape)
        return np.where(draws < probs, 1.0, -1.0)

    def serialize(self) -> Mapping[str, Any]:
        # 直接复用基类序列化逻辑，当前机制无额外可序列化参数
        base = super().serialize()
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "DuchiMechanism":
        # 从序列化数据恢复 DuchiMechanism 实例，并同步内部元数据与校准标记
        inst = cls(
            epsilon=float(data["epsilon"]),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
