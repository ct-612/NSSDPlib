"""
Post-processing helpers for CDP query outputs.

Responsibilities
  - Enforce numeric bounds and non-negativity for scalar outputs.
  - Provide normalization, simplex projection, and monotonicity for vectors.
  - Offer safe arithmetic helpers for ratios, means, and variances.

Usage Context
  - Use after DP release to restore invariants for reporting or downstream use.
  - Intended for CDP query outputs (count/sum/mean/histogram).

Limitations
  - Post-processing cannot recover information lost to DP noise.
  - Does not replace proper bounds or sensitivity configuration.
"""
# 说明：为 CDP 查询输出提供后处理工具，保证数值可行性并稳定常见统计结果。
# 职责：
# - 约束噪声结果到合法区间，提供安全的数值运算
# - 提供概率归一化、单纯形投影与单调性约束
# - 提供直方图与常见统计量的后处理入口

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np

from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type

Number = Union[int, float, np.number]
ArrayLike = Union[Sequence[Number], np.ndarray]


def _as_float(value: Any, *, label: str = "value") -> float:
    # 统一数值转换并校验有限性，确保后续运算稳定
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ParamValidationError(f"{label} must be numeric") from exc
    if not math.isfinite(numeric):
        raise ParamValidationError(f"{label} must be finite")
    return numeric


def _validate_bounds(bounds: Tuple[Number, Number]) -> Tuple[float, float]:
    # 校验边界格式并保持 lower <= upper
    ensure_type(bounds, (tuple, list), label="bounds")
    ensure(len(bounds) == 2, "bounds must be a (lower, upper) pair", error=ParamValidationError)
    lower = _as_float(bounds[0], label="bounds[0]")
    upper = _as_float(bounds[1], label="bounds[1]")
    ensure(lower <= upper, "bounds must satisfy lower <= upper", error=ParamValidationError)
    return lower, upper


def _as_array(values: ArrayLike, *, label: str = "values") -> np.ndarray:
    # 统一转为浮点数组以便向量化处理
    try:
        arr = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ParamValidationError(f"{label} must be numeric") from exc
    return arr


def clip_non_negative(values: ArrayLike) -> np.ndarray:
    """Clip values to be non-negative."""
    # 将数值裁剪到非负区间
    arr = _as_array(values)
    return np.maximum(arr, 0.0)


def clip_non_negative_scalar(value: Number) -> float:
    """Clip a scalar value to be non-negative."""
    # 将标量裁剪到非负区间
    numeric = _as_float(value)
    return max(numeric, 0.0)


def clip_bounds(values: ArrayLike, bounds: Tuple[Number, Number]) -> np.ndarray:
    """Clip values to provided bounds."""
    # 将数组裁剪到给定边界
    lower, upper = _validate_bounds(bounds)
    arr = _as_array(values)
    return np.clip(arr, lower, upper)


def clip_bounds_scalar(value: Number, bounds: Tuple[Number, Number]) -> float:
    """Clip a scalar value to provided bounds."""
    # 将标量裁剪到给定边界
    lower, upper = _validate_bounds(bounds)
    numeric = _as_float(value)
    return float(min(max(numeric, lower), upper))


def clip_probability(value: Number) -> float:
    """Clip a scalar probability to [0, 1]."""
    # 保证概率落在 [0, 1]
    return clip_bounds_scalar(value, (0.0, 1.0))


def clip_count(value: Number, *, total_count: Optional[Number] = None) -> float:
    """Clip a count to [0, total_count] when total_count is provided."""
    # 限制计数范围并可选应用总数上限
    numeric = _as_float(value)
    if total_count is None:
        return max(numeric, 0.0)
    total = _as_float(total_count, label="total_count")
    ensure(total >= 0.0, "total_count must be non-negative", error=ParamValidationError)
    return float(min(max(numeric, 0.0), total))


def clip_sum(
    value: Number,
    *,
    bounds: Tuple[Number, Number],
    count: Optional[Number] = None,
) -> float:
    """Clip a noisy sum to per-record bounds or to count-scaled bounds when provided."""
    # 按单记录或总范围裁剪求和结果
    lower, upper = _validate_bounds(bounds)
    numeric = _as_float(value)
    if count is None:
        return float(min(max(numeric, lower), upper))
    count_val = _as_float(count, label="count")
    ensure(count_val >= 0.0, "count must be non-negative", error=ParamValidationError)
    return float(np.clip(numeric, count_val * lower, count_val * upper))


