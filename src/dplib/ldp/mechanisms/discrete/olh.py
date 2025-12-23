"""
Optimized local hashing mechanism for categorical domains under LDP.

Responsibilities
  - Hash categorical indices into a smaller hash range.
  - Apply randomized response in hash space using epsilon.
  - Expose configuration needed to reproduce hash mapping.

Usage Context
  - Use when the original categorical domain is large.
  - Intended for local perturbation with hash-based aggregation.

Limitations
  - Hash collisions are inherent and can affect estimation.
  - Requires a fixed domain size and hash range configuration.
"""
# 说明：实现基于优化局部哈希（OLH）的本地差分隐私机制，在哈希空间中执行 GRR 式扰动。
# 职责：
# - 基于给定离散域大小与哈希范围构造单个哈希函数并映射类别索引
# - 按 epsilon 校准哈希空间内真实哈希值与非真实哈希值的响应概率 p/q
# - 提供输入合法性校验、随机化输出以及序列化/反序列化机制配置的能力

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.ldp_utils import make_hash_family
from dplib.ldp.types import EncodedValue
from dplib.core.utils.param_validation import ParamValidationError


class OLHMechanism(BaseLDPMechanism):
    """
    Optimized local hashing with GRR-style perturbation in hash space.

    - Configuration
      - epsilon: Privacy budget for randomized response in hash space.
      - domain_size: Size of the original categorical domain.
      - hash_range: Size of the hash domain.
      - hash_seed: Seed used to derive the hash function.
      - identifier: Optional stable identifier for reports and serialization.
      - rng: Optional random generator used for sampling.
      - name: Optional human-readable name override.

    - Behavior
      - Hashes input indices into the hash range.
      - Returns the hashed value with probability p, otherwise a random alternative.

    - Usage Notes
      - Inputs must be integer indices in the range [0, domain_size).
      - The hash range must be greater than 1.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        domain_size: int,
        hash_range: int,
        hash_seed: int = 0,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化 OLH 机制并检查 domain_size 与 hash_range 等核心参数的合法性
        if domain_size < 2:
            raise ParamValidationError("domain_size must be at least 2")
        if hash_range <= 1:
            raise ParamValidationError("hash_range must be greater than 1")

        self.domain_size = int(domain_size)
        self.hash_range = int(hash_range)
        self.hash_seed = int(hash_seed)
        self._hash_fn = make_hash_family(1, self.hash_range, self.hash_seed)[0]

        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)

        exp_eps = math.exp(self.epsilon)
        denom = exp_eps + self.hash_range - 1
        self.p: float = exp_eps / denom
        self.q: float = 1.0 / denom

    def _validate_value(self, value: EncodedValue) -> int:
        # 校验输入值是否为合法的整数类别索引并返回规范化后的 int
        if not isinstance(value, (int, np.integer)):
            raise ParamValidationError("value must be an integer category index")
        if value < 0 or value >= self.domain_size:
            raise ParamValidationError("value out of domain range")
        return value

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Hash the value and apply GRR in the hash range."""
        # 将类别索引映射到哈希空间并按 p/q 规则在 hash_range 内执行 GRR 式随机响应
        v = self._validate_value(value)
        hashed = self._hash_fn(str(v))

        if self._rng.random() < self.p:
            return hashed

        alt = int(self._rng.integers(0, self.hash_range - 1))
        if alt >= hashed:
            alt += 1
        return alt

    def serialize(self) -> Dict[str, Any]:
        # 将 OLH 机制配置与核心参数导出为可序列化字典，便于重建机制实例
        base = super().serialize()
        base.update(
            {
                "domain_size": self.domain_size,
                "hash_range": self.hash_range,
                "hash_seed": self.hash_seed,
                "p": self.p,
                "q": self.q,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "OLHMechanism":
        # 从序列化字典中还原 OLH 机制实例，并恢复元数据与校准标记
        inst = cls(
            epsilon=float(data["epsilon"]),
            domain_size=int(data["domain_size"]),
            hash_range=int(data["hash_range"]),
            hash_seed=int(data.get("hash_seed", 0)),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
