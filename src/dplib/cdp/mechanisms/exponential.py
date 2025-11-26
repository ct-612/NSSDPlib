"""
Exponential mechanism for pure differential privacy.

Responsibilities:
    * sample outputs proportionally to exp(epsilon * utility / (2 * sensitivity))
    * support pre-computed utility scores or on-the-fly scoring functions
    * persist recent sampling metadata for auditability
"""
# 说明：指数机制实现。
# 职责：
# - 根据 exp(ε·utility/(2Δ)) 生成输出采样分布
# - 支持预先给出的效用分数或基于 utility_fn 的即时计算
# - 序列化时保留候选集与最近一次采样概率，便于审计与测试

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from dplib.core.privacy.base_mechanism import BaseMechanism, CalibrationError, ValidationError
from dplib.core.utils.math_utils import softmax

UtilityFn = Callable[[Any, Any], float]


class ExponentialMechanism(BaseMechanism):
    """Pure-DP exponential mechanism."""

    def __init__(
        self,
        epsilon: float = 1.0,
        sensitivity: float = 1.0,
        *,
        candidates: Optional[Sequence[Any]] = None,
        utility_fn: Optional[UtilityFn] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 初始化指数机制：设置 ε、全局敏感度、默认候选集及效用函数，并准备审计字段
        super().__init__(epsilon=epsilon, rng=rng, name=name)
        self._validate_sensitivity(sensitivity)
        self.sensitivity = float(sensitivity)
        self.utility_fn = utility_fn
        self.default_candidates: Optional[Tuple[Any, ...]] = tuple(candidates) if candidates else None
        self._last_candidates: Optional[Tuple[Any, ...]] = None
        self._last_probabilities: Optional[np.ndarray] = None

    # pylint: disable=arguments-differ
    def _calibrate_parameters(
        self,
        *,
        sensitivity: Optional[float],
        candidates: Optional[Sequence[Any]] = None,
        **kwargs: Any,
    ) -> None:
        # 内部参数校准：可动态更新敏感度和默认候选集，并在 meta 中标记分布类型
        """Update sensitivity and optional default candidate set."""
        del kwargs
        if sensitivity is not None:
            self._validate_sensitivity(sensitivity)
            self.sensitivity = float(sensitivity)
        if candidates is not None:
            candidate_tuple = tuple(candidates)
            if not candidate_tuple:
                raise ValidationError("candidates must be a non-empty sequence")
            self.default_candidates = candidate_tuple
        if self.default_candidates is not None and len(self.default_candidates) == 0:
            raise ValidationError("candidates must be a non-empty sequence")
        self._meta["distribution"] = "exponential"

    def _resolve_candidates_and_scores(
        self,
        value: Any,
        *,
        candidates: Optional[Sequence[Any]],
        scores: Optional[Sequence[float]],
    ) -> Tuple[Tuple[Any, ...], np.ndarray]:
        # 统一解析“候选集 + 分数”输入形式：支持显式 scores、映射、(候选, 分数) 对或 utility_fn
        if scores is not None:
            candidate_source = candidates or self.default_candidates
            if candidate_source is None:
                raise ValidationError("candidates must be provided when passing scores")
            candidate_tuple = tuple(candidate_source)
            if not candidate_tuple:
                raise ValidationError("candidates must be non-empty")
            score_arr = np.asarray(scores, dtype=float)
            if score_arr.shape[0] != len(candidate_tuple):
                raise ValidationError("scores length must match candidates length")
            return candidate_tuple, score_arr

        if isinstance(value, Mapping):
            candidate_tuple = tuple(value.keys())
            if not candidate_tuple:
                raise ValidationError("utility mapping must be non-empty")
            score_arr = np.asarray(list(value.values()), dtype=float)
            return candidate_tuple, score_arr

        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) == 2 and isinstance(value[0], Sequence) and not isinstance(value[0], (str, bytes)):
                candidate_tuple = tuple(value[0])
                score_arr = np.asarray(value[1], dtype=float)
                if len(candidate_tuple) == 0:
                    raise ValidationError("candidates must be non-empty")
                if score_arr.shape[0] != len(candidate_tuple):
                    raise ValidationError("scores length must match candidates length")
                return candidate_tuple, score_arr
            if value and isinstance(value[0], tuple) and len(value[0]) == 2:
                candidate_tuple = tuple(item[0] for item in value)
                score_arr = np.asarray([item[1] for item in value], dtype=float)
                return candidate_tuple, score_arr

        if self.utility_fn is not None:
            candidate_source = candidates or self.default_candidates
            if candidate_source is None:
                raise ValidationError("candidates must be provided when using a utility function")
            candidate_tuple = tuple(candidate_source)
            if not candidate_tuple:
                raise ValidationError("candidates must be non-empty")
            score_arr = np.asarray([float(self.utility_fn(value, cand)) for cand in candidate_tuple], dtype=float)
            return candidate_tuple, score_arr

        raise ValidationError("value must provide candidate utilities via mapping, pairs, or utility_fn")

    def randomise(
        self,
        value: Any,
        *,
        candidates: Optional[Sequence[Any]] = None,
        scores: Optional[Sequence[float]] = None,
    ) -> Any:
        # 指数机制核心接口：根据效用分数构造软最大分布并按概率采样候选
        """Sample a candidate proportional to the exponentiated utility score."""
        self.require_calibrated()
        candidates_tuple, score_arr = self._resolve_candidates_and_scores(
            value,
            candidates=candidates,
            scores=scores,
        )
        if score_arr.size == 0:
            raise CalibrationError("no utility scores available for sampling")

        beta = self.epsilon / (2.0 * self.sensitivity)
        logits = beta * score_arr
        probs = softmax(logits)
        probs = probs / probs.sum()
        chosen = int(self._rng.choice(len(candidates_tuple), p=probs))

        # 保留最近一次采样的候选集与概率向量，方便调试与审计
        self._last_candidates = candidates_tuple
        self._last_probabilities = probs
        return candidates_tuple[chosen]

    def serialize(self) -> Dict[str, Any]:
        # 序列化时在基类基础上附加敏感度、默认候选集、最近候选集与最近概率向量
        """Include sensitivity and recent sampling metadata."""
        base = super().serialize()
        base.update(
            {
                "sensitivity": self.sensitivity,
                "default_candidates": list(self.default_candidates) if self.default_candidates is not None else None,
                "last_candidates": list(self._last_candidates) if self._last_candidates is not None else None,
                "last_probabilities": None
                if self._last_probabilities is None
                else self._last_probabilities.tolist(),
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "ExponentialMechanism":
        # 反序列化：恢复参数配置、校准状态以及最近一次采样的审计信息
        inst = cls(
            epsilon=data.get("epsilon"),
            sensitivity=data.get("sensitivity", 1.0),
            candidates=data.get("default_candidates"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        last_candidates = data.get("last_candidates")
        inst._last_candidates = tuple(last_candidates) if last_candidates else None
        last_probs = data.get("last_probabilities")
        inst._last_probabilities = None if last_probs is None else np.asarray(last_probs, dtype=float)
        return inst
