"""
Optimized unary encoding mechanism for bit-vector inputs under LDP.

Responsibilities
  - Configure unary randomized response probabilities based on epsilon.
  - Randomize each bit independently according to OUE parameters.
  - Preserve input container type when returning perturbed output.

Usage Context
  - Use for bit-vector reports such as unary-encoded categories.
  - Intended for local perturbation of vectorized discrete data.

Limitations
  - Assumes input values are binary indicators.
  - Does not enforce a specific vector length.
"""
# 说明：实现基于优化一元编码（OUE）的本地差分隐私机制，对比特向量执行独立随机翻转以满足 LDP 约束。
# 职责：
# - 基于 epsilon 或显式给定参数配置 OUE 的 p/q 概率
# - 支持在 numpy 数组、bitarray 与普通序列之间进行统一的比特向量转换与封装
# - 提供对输入比特向量的逐位随机化以及机制状态的序列化与反序列化

from __future__ import annotations

import math
from typing import Any, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.ldp_utils import ensure_probability, make_bitarray
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class OUEMechanism(BaseLDPMechanism):
    """
    Optimized unary encoding for independent bit perturbation.

    - Configuration
      - epsilon: Privacy budget used to derive default probabilities.
      - p: Optional probability to keep a 1 as 1.
      - q: Optional probability to flip a 0 to 1.
      - identifier: Optional stable identifier for reports and serialization.
      - rng: Optional random generator used for sampling.
      - name: Optional human-readable name override.

    - Behavior
      - Flips each input bit independently using p and q.
      - Supports numpy arrays, bitarray-like objects, and Python sequences.

    - Usage Notes
      - When p or q are not provided, defaults are derived from epsilon.
      - Input values should be 0/1 indicators.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        p: Optional[float] = None,
        q: Optional[float] = None,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化 OUE 机制并根据 epsilon 或显式参数确定正位/负位翻转概率 p 和 q
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)
        default_q = 1.0 / (math.exp(self.epsilon) + 1.0)
        self.p: float = 0.5 if p is None else float(p)
        self.q: float = default_q if q is None else float(q)
        ensure_probability(self.p, name="p")
        ensure_probability(self.q, name="q")

    def _to_list(self, bits: EncodedValue) -> Sequence[int]:
        # 将各类比特向量表示统一转换为简单的 0/1 列表供内部随机化逻辑使用
        if isinstance(bits, np.ndarray):
            return bits.astype(int).flatten().tolist()
        if isinstance(bits, (list, tuple)):
            return list(bits)
        try:
            # 对 bitarray 类型调用 tolist() 以获取 Python 原生列表
            return bits.tolist()  # type: ignore[call-arg,attr-defined]
        except Exception as exc:
            raise ParamValidationError("bits must be a sequence or array-like of 0/1") from exc

    def _wrap(self, original: EncodedValue, values: Sequence[int]) -> EncodedValue:
        # 根据原始输入类型将随机化后的比特结果包装回 numpy/bitarray/列表等相同外形
        if isinstance(original, np.ndarray):
            arr = np.asarray(values, dtype=original.dtype if hasattr(original, "dtype") else int)
            return arr.reshape(original.shape)
        if hasattr(original, "tolist") and not isinstance(original, (list, tuple)):
            # 对 bitarray 类实现根据置 1 索引重建新的 bitarray
            ones = [idx for idx, v in enumerate(values) if v]
            return make_bitarray(len(values), ones)
        return list(values)

    def randomise(self, bits: EncodedValue) -> EncodedValue:
        """Independent bit flips using OUE parameters."""
        # 依据 OUE 的 p/q 概率独立地对输入比特向量的每一位执行随机翻转
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
        # 将 OUE 机制的核心参数与状态导出为可序列化字典
        base = super().serialize()
        base.update({"p": self.p, "q": self.q})
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "OUEMechanism":
        # 从字典配置中重建 OUE 机制实例并恢复元数据与校准标记
        inst = cls(
            epsilon=float(data["epsilon"]),
            p=data.get("p"),
            q=data.get("q"),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
