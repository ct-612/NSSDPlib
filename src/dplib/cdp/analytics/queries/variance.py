"""
Privacy-preserving variance query utilities.

Responsibilities
  - Compute variance from noisy sum, sum-of-squares, and count with clipping.
  - Stabilise denominators when noisy counts approach zero.
  - Expose configurable epsilon splits for calibration.

Usage Context
  - Use to release a noisy variance estimate for bounded numeric data.
  - Composes multiple private queries under a shared budget.

Limitations
  - Requires non-empty inputs and finite numeric bounds.
  - Variance estimates are clipped to a feasible upper bound.
"""
# 说明：用于在有界数值范围内基于噪声化 sum/sum-of-squares/count 估计差分隐私方差的查询工具。
# 职责：
# - 通过 PrivateSumQuery 与 PrivateCountQuery 组合实现带裁剪的方差估计
# - 在噪声计数接近零时稳定分母以避免数值爆炸或异常放大
# - 提供可配置的 epsilon 拆分策略并允许外部注入自定义子查询实例

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from dplib.core.privacy.base_mechanism import ValidationError
from dplib.core.utils.param_validation import ensure

from .count import PrivateCountQuery
from .sum import PrivateSumQuery


class PrivateVarianceQuery:
    """
    Release DP protected variance estimates.

    - Configuration
      - epsilon: Total privacy budget for the composed query.
      - bounds: Lower and upper bounds applied to inputs.
      - ddof: Delta degrees of freedom used in variance adjustment.
      - sum_epsilon: Optional budget for the sum query.
      - squares_epsilon: Optional budget for the sum-of-squares query.
      - count_epsilon: Optional budget for the count query.
      - sum_query: Optional preconfigured sum query override.
      - squares_query: Optional preconfigured sum-of-squares query override.
      - count_query: Optional preconfigured count query override.
      - min_count: Lower bound for stabilizing noisy counts.

    - Behavior
      - Clips inputs and combines noisy sums to compute variance.
      - Applies ddof correction and bounds the result.

    - Usage Notes
      - Provide custom queries to control calibration or accounting.
    """

    def __init__(
        self,
        epsilon: float,
        bounds: Tuple[float, float],
        *,
        ddof: int = 1,
        sum_epsilon: Optional[float] = None,
        squares_epsilon: Optional[float] = None,
        count_epsilon: Optional[float] = None,
        sum_query: Optional[PrivateSumQuery] = None,
        squares_query: Optional[PrivateSumQuery] = None,
        count_query: Optional[PrivateCountQuery] = None,
        min_count: float = 1e-6,
    ):
        # 初始化方差查询并对边界、epsilon、ddof 等参数进行校验与归一化
        # 如未显式提供子查询则按 epsilon 等分构造 sum/count/sum-of-squares 三个子查询
        self.lower, self.upper = PrivateSumQuery._validate_bounds(bounds)
        self.epsilon = self._validate_epsilon(epsilon)
        ensure(ddof >= 0, "ddof must be non-negative", error=ValidationError)
        self.ddof = int(ddof)
        self.min_count = float(max(min_count, 1e-12))

        third = self.epsilon / 3.0
        self.sum_query = self._resolve_sum_query(sum_query, sum_epsilon, default_eps=third)
        self.count_query = self._resolve_count_query(count_query, count_epsilon, default_eps=third)
        self.squares_query = self._resolve_squares_query(
            squares_query, squares_epsilon, default_eps=third
        )

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将传入的 epsilon 转为浮点并要求其为正数否则抛出 ValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValidationError("epsilon must be a positive number for variance queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for variance queries", error=ValidationError)
        return numeric

    def _square_bounds(self) -> Tuple[float, float]:
        # 根据原始 bounds 推导平方后的数值区间用于 sum-of-squares 查询裁剪
        lower_sq = 0.0 if self.lower <= 0 <= self.upper else min(self.lower ** 2, self.upper ** 2)
        upper_sq = max(self.lower ** 2, self.upper ** 2)
        return float(lower_sq), float(upper_sq)

    def _resolve_sum_query(
        self,
        query: Optional[PrivateSumQuery],
        sum_epsilon: Optional[float],
        *,
        default_eps: float,
    ) -> PrivateSumQuery:
        # 若外部已提供 sum_query 则直接复用否则基于给定或默认 epsilon 构造
        if query is not None:
            return query
        eps = float(sum_epsilon) if sum_epsilon is not None else default_eps
        ensure(eps > 0, "sum_epsilon must be positive", error=ValidationError)
        return PrivateSumQuery(epsilon=eps, bounds=(self.lower, self.upper))

    def _resolve_squares_query(
        self,
        query: Optional[PrivateSumQuery],
        squares_epsilon: Optional[float],
        *,
        default_eps: float,
    ) -> PrivateSumQuery:
        # 若未提供 squares_query 则在平方后的边界上构造 sum-of-squares 查询实例
        if query is not None:
            return query
        eps = float(squares_epsilon) if squares_epsilon is not None else default_eps
        ensure(eps > 0, "squares_epsilon must be positive", error=ValidationError)
        return PrivateSumQuery(epsilon=eps, bounds=self._square_bounds())

    def _resolve_count_query(
        self,
        query: Optional[PrivateCountQuery],
        count_epsilon: Optional[float],
        *,
        default_eps: float,
    ) -> PrivateCountQuery:
        # 若未提供 count_query 则基于给定或默认 epsilon 构造计数查询
        if query is not None:
            return query
        eps = float(count_epsilon) if count_epsilon is not None else default_eps
        ensure(eps > 0, "count_epsilon must be positive", error=ValidationError)
        return PrivateCountQuery(epsilon=eps)

    @staticmethod
    def _materialize_numeric(values: Any) -> Sequence[float]:
        # 复用求和查询的数值归一化逻辑并确保非空输入
        numeric = PrivateSumQuery._materialize_numeric(values)
        if not numeric:
            raise ValidationError("variance query requires at least one value")
        return numeric

    def _variance_upper_bound(self, mean_estimate: Optional[float] = None) -> float:
        # 利用有界变量的 Bhatia-Davis 上界：Var(X) <= (M-μ)(μ-m)
        span = self.upper - self.lower
        if mean_estimate is None:
            return (span * span) / 4.0
        clipped_mean = float(np.clip(mean_estimate, self.lower, self.upper))
        bound = (self.upper - clipped_mean) * (clipped_mean - self.lower)
        return max(0.0, bound)

    def evaluate(self, values: Iterable[float]) -> float:
        """
        Execute the DP variance query.

        Args:
            values: Iterable numeric data.
        Returns:
            Noisy variance estimate (bounded to feasible range).
        """
        # 先裁剪与平方数据，再分别求 DP sum/sum-of-squares/count 并组合成方差估计
        materialized: List[float] = list(self._materialize_numeric(values))
        clipped = np.clip(np.asarray(materialized, dtype=float), self.lower, self.upper)
        squared = np.square(clipped)

        dp_sum = self.sum_query.evaluate(clipped.tolist())
        dp_sum_squares = self.squares_query.evaluate(squared.tolist())
        dp_count = self.count_query.evaluate(clipped.tolist())

        # 使用 min_count 稳定分母避免在噪声计数接近 0 时方差被放大
        stable_count = max(dp_count, self.min_count)
        mean_estimate = dp_sum / stable_count
        second_moment = dp_sum_squares / stable_count
        raw_variance = max(second_moment - mean_estimate ** 2, 0.0)

        # 应用 ddof 校正样本方差并对最终结果按 Bhatia-Davis 上界进行裁剪
        denominator = max(stable_count - self.ddof, self.min_count)
        adjusted_variance = raw_variance * (stable_count / denominator)
        variance_bound = self._variance_upper_bound(mean_estimate)
        bounded = np.clip(adjusted_variance, 0.0, variance_bound)
        return float(bounded)
