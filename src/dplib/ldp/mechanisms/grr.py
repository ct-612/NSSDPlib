# src\dplib\ldp\mechanisms\grr.py
from __future__ import annotations
from typing import Sequence, Any, Dict, Optional
import numpy as np
from dplib.core.privacy.base_mechanism import BaseMechanism, MechanismError, ValidationError

class GRRMechanism(BaseMechanism):
	"""
	Generalized Randomized Response (GRR) for discrete domain LDP.
	- domain: 离散值列表（如 ["A", "B", "C"] 或 [0,1,2]）
	- epsilon: 隐私预算
	- 支持 serialize/deserialize
	"""
	def __init__(self, epsilon: float, domain: Sequence[Any], rng: Optional[Any] = None, name: Optional[str] = None):
		if not isinstance(domain, (list, tuple)) or len(domain) < 2:
			raise ValidationError("GRR domain must be a list/tuple with >=2 elements")
		self.domain = list(domain)
		self.k = len(self.domain)
		super().__init__(epsilon=epsilon, rng=rng, name=name)
		self.p: Optional[float] = None
		self.q: Optional[float] = None

	def calibrate(self, sensitivity: float = None, **kwargs) -> None:
		# GRR不需要sensitivity，直接用epsilon和k
		if self.k < 2:
			raise MechanismError("GRR domain size must be >=2")
		self.p = np.exp(self.epsilon) / (np.exp(self.epsilon) + self.k - 1)
		self.q = 1.0 / (np.exp(self.epsilon) + self.k - 1)
		self._calibrated = True

	def randomise(self, value: Any) -> Any:
		self.require_calibrated()
		if value not in self.domain:
			raise MechanismError(f"Value {value} not in GRR domain {self.domain}")
		# 按概率p保留原值，按概率q随机选其他值
		if self._rng.random() < self.p:
			return value
		else:
			# 随机选一个非原值
			others = [v for v in self.domain if v != value]
			return self._rng.choice(others)

	def serialize(self) -> Dict[str, Any]:
		base = super().serialize()
		base.update({"mechanism": "grr", "domain": self.domain, "p": self.p, "q": self.q})
		return base

	@classmethod
	def deserialize(cls, data: Dict[str, Any]) -> "GRRMechanism":
		eps = data.get("epsilon")
		domain = data.get("domain")
		inst = cls(epsilon=eps, domain=domain)
		# restore meta and calibrated flag;
		inst._meta = dict(data.get("meta", {}))
		inst._calibrated = bool(data.get("calibrated", False))
		inst.p = data.get("p", None)
		inst.q = data.get("q", None)
		return inst
