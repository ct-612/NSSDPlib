"""
Optimal Unary Encoding (OUE) mechanism for categorical LDP domains.

Responsibilities:
    * validate discrete domains and cache index lookups
    * calibrate OUE Bernoulli parameters from epsilon
    * randomise scalars, Python sequences, and numpy arrays into unary vectors
"""
# 说明：实现最优一元编码（OUE）的本地差分隐私机制。
# 职责：
# - 校验离散域并建立值→索引缓存
# - 依据 ε 标定两类伯努利参数 p/q（真位与非真位置 1 的概率）
# - 将标量/序列/NumPy 数组随机化为一元向量表示（0/1）

from __future__ import annotations
from typing import Sequence, Any, Dict, Optional
import math
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, MechanismError, ValidationError


class OUEMechanism(BaseMechanism):
    """Optimal Unary Encoding LDP mechanism."""
    # OUE 将类别编码为长度 k 的一元向量。对真位以概率 p 置 1，对其他位以概率 q 置 1。

    def __init__(
        self,
        epsilon: float,
        domain: Sequence[Any],
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 构造时先校验域，再缓存域与索引，加速后续查找
        self._validate_domain(domain)
        self.domain = list(domain)                     # 规范化为 list，保持可序列化
        self.k = len(self.domain)                      # 域大小 k
        self._index: Dict[Any, int] = {value: idx for idx, value in enumerate(self.domain)}  # 值→索引映射
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        self.p: Optional[float] = None                 # 真位置 1 的概率（校准后设定）
        self.q: Optional[float] = None                 # 非真位置 1 的概率（校准后设定）

    # utils ------------------------------------------------------------------------
    @staticmethod
    def _validate_domain(domain: Sequence[Any]) -> None:
        """Ensure the domain is a duplicate-free sequence with >= 2 values."""
        # 要求：是序列；元素数≥2；无重复
        if not isinstance(domain, Sequence):
            raise ValidationError("OUE domain must be a sequence")
        values = list(domain)
        if len(values) < 2:
            raise ValidationError("OUE domain must contain at least two values")
        if len(set(values)) != len(values):
            raise ValidationError("OUE domain must not contain duplicates")

    # calibration ------------------------------------------------------------------
    def _calibrate_parameters(self, *, sensitivity: Optional[float], **kwargs: Any) -> None:
        """Derive true/false Bernoulli probabilities according to OUE."""
        # OUE 经典设定：p = 1/2，q = 1/(e^ε + 1)
        # 注：sensitivity 对 OUE 无直接作用，丢弃
        del sensitivity, kwargs
        if self.k < 2:
            raise MechanismError("OUE domain size must be >= 2")
        exp_eps = math.exp(self.epsilon)
        self.p = 0.5
        self.q = 1.0 / (exp_eps + 1.0)

    # sampling ---------------------------------------------------------------------
    def _ensure_value_in_domain(self, value: Any) -> None:
        # 确认输入值属于定义域，否则抛出错误
        if value not in self._index:
            raise MechanismError(f"value {value!r} not contained in OUE domain {self.domain}")
    
    def _randomise_single(self, value: Any) -> np.ndarray:
        # 单值随机化：生成长度 k 的一元向量，真位使用 p，其他位使用 q 采样伯努利
        self._ensure_value_in_domain(value)
        if self.p is None or self.q is None:
            raise MechanismError("OUE mechanism not calibrated; call calibrate()")
        idx = self._index[value]                       # 真位索引
        probs = np.full(self.k, self.q, dtype=float)   # 初始化所有位的置 1 概率为 q
        probs[idx] = self.p                            # 真位使用 p
        draws = self._rng.random(self.k)               # 生成 [0,1) 独立均匀样本
        return (draws < probs).astype(np.int8)         # 比较后得到 0/1，使用紧凑 int8

    def _randomise_sequence(self, values: Sequence[Any]) -> np.ndarray:
        # 序列随机化：逐元素调用 _randomise_single 并在第 0 维堆叠
        if len(values) == 0:
            return np.empty((0, self.k), dtype=np.int8)
        encoded = [self._randomise_single(v) for v in values]
        return np.stack(encoded, axis=0)

    def _randomise_ndarray(self, arr: np.ndarray) -> np.ndarray:
        # NumPy 数组随机化：扁平化→逐元素编码→再按原形状在末维扩展为 (…, k)
        if arr.size == 0:
            return np.empty(arr.shape + (self.k,), dtype=np.int8)
        flat = arr.reshape(-1)
        encoded = [self._randomise_single(v) for v in flat]
        stacked = np.stack(encoded, axis=0)
        return stacked.reshape(arr.shape + (self.k,))

    def randomise(self, value: Any) -> Any:
        """Randomise scalars, python sequences, or numpy arrays via unary encoding."""
        # 入口：根据输入类型分发到对应实现；在使用前确保已校准
        self.require_calibrated()
        if isinstance(value, np.ndarray):
            return self._randomise_ndarray(value)
        if isinstance(value, (list, tuple)):
            return self._randomise_sequence(value)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return self._randomise_sequence(list(value))
        return self._randomise_single(value)

    # serialization ----------------------------------------------------------------
    @property
    def probabilities(self) -> Dict[str, Optional[float]]:
        """Expose Bernoulli parameters for inspection."""
        # 暴露当前 p/q，便于测试或监控
        return {"true_bit_one": self.p, "other_bit_one": self.q}

    def serialize(self) -> Dict[str, Any]:
        # 在基类元数据基础上，保存域与 p/q 以支持往返复现
        base = super().serialize()
        base.update({"domain": self.domain, "p": self.p, "q": self.q})
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "OUEMechanism":
        # 反序列化：恢复域、p/q、元数据与校准标志；RNG 不跨环境恢复
        domain = data.get("domain")
        if domain is None:
            raise ValidationError("serialized OUE mechanism missing 'domain'")
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
