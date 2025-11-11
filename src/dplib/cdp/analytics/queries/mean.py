"""
Privacy-preserving MEAN query utilities.

Responsibilities:
    * reuse DP sum/count queries with configurable budget splits
    * clip numeric data to user-provided bounds before aggregation
    * stabilise outputs when noisy counts approach zero
"""
# 说明：差分隐私均值查询工具。
# 职责：
# - 复用 DP 的 sum/count 查询，并允许 ε 在两者之间按比例拆分（默认各 1/2）
# - 在聚合前对数据按用户给定区间进行裁剪（clip），保证全局敏感度有限
# - 当噪声化的计数接近 0 时，通过最小计数阈值稳定输出，避免除零或爆炸值

from __future__ import annotations
from typing import Iterable, Optional, Sequence, Tuple, Any
import numpy as np
from dplib.core.privacy.base_mechanism import ValidationError
from .sum import PrivateSumQuery
from .count import PrivateCountQuery


class PrivateMeanQuery:
    """Release DP protected means via calibrated sum/count queries."""
    # 先计算 DP 和（受 bounds 限制）与 DP 计数，再用它们的比值作为 DP 均值估计。

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
        # 初始化：校验并拆解边界，校验 ε，设置最小计数阈值。
        # 若未注入现成查询器，则按给定或默认 ε 切分创建 DP 和/计数查询器。
        self.lower, self.upper = self._validate_bounds(bounds)
        self._validate_epsilon(epsilon)
        self.epsilon = float(epsilon)
        self.min_count = float(max(min_count, 1e-12))  # 防御式下界，避免 0 或负值
        self.sum_query = self._resolve_sum_query(sum_query, sum_epsilon)
        self.count_query = self._resolve_count_query(count_query, count_epsilon)

    @staticmethod
    def _validate_bounds(bounds: Tuple[float, float]) -> Tuple[float, float]:
        # 边界必须是 (lower, upper) 且 lower < upper，用于限制输入与最终输出范围
        if (
            not isinstance(bounds, (tuple, list))
            or len(bounds) != 2
        ):
            raise ValidationError("bounds must be a (lower, upper) pair for mean queries")
        lower, upper = float(bounds[0]), float(bounds[1])
        if lower >= upper:
            raise ValidationError("mean query bounds must satisfy lower < upper")
        return lower, upper

    @staticmethod
    def _validate_epsilon(epsilon: float) -> None:
        # ε 必须为正
        if epsilon is None or float(epsilon) <= 0:
            raise ValidationError("epsilon must be a positive number for mean queries")

    def _resolve_sum_query(
        self,
        query: Optional[PrivateSumQuery],
        sum_epsilon: Optional[float],
    ) -> PrivateSumQuery:
        # 求和查询解析：优先使用注入的 query；否则以 sum_epsilon 或 ε/2 实例化 PrivateSumQuery
        if query is not None:
            return query
        eps = float(sum_epsilon) if sum_epsilon is not None else self.epsilon / 2.0
        if eps <= 0:
            raise ValidationError("sum_epsilon must be positive")
        return PrivateSumQuery(epsilon=eps, bounds=(self.lower, self.upper))

    def _resolve_count_query(
        self,
        query: Optional[PrivateCountQuery],
        count_epsilon: Optional[float],
    ) -> PrivateCountQuery:
        # 计数查询解析：同上，使用 count_epsilon 或 ε/2
        if query is not None:
            return query
        eps = float(count_epsilon) if count_epsilon is not None else self.epsilon / 2.0
        if eps <= 0:
            raise ValidationError("count_epsilon must be positive")
        return PrivateCountQuery(epsilon=eps)

    @staticmethod
    def _to_numpy(values: Any) -> np.ndarray:
        # 将输入转为 float 型 ndarray；拒绝字符串；支持任意可迭代转数组
        if isinstance(values, (str, bytes)):
            raise ValidationError("mean query input must be numeric and non-string")
        if isinstance(values, np.ndarray):
            return values.astype(float)
        if isinstance(values, Sequence):
            return np.asarray(values, dtype=float)
        try:
            return np.asarray(list(values), dtype=float)
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValidationError("mean query input must be numeric iterable") from exc

    def evaluate(self, values: Iterable[float]) -> float:
        """
        Execute the DP mean query.

        Args:
            values: Iterable numeric data.
        Returns:
            Noisy, clipped mean estimate.
        """
        # 流程：
        # 1) 转换为 ndarray，为空则报错；
        # 2) 用 DP 和查询（内部执行裁剪与加噪）得到 dp_sum；
        # 3) 用 DP 计数查询得到 dp_count，并与 min_count 取 max 以稳定；
        # 4) 计算均值并将结果裁剪回 [lower, upper] 区间。
        arr = self._to_numpy(values)
        if arr.size == 0:
            raise ValidationError("mean query requires at least one value")

        dp_sum = self.sum_query.evaluate(arr)
        dp_count = self.count_query.evaluate(arr)
        stable_count = max(dp_count, self.min_count)
        mean_estimate = dp_sum / stable_count
        return float(np.clip(mean_estimate, self.lower, self.upper))
