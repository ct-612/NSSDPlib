"""
Privacy-preserving MEAN query utilities.

Responsibilities
  - Reuse DP sum/count queries with configurable budget splits.
  - Clip numeric data to user-provided bounds before aggregation.
  - Stabilise outputs when noisy counts approach zero.

Usage Context
  - Use to release a noisy mean for bounded numeric data.
  - Composes private sum and count queries under a shared budget.

Limitations
  - Requires non-empty inputs and finite numeric bounds.
  - Mean estimates are clipped to the provided bounds.
"""
# 说明：通过复用差分隐私的求和与计数查询在有界数值范围内释放带噪声的均值估计。
# 职责：
# - 接收用户提供的数值边界并在聚合前对原始数据进行裁剪以保证有限敏感度
# - 支持在总 epsilon 下对 sum/count 进行可配置的预算拆分或复用外部子查询
# - 在计数噪声接近零时通过最小计数阈值稳定输出避免数值发散

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence, Tuple

import numpy as np

from dplib.core.privacy.base_mechanism import ValidationError
from dplib.core.utils.param_validation import ensure

from .count import PrivateCountQuery
from .sum import PrivateSumQuery


class PrivateMeanQuery:
    """
    Release DP protected means via calibrated sum/count queries.

    - Configuration
      - epsilon: Total privacy budget for the composed query.
      - bounds: Lower and upper bounds applied to inputs.
      - sum_epsilon: Optional budget for the sum query.
      - count_epsilon: Optional budget for the count query.
      - sum_query: Optional preconfigured sum query override.
      - count_query: Optional preconfigured count query override.
      - min_count: Lower bound for stabilizing noisy counts.

    - Behavior
      - Clips inputs to bounds, then combines noisy sum and count.
      - Stabilizes the denominator and clips the mean to bounds.

    - Usage Notes
      - Provide custom queries to control calibration or accounting.
    """

    def __init__(
        self,
        epsilon: float,
        bounds: Tuple[float, float],
        *,
        sum_epsilon: Optional[float] = None,
        count_epsilon: Optional[float] = None,
        sum_query: Optional[PrivateSumQuery] = None,
        count_query: Optional[PrivateCountQuery] = None,
        min_count: float = 1e-6,
    ):
        # 初始化 DP 均值查询并校验 epsilon 与边界等基础配置
        # 依据总 epsilon 或显式拆分构造 sum 与 count 子查询并设置最小计数下界
        self.lower, self.upper = PrivateSumQuery._validate_bounds(bounds)
        self.epsilon = self._validate_epsilon(epsilon)
        self.min_count = float(max(min_count, 1e-12))
        self.sum_query = self._resolve_sum_query(sum_query, sum_epsilon)
        self.count_query = self._resolve_count_query(count_query, count_epsilon)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将传入的 epsilon 转为浮点并要求其为正数否则抛出 ValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("epsilon must be a positive number for mean queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for mean queries", error=ValidationError)
        return numeric

    def _resolve_sum_query(
        self,
        query: Optional[PrivateSumQuery],
        sum_epsilon: Optional[float],
    ) -> PrivateSumQuery:
        # 若未提供外部 sum_query 则根据拆分的 sum_epsilon 构造带界求和查询
        if query is not None:
            return query
        eps = float(sum_epsilon) if sum_epsilon is not None else self.epsilon / 2.0
        ensure(eps > 0, "sum_epsilon must be positive", error=ValidationError)
        return PrivateSumQuery(epsilon=eps, bounds=(self.lower, self.upper))

    def _resolve_count_query(
        self,
        query: Optional[PrivateCountQuery],
        count_epsilon: Optional[float],
    ) -> PrivateCountQuery:
        # 若未提供外部 count_query 则根据拆分的 count_epsilon 构造计数查询
        if query is not None:
            return query
        eps = float(count_epsilon) if count_epsilon is not None else self.epsilon / 2.0
        ensure(eps > 0, "count_epsilon must be positive", error=ValidationError)
        return PrivateCountQuery(epsilon=eps)

    @staticmethod
    def _materialize_numeric(values: Any) -> Sequence[float]:
        # 复用求和查询的数值归一化逻辑并确保非空输入
        numeric = PrivateSumQuery._materialize_numeric(values)
        if not numeric:
            raise ValidationError("mean query requires at least one value")
        return numeric

    def evaluate(self, values: Iterable[float]) -> float:
        """
        Execute the DP mean query.

        Args:
            values: Iterable numeric data.
        Returns:
            Noisy, clipped mean estimate.
        """
        # 裁剪数据然后通过 DP sum 与 DP count 组合得到均值估计
        materialized = list(self._materialize_numeric(values))
        clipped = np.clip(np.asarray(materialized, dtype=float), self.lower, self.upper).tolist()

        dp_sum = self.sum_query.evaluate(clipped)
        dp_count = self.count_query.evaluate(clipped)
        # 使用 min_count 稳定分母避免噪声计数接近 0 时导致均值发散
        stable_count = max(dp_count, self.min_count)
        mean_estimate = dp_sum / stable_count
        # 将均值估计限制在原始边界范围之内以提升结果可解释性与鲁棒性
        bounded = np.clip(mean_estimate, self.lower, self.upper)
        return float(bounded)
