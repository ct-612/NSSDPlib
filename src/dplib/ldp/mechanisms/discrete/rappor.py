"""RAPPOR mechanism for LDP (simplified single-stage reporting)."""
# 说明：实现简化单阶段 RAPPOR 本地差分隐私机制，对比特向量执行按位二元随机响应。
# 职责：
# - 基于 epsilon 或显式给定参数配置 RAPPOR 的 p/q 概率
# - 支持在 numpy 数组、bitarray 与普通序列之间进行统一的比特向量表示转换
# - 提供按位随机响应与机制状态序列化/反序列化能力，便于聚合端重建配置

from __future__ import annotations

import math
from typing import Any, List, Mapping, Optional, Sequence

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.ldp_utils import ensure_probability, make_bitarray
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class RAPPORMechanism(BaseLDPMechanism):
    """
    Simplified RAPPOR-style bit flipping.

    Uses binary randomized response per bit with parameters (p, q):
      - bit=1 -> report 1 w.p. p
      - bit=0 -> report 1 w.p. q
    Defaults choose the symmetric RR instantiation derived from epsilon.
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
        # 初始化 RAPPOR 机制并根据 epsilon 或显式给定值推导每位为 1 的报告概率 p/q
        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)
        exp_eps = math.exp(self.epsilon)
        default_p = exp_eps / (exp_eps + 1.0)
        default_q = 1.0 / (exp_eps + 1.0)
        self.p: float = default_p if p is None else float(p)
        self.q: float = default_q if q is None else float(q)
        ensure_probability(self.p, name="p")
        ensure_probability(self.q, name="q")

    def _to_list(self, bits: EncodedValue) -> Sequence[int]:
        # 将多种比特容器统一转换为 0/1 列表，方便内部循环与随机数生成
        if isinstance(bits, np.ndarray):
            return bits.astype(int).flatten().tolist()
        if isinstance(bits, (list, tuple)):
            return list(bits)
        try:
            return bits.tolist()  # type: ignore[attr-defined]
        except Exception as exc:
            raise ParamValidationError("bits must be a sequence or array-like of 0/1") from exc

    def _wrap(self, original: EncodedValue, values: Sequence[int]) -> EncodedValue:
        # 根据原始输入类型将随机化后的比特序列还原为相同形状和容器类型
        if isinstance(original, np.ndarray):
            arr = np.asarray(values, dtype=original.dtype if hasattr(original, "dtype") else int)
            return arr.reshape(original.shape)
        if hasattr(original, "tolist") and not isinstance(original, (list, tuple)):
            ones = [idx for idx, v in enumerate(values) if v]
            return make_bitarray(len(values), ones)
        return list(values)

    def randomise(self, bits: EncodedValue) -> EncodedValue:
        """Apply per-bit binary RR according to RAPPOR parameters."""
        # 使用 RAPPOR 的 p/q 参数对每一位独立执行二元随机响应
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
        # 将当前机制配置与 p/q 参数导出为字典，支持持久化与跨进程传输
        base = super().serialize()
        base.update({"p": self.p, "q": self.q})
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "RAPPORMechanism":
        # 从序列化字典重建 RAPPOR 实例，并恢复元数据与校准状态标记
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
