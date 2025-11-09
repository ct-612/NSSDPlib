"""
Generalised Randomised Response mechanism for discrete LDP domains.

Responsibilities:
    * validate arbitrary discrete domains
    * calibrate truthful/non-truthful probabilities from epsilon
    * randomise scalars, Python sequences, and numpy arrays
"""
# 说明：实现通用化随机响应机制，用于离散型本地差分隐私（LDP）域。
# 主要职责：
# 1) 校验任意离散域的合法性
# 2) 根据隐私预算 ε（epsilon）计算“真实响应概率”和“非真实响应概率”
# 3) 对标量、Python 序列以及 NumPy 数组执行随机化操作

from __future__ import annotations
from typing import Sequence, Any, Dict, Optional
import math
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, MechanismError, ValidationError


class GRRMechanism(BaseMechanism):
    """LDP Generalised Randomised Response with arbitrary discrete domain."""

    def __init__(
        self,
        epsilon: float,
        domain: Sequence[Any],
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 校验离散域是否合法（重复、长度等）
        self._validate_domain(domain)
        # 保存域与其大小
        self.domain = list(domain)
        self.k = len(self.domain)
        # 预缓存“非真实值”候选集合映射，加速采样
        self._others_map: Dict[Any, np.ndarray] = {}
        # 调用父类初始化（含 epsilon、RNG、名称）
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        # 机制参数：真实回答概率 p 与非真实回答概率 q
        self.p: Optional[float] = None
        self.q: Optional[float] = None
        # 构建域值缓存映射
        self._build_domain_cache()

    # utils ------------------------------------------------------------------------
    @staticmethod
    def _validate_domain(domain: Sequence[Any]) -> None:
        """Ensure domain configuration is a duplicate-free sequence with >= 2 entries."""
        # 校验输入是否为序列类型
        if not isinstance(domain, Sequence):
            raise ValidationError("GRR domain must be a sequence")
        values = list(domain)
        # 校验域至少包含两个不同值
        if len(values) < 2:
            raise ValidationError("GRR domain must contain at least two values")
        # 校验域内元素不能重复
        if len(set(values)) != len(values):
            raise ValidationError("GRR domain must not contain duplicates")

    def _build_domain_cache(self) -> None:
        """Pre-compute alternatives for each domain value to accelerate sampling."""
        # 预先为每个域值构建对应的“其他值”数组，避免在采样时重复过滤
        self._others_map = {
            value: np.array([v for v in self.domain if v != value], dtype=object)
            for value in self.domain
        }

    # calibration ------------------------------------------------------------------
    def _calibrate_parameters(self, *, sensitivity: Optional[float], **kwargs: Any) -> None:
        """Derive truthful and non-truthful probabilities from epsilon and domain size."""
        # GRR 不依赖敏感度，丢弃相关参数
        del sensitivity, kwargs
        # 域大小校验
        if self.k < 2:
            raise MechanismError("GRR domain size must be >= 2")
        # 根据 epsilon 推导真实响应与非真实响应概率
        exp_eps = math.exp(self.epsilon)
        denom = exp_eps + self.k - 1
        self.p = exp_eps / denom
        self.q = (1.0 - self.p) / (self.k - 1)

    # sampling ---------------------------------------------------------------------
    def _ensure_value_in_domain(self, value: Any) -> None:
        """Validate that the provided value belongs to the discrete domain."""
        # 确认输入值属于定义域，否则抛出错误
        if value not in self._others_map:
            raise MechanismError(f"value {value!r} not contained in GRR domain {self.domain}")

    def _randomise_single(self, value: Any) -> Any:
        """Sample a single noisy response for the provided value."""
        # 校验输入是否在域中
        self._ensure_value_in_domain(value)
        # 按概率 p 保留真实值，否则随机返回其他域值
        if self._rng.random() < self.p:
            return value
        others = self._others_map[value]
        idx = self._rng.integers(0, len(others))
        return others[idx]

    def _randomise_sequence(self, values: Sequence[Any]) -> Sequence[Any]:
        """Apply randomised response independently to every element of the sequence."""
        # 对序列中每个元素独立应用随机化响应
        mapped = [self._randomise_single(v) for v in values]
        # 保持输入类型（list 或 tuple）一致
        return tuple(mapped) if isinstance(values, tuple) else mapped

    def randomise(self, value: Any) -> Any:
        """Add categorical noise to scalars, sequences, or numpy arrays."""
        # 确保机制已校准
        self.require_calibrated()
        # 若输入为 ndarray，则使用 np.vectorize 实现元素级随机化
        if isinstance(value, np.ndarray):
            flat = np.vectorize(self._randomise_single, otypes=[object])(value)
            return flat.reshape(value.shape)
        # 若输入为 list 或 tuple，逐元素处理
        if isinstance(value, (list, tuple)):
            return self._randomise_sequence(value)
        # 若为一般序列类型（排除字符串），按元素随机化
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return [self._randomise_single(v) for v in value]
        # 否则视为单个标量处理
        return self._randomise_single(value)

    # serialization ----------------------------------------------------------------
    @property
    def probabilities(self) -> Dict[str, Optional[float]]:
        """Return the truthful and non-truthful probabilities for inspection."""
        # 返回当前机制的 p 与 q 供外部检查
        return {"truthful": self.p, "other": self.q}

    def serialize(self) -> Dict[str, Any]:
        """Include domain and calibrated probabilities when serialising."""
        # 序列化时包含域及校准参数
        base = super().serialize()
        base.update({"domain": self.domain, "p": self.p, "q": self.q})
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "GRRMechanism":
        """Recreate a mechanism from a serialized snapshot."""
        # 从序列化数据中恢复机制实例
        domain = data.get("domain")
        if domain is None:
            raise ValidationError("serialized GRR mechanism missing 'domain'")
        # 重建机制对象并恢复内部状态
        inst = cls(
            epsilon=data.get("epsilon"),
            domain=domain,
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        inst.p = data.get("p")
        inst.q = data.get("q")
        return inst
