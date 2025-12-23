"""
Post-processing utilities to enforce basic consistency on vector-like estimates.

Responsibilities
  - Provide non-negativity, normalization, and simplex projection helpers.
  - Offer monotonicity enforcement for ordered estimates.
  - Wrap aggregators to post-process selected metric outputs.

Usage Context
  - Use to post-process vector estimates such as frequencies.
  - Intended for consistency fixes that do not change privacy guarantees.

Limitations
  - Only applies to numpy array outputs for selected metrics.
  - Post-processing is configuration-driven and does not infer constraints.
"""
# 说明：提供针对向量型估计输出的后处理工具与聚合器包装器，用于在不影响隐私保证的前提下修正数值不一致问题。
# 职责：
# - 提供非负裁剪、归一化、simplex 投影与单调性约束等基础向量后处理函数
# - 封装任意 BaseAggregator 实例，并按 apply_to_metrics 对指定 metric 输出进行一致性修正
# - 在元数据中记录各类后处理开关与参数便于调试和下游分析

from __future__ import annotations

from typing import Any, Mapping, Sequence, Optional

import numpy as np

from .base import BaseAggregator, StatelessAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


def enforce_non_negative(probs: np.ndarray) -> np.ndarray:
    """Clip probabilities to be non-negative."""
    # 将输入概率向量转换为浮点数组并对所有分量做下限裁剪以避免出现负值
    arr = np.asarray(probs, dtype=float)
    return np.clip(arr, 0.0, None)


def normalize_probabilities(probs: np.ndarray) -> np.ndarray:
    """
    Normalize to sum to 1 when possible; fall back to uniform if total is zero.
    """
    # 在总和大于 0 时按总和做归一化，若总和为 0 则退化为各分量相等的均匀分布
    arr = np.asarray(probs, dtype=float)
    total = float(arr.sum())
    if total > 0:
        return arr / total
    if arr.size == 0:
        return arr
    return np.full_like(arr, 1.0 / arr.size, dtype=float)


def project_simplex(
    probs: np.ndarray,
    *,
    target_sum: float = 1.0,
    axis: Optional[int] = None,
    clip_tolerance: float = 0.0,
) -> np.ndarray:
    """
    Project vector onto probability simplex (non-negative, sum=target_sum) using
    the algorithm from Duchi et al. (2008). Supports batch projection via `axis`.

    Args:
        probs: input array.
        target_sum: desired sum after projection (default 1.0).
        axis: if not None, project along this axis independently.
        clip_tolerance: pre-clip small negatives to 0 when within tolerance to reduce
            floating point artifacts before projection.
    """
    # 使用 Duchi 等人的投影算法将向量或批量向量投影到给定和的概率单纯形上

    def _project(vec: np.ndarray) -> np.ndarray:
        v = vec.astype(float, copy=True)
        if clip_tolerance > 0:
            v[v > -clip_tolerance] = np.maximum(v[v > -clip_tolerance], 0.0)
        if v.size == 0:
            return v
        u = np.sort(v)[::-1]
        cssv = np.cumsum(u)
        rho = np.nonzero(u * np.arange(1, len(u) + 1) > (cssv - target_sum))[0]
        theta = 0.0
        if len(rho) > 0:
            rho_max = rho[-1]
            theta = (cssv[rho_max] - target_sum) / float(rho_max + 1)
        w = np.maximum(v - theta, 0)
        return w

    arr = np.asarray(probs, dtype=float)
    if axis is None:
        return _project(arr).reshape(probs.shape)

    # 按指定 axis 维度对每个切片独立执行 simplex 投影
    return np.apply_along_axis(_project, axis, arr)


def enforce_monotonic(probs: np.ndarray, *, increasing: bool = True) -> np.ndarray:
    """
    Enforce monotonicity by cumulative max (non-decreasing) or min (non-increasing).
    """
    # 通过前向累积最大值或最小值强制概率序列满足单调递增或单调递减约束
    arr = np.asarray(probs, dtype=float)
    if arr.size == 0:
        return arr
    if increasing:
        return np.maximum.accumulate(arr)
    return np.minimum.accumulate(arr)


