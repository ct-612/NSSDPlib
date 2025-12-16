"""Generalised Randomised Response (k-ary GRR) for LDP."""
# 说明：实现 k 元广义随机响应（GRR）的本地差分隐私机制，用于离散类别数据扰动。
# 职责：
# - 支持基于显式类别集合或 domain_size 的有限离散域建模
# - 按给定 epsilon 预计算真实值与非真实值的响应概率 prob_true/prob_false
# - 提供值到索引及索引到值的双向映射、随机化输出和序列化/反序列化能力

from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import numpy as np

from dplib.ldp.mechanisms.base import BaseLDPMechanism
from dplib.ldp.types import EncodedValue


class GRRMechanism(BaseLDPMechanism):
    """k-ary Generalised Randomised Response mechanism."""

    def __init__(
        self,
        epsilon: float,
        *,
        categories: Optional[Sequence[Any]] = None,
        domain_size: Optional[int] = None,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 根据给定类别集合或离散域大小初始化 GRR 机制并检查参数合法性
        if categories is None and domain_size is None:
            raise ValueError("either categories or domain_size must be provided")
        if categories is not None and domain_size is not None:
            raise ValueError("provide either categories or domain_size, not both")

        self._categories: Optional[Sequence[Any]] = tuple(categories) if categories is not None else None
        self._index_map: Optional[Dict[Any, int]] = None
        if self._categories is not None:
            if len(self._categories) == 0:
                raise ValueError("categories must be non-empty")
            self._index_map = {value: idx for idx, value in enumerate(self._categories)}
            self._k = len(self._categories)
        else:
            if domain_size is None or domain_size <= 0:
                raise ValueError("domain_size must be positive")
            self._k = int(domain_size)

        if self._k <= 1:
            raise ValueError("domain must contain at least two categories")

        super().__init__(epsilon=epsilon, delta=0.0, identifier=identifier, rng=rng, name=name)

        exp_eps = math.exp(self.epsilon)
        denom = exp_eps + self._k - 1
        self.prob_true: float = exp_eps / denom
        self.prob_false: float = 1.0 / denom

    def _to_index(self, value: EncodedValue) -> int:
        # 将原始值映射为离散域中的整数索引并进行合法性检查
        if self._categories is None:
            if not isinstance(value, (int, np.integer)):
                raise ValueError("value must be an integer index within domain")
            idx = int(value)
        else:
            if value not in self._index_map:  # type: ignore[arg-type]
                raise ValueError("value not in configured categories")
            idx = self._index_map[value]  # type: ignore[index]

        if idx < 0 or idx >= self._k:
            raise ValueError("value index out of domain range")
        return idx

    def _from_index(self, idx: int) -> Any:
        # 将域内索引恢复为对应的类别值
        if self._categories is None:
            return idx
        return self._categories[idx]

    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Apply GRR to the provided categorical value."""
        # 按 GRR 规则对给定类别值进行随机响应，以 prob_true 返回真实值，否则返回其他类别
        idx = self._to_index(value)
        if self._rng.random() < self.prob_true:
            return self._from_index(idx)

        alt = int(self._rng.integers(0, self._k - 1))
        if alt >= idx:
            alt += 1
        return self._from_index(alt)

    @property
    def domain_size(self) -> int:
        # 返回 GRR 机制所作用的离散域大小 k
        return self._k

    def serialize(self) -> Dict[str, Any]:
        # 将当前 GRR 机制状态序列化为字典，便于持久化或跨进程传输
        base = super().serialize()
        base.update(
            {
                "categories": list(self._categories) if self._categories is not None else None,
                "domain_size": self._k,
                "prob_true": self.prob_true,
                "prob_false": self.prob_false,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "GRRMechanism":
        # 从序列化字典重建 GRR 实例，并恢复元信息与校准状态
        categories = data.get("categories")
        domain_size = data.get("domain_size")
        inst = cls(
            epsilon=float(data["epsilon"]),
            categories=categories,
            domain_size=domain_size if categories is None else None,
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
