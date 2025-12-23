"""
Generic bit-vector randomized response for LDP.

Responsibilities
  - Apply independent bit flips using provided p and q probabilities.
  - Support common bit-vector container types.
  - Expose configuration via serialization helpers.

Usage Context
  - Use as a general-purpose bit-vector mechanism when p and q are chosen externally.
  - Intended for local perturbation of binary indicator vectors.

Limitations
  - Requires explicit p and q parameters.
  - Assumes input values are binary indicators.
"""
# 说明：为本地差分隐私场景提供通用一元随机响应机制的实现。
# 职责：
# - 基于给定的 p/q 参数对比特向量执行逐位随机响应
# - 支持 numpy 数组、bitarray 与普通序列等多种比特表示之间的转换与封装
# - 提供机制参数的合法性校验以及序列化/反序列化以便在客户端与聚合端之间传递配置

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.ldp_utils import ensure_probability, make_bitarray
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class UnaryRandomizer(BaseLDPMechanism):
    """
    Bit-wise randomized response parameterized by p and q.

    - Configuration
      - epsilon: Privacy budget for record keeping in reports.
      - p: Probability to keep a 1 as 1.
      - q: Probability to flip a 0 to 1.
      - identifier: Optional stable identifier for reports and serialization.
      - rng: Optional random generator used for sampling.
      - name: Optional human-readable name override.

    - Behavior
      - Applies independent randomized response to each bit.
      - Supports numpy arrays, bitarray-like objects, and Python sequences.

    - Usage Notes
      - p and q must be valid probabilities in [0, 1].
      - Input values should be 0/1 indicators.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        p: float,
        q: float,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化通用比特随机响应机制，记录 p/q 并校验概率参数范围
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)
        self.p = float(p)
        self.q = float(q)
        ensure_probability(self.p, name="p")
        ensure_probability(self.q, name="q")

    def _to_list(self, bits: EncodedValue) -> Sequence[int]:
        # 将输入比特容器统一转换为扁平的 0/1 列表以便内部随机化处理
        if isinstance(bits, np.ndarray):
            return bits.astype(int).flatten().tolist()
        if isinstance(bits, (list, tuple)):
            return list(bits)
        try:
            return bits.tolist()  # type: ignore[attr-defined]
        except Exception as exc:
            raise ParamValidationError("bits must be a sequence or array-like of 0/1") from exc

    def _wrap(self, original: EncodedValue, values: Sequence[int]) -> EncodedValue:
        # 按照原始输入类型与形状将随机化后的比特结果重新封装返回
        if isinstance(original, np.ndarray):
            arr = np.asarray(values, dtype=original.dtype if hasattr(original, "dtype") else int)
            return arr.reshape(original.shape)
        if hasattr(original, "tolist") and not isinstance(original, (list, tuple)):
            ones = [idx for idx, v in enumerate(values) if v]
            return make_bitarray(len(values), ones)
        return list(values)

    def randomise(self, bits: EncodedValue) -> EncodedValue:
        """Independent bit flips following p/q randomized response."""
        # 对输入比特向量的每一位按照 p/q 规则独立执行随机响应
        bit_list = self._to_list(bits)
        rand = self._rng.random(len(bit_list))
        result: List[int] = []
        for v, r in zip(bit_list, rand):
            if v:
                result.append(1 if r < self.p else 0)
            else:
                result.append(1 if r < self.q else 0)
        return self._wrap(bits, result)

    def serialize(self) -> dict[str, Any]:
        # 导出机制的基础配置与 p/q 参数，生成可序列化的字典表示
        base = super().serialize()
        base.update({"p": self.p, "q": self.q})
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "UnaryRandomizer":
        # 从字典配置重建 UnaryRandomizer 实例，并恢复元数据与校准状态
        inst = cls(
            epsilon=float(data["epsilon"]),
            p=float(data["p"]),
            q=float(data["q"]),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