def safe_divide(
    numerator: Number,
    denominator: Number,
    *,
    default: float = 0.0,
    min_denominator: float = 1e-12,
) -> float:
    """Divide with a minimum denominator guard."""
    # 分母设置下限以避免数值不稳定
    ensure(min_denominator > 0.0, "min_denominator must be positive", error=ParamValidationError)
    num = _as_float(numerator, label="numerator")
    den = _as_float(denominator, label="denominator")
    if abs(den) < min_denominator:
        return float(default)
    return float(num / den)


def safe_mean(
    dp_sum: Number,
    dp_count: Number,
    *,
    bounds: Optional[Tuple[Number, Number]] = None,
    min_count: float = 1.0,
) -> float:
    """Compute a mean with a stabilized denominator and optional clipping."""
    # 用稳定分母计算均值并可选裁剪
    ensure(min_count > 0.0, "min_count must be positive", error=ParamValidationError)
    total = _as_float(dp_count, label="dp_count")
    denom = total if total >= min_count else min_count
    mean = safe_divide(dp_sum, denom, default=0.0, min_denominator=min_count)
    if bounds is not None:
        mean = clip_bounds_scalar(mean, bounds)
    return float(mean)


def safe_rate(
    numerator: Number,
    denominator: Number,
    *,
    min_denominator: float = 1e-12,
) -> float:
    """Compute a rate clipped to [0, 1]."""
    # 计算比例并裁剪到概率区间
    value = safe_divide(numerator, denominator, default=0.0, min_denominator=min_denominator)
    return clip_probability(value)


def variance_upper_bound(
    bounds: Tuple[Number, Number],
    *,
    mean: Optional[Number] = None,
) -> float:
    """Compute an upper bound on variance for bounded data."""
    # 基于边界与可选均值给出方差上界
    lower, upper = _validate_bounds(bounds)
    span = upper - lower
    if mean is None:
        return float((span * span) / 4.0)
    mean_val = clip_bounds_scalar(mean, (lower, upper))
    return float(max((upper - mean_val) * (mean_val - lower), 0.0))


def clip_variance(
    value: Number,
    *,
    bounds: Tuple[Number, Number],
    mean: Optional[Number] = None,
) -> float:
    """Clip variance to [0, variance_upper_bound]."""
    # 将方差限制在可行范围
    upper = variance_upper_bound(bounds, mean=mean)
    numeric = _as_float(value)
    return float(min(max(numeric, 0.0), upper))


def normalize_probabilities(probs: ArrayLike) -> np.ndarray:
    """Normalize to sum to 1 when possible; fall back to uniform if total is zero."""
    # 归一化概率并在全零时回退均匀分布
    arr = _as_array(probs)
    total = float(arr.sum())
    if total > 0.0:
        return arr / total
    if arr.size == 0:
        return arr
    return np.full_like(arr, 1.0 / arr.size, dtype=float)


def project_simplex(
    probs: ArrayLike,
    *,
    target_sum: float = 1.0,
    axis: Optional[int] = None,
    clip_tolerance: float = 0.0,
) -> np.ndarray:
    """
    Project vector onto probability simplex using Duchi et al. (2008).
    Supports batch projection via `axis`.
    """
    # 将向量投影到给定和的概率单纯形
    ensure(target_sum > 0.0, "target_sum must be positive", error=ParamValidationError)

    def _project(vec: np.ndarray) -> np.ndarray:
        # 计算投影阈值并裁剪为非负
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
        return np.maximum(v - theta, 0.0)

    arr = _as_array(probs)
    if axis is None:
        return _project(arr).reshape(arr.shape)
    return np.apply_along_axis(_project, axis, arr)


def enforce_monotonic(values: ArrayLike, *, increasing: bool = True) -> np.ndarray:
    """Enforce monotonicity by cumulative max/min."""
    # 按方向施加单调约束
    arr = _as_array(values)
    if arr.size == 0:
        return arr
    if increasing:
        return np.maximum.accumulate(arr)
    return np.minimum.accumulate(arr)