class ConsistencyPostProcessor(StatelessAggregator):
    """
    Wrap an aggregator and post-process selected metrics for consistency.

    By default, only "frequency" metrics are post-processed. When strict_metrics=True,
    the wrapper will raise ParamValidationError if the inner aggregator produces a
    metric outside apply_to_metrics to surface configuration mismatches early.

    - Configuration
      - inner_aggregator: Aggregator whose outputs are post-processed.
      - apply_to_metrics: Metric names to which post-processing applies.
      - strict_metrics: Whether to error on metrics outside apply_to_metrics.
      - non_negative: Whether to clip negative values to zero.
      - normalize: Whether to normalize vectors to sum to one.
      - use_simplex: Whether to project onto a probability simplex.
      - monotonic: Whether to enforce monotonicity.
      - monotonic_increasing: Direction for monotonic enforcement when enabled.
      - simplex_target_sum: Target sum for simplex projection.
      - simplex_axis: Axis along which to project when using batched arrays.
      - simplex_clip_tolerance: Pre-clip tolerance for small negative values.

    - Behavior
      - Applies selected consistency operators to supported metric outputs.
      - Preserves other estimates and metadata from the inner aggregator.

    - Usage Notes
      - Use for post-processing only; it does not alter privacy guarantees.
    """
    # 默认执行非负与归一化，可选 simplex 投影与单调约束。

    def __init__(
        self,
        inner_aggregator: BaseAggregator,
        *,
        apply_to_metrics: Optional[Sequence[str]] = None,
        strict_metrics: bool = False,
        non_negative: bool = True,
        normalize: bool = True,
        use_simplex: bool = False,
        monotonic: bool = False,
        monotonic_increasing: bool = True,
        simplex_target_sum: float = 1.0,
        simplex_axis: Optional[int] = None,
        simplex_clip_tolerance: float = 0.0,
    ):
        # 保存被包装的内部聚合器实例并记录是否启用非负裁剪与归一化的开关配置
        if inner_aggregator is None:
            raise ParamValidationError("inner_aggregator is required")
        self.inner_aggregator = inner_aggregator
        if apply_to_metrics is None:
            self.apply_to_metrics = ("frequency",)
        else:
            metrics = tuple(str(m).lower() for m in apply_to_metrics if str(m).strip())
            if len(metrics) == 0:
                raise ParamValidationError("apply_to_metrics must be non-empty when provided")
            self.apply_to_metrics = metrics
        self.strict_metrics = strict_metrics
        self.non_negative = non_negative
        self.normalize = normalize
        self.use_simplex = use_simplex
        self.monotonic = monotonic
        self.monotonic_increasing = monotonic_increasing
        self.simplex_target_sum = simplex_target_sum
        self.simplex_axis = simplex_axis
        self.simplex_clip_tolerance = simplex_clip_tolerance

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 先调用内部聚合器获得估计，再按配置对指定 metric 执行一致性修正
        inner_estimate = self.inner_aggregator.aggregate(reports)
        # 使用 as_numpy 便于处理数组结果
        est = inner_estimate.as_numpy()
        point = est.point

        metric_name = (est.metric or "").lower()
        if metric_name not in self.apply_to_metrics:
            if self.strict_metrics:
                raise ParamValidationError(
                    "metric '{}' is not in apply_to_metrics {}; add it to apply_to_metrics to enable post-processing"
                )
        elif isinstance(point, np.ndarray):
            processed = point
            if self.non_negative:
                processed = enforce_non_negative(processed)
            if self.monotonic:
                processed = enforce_monotonic(processed, increasing=self.monotonic_increasing)
            if self.normalize:
                processed = normalize_probabilities(processed)
            if self.use_simplex:
                processed = project_simplex(
                    processed,
                    target_sum=self.simplex_target_sum,
                    axis=self.simplex_axis,
                    clip_tolerance=self.simplex_clip_tolerance,
                )
                if self.monotonic:
                    processed = enforce_monotonic(processed, increasing=self.monotonic_increasing)
                    if self.normalize:
                        processed = normalize_probabilities(processed)
            point = processed

        metadata = dict(est.metadata)
        metadata.update(
            {
                "postprocessed": True,
                "non_negative": self.non_negative,
                "normalized": self.normalize,
                "simplex_projection": self.use_simplex,
                "monotonic": self.monotonic,
                "monotonic_increasing": self.monotonic_increasing,
                "apply_to_metrics": list(self.apply_to_metrics),
                "strict_metrics": self.strict_metrics,
                "simplex_target_sum": self.simplex_target_sum,
                "simplex_axis": self.simplex_axis,
                "simplex_clip_tolerance": self.simplex_clip_tolerance,
            }
        )

        return Estimate(
            metric=est.metric,
            point=point,
            variance=est.variance,
            confidence_interval=est.confidence_interval,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回当前后处理器类型名称、内部聚合器类名以及非负、归一化与 simplex 投影等开关状态元信息
        return {
            "type": "consistency",
            "inner_aggregator": self.inner_aggregator.__class__.__name__,
            "non_negative": self.non_negative,
            "normalize": self.normalize,
            "simplex_projection": self.use_simplex,
            "monotonic": self.monotonic,
            "monotonic_increasing": self.monotonic_increasing,
            "apply_to_metrics": list(self.apply_to_metrics),
            "strict_metrics": self.strict_metrics,
            "simplex_target_sum": self.simplex_target_sum,
            "simplex_axis": self.simplex_axis,
            "simplex_clip_tolerance": self.simplex_clip_tolerance,
        }

    def reset(self) -> None:
        # 将重置调用透传给内部聚合器，自身不维护额外持久状态
        self.inner_aggregator.reset()
        return None