def rescale_to_total(values: ArrayLike, total: Number) -> np.ndarray:
    """Rescale a non-negative vector to a target sum."""
    # 将非负向量缩放到指定总量
    total_val = _as_float(total, label="total")
    ensure(total_val >= 0.0, "total must be non-negative", error=ParamValidationError)
    arr = clip_non_negative(values)
    current = float(arr.sum())
    if current <= 0.0:
        if arr.size == 0:
            return arr
        return np.full_like(arr, total_val / arr.size, dtype=float)
    return arr * (total_val / current)


@dataclass
class HistogramPostprocessResult:
    counts: Sequence[float]
    probabilities: Optional[Sequence[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 序列化后处理结果为字典
        return {
            "counts": list(self.counts),
            "probabilities": None if self.probabilities is None else list(self.probabilities),
            "metadata": dict(self.metadata),
        }


def postprocess_histogram(
    counts: ArrayLike,
    *,
    total_count: Optional[Number] = None,
    non_negative: bool = True,
    normalize: bool = False,
    use_simplex: bool = False,
    monotonic: bool = False,
    monotonic_increasing: bool = True,
    simplex_target_sum: float = 1.0,
    simplex_axis: Optional[int] = None,
    simplex_clip_tolerance: float = 0.0,
) -> HistogramPostprocessResult:
    """Post-process histogram counts and optionally return probabilities."""
    # 对直方图计数执行后处理并可生成概率
    arr = _as_array(counts)
    ensure(arr.ndim == 1, "counts must be 1-dimensional", error=ParamValidationError)
    if non_negative:
        arr = np.maximum(arr, 0.0)
    if monotonic:
        arr = enforce_monotonic(arr, increasing=monotonic_increasing)
    if total_count is not None:
        arr = rescale_to_total(arr, total_count)

    probs = None
    if normalize:
        probs = normalize_probabilities(arr)
        if use_simplex:
            probs = project_simplex(
                probs,
                target_sum=simplex_target_sum,
                axis=simplex_axis,
                clip_tolerance=simplex_clip_tolerance,
            )
        if monotonic:
            probs = enforce_monotonic(probs, increasing=monotonic_increasing)
        probs = normalize_probabilities(probs)

    metadata = {
        "non_negative": non_negative,
        "normalize": normalize,
        "use_simplex": use_simplex,
        "monotonic": monotonic,
        "monotonic_increasing": monotonic_increasing,
        "total_count": None if total_count is None else float(total_count),
        "simplex_target_sum": simplex_target_sum,
        "simplex_axis": simplex_axis,
        "simplex_clip_tolerance": simplex_clip_tolerance,
    }
    return HistogramPostprocessResult(
        counts=arr.tolist(),
        probabilities=None if probs is None else probs.tolist(),
        metadata=metadata,
    )


def postprocess_count(value: Number, *, total_count: Optional[Number] = None) -> float:
    """Clip a noisy count to a feasible range."""
    # 统一入口裁剪计数
    return clip_count(value, total_count=total_count)


def postprocess_sum(
    value: Number,
    *,
    bounds: Tuple[Number, Number],
    count: Optional[Number] = None,
) -> float:
    """Clip a noisy sum to feasible bounds."""
    # 统一入口裁剪求和
    return clip_sum(value, bounds=bounds, count=count)


def postprocess_mean(
    dp_sum: Number,
    dp_count: Number,
    *,
    bounds: Tuple[Number, Number],
    min_count: float = 1.0,
) -> float:
    """Compute a stabilized, clipped mean."""
    # 统一入口计算均值
    return safe_mean(dp_sum, dp_count, bounds=bounds, min_count=min_count)


def postprocess_variance(
    value: Number,
    *,
    bounds: Tuple[Number, Number],
    mean: Optional[Number] = None,
) -> float:
    """Clip variance to the feasible range for bounded data."""
    # 统一入口裁剪方差
    return clip_variance(value, bounds=bounds, mean=mean)


def postprocess_rate(
    numerator: Number,
    denominator: Number,
    *,
    min_denominator: float = 1e-12,
) -> float:
    """Compute a stabilized rate clipped to [0, 1]."""
    # 统一入口计算比例
    return safe_rate(numerator, denominator, min_denominator=min_denominator)
