"""
Numerical utilities shared across the library.

Responsibilities
  - Provide numerically stable aggregations (logsumexp, softmax).
  - Expose helper statistics such as stable mean and variance.
  - Guard against floating point issues in probability utilities.

Usage Context
  - Use in DP mechanisms or analytics where numerical stability matters.
  - Intended for small utility helpers reused across modules.

Limitations
  - Assumes numeric inputs convertible to numpy arrays.
  - Does not validate probability semantics beyond clamping and normalization.
"""
# 说明：库内共享的数值工具函数集合，集中实现数值稳定的聚合与统计运算。
# 职责：
# - 提供数值稳定的 logsumexp / softmax 计算，避免溢出或下溢
# - 提供稳定的均值 / 方差统计（包括在线 Welford 算法）
# - 对概率向量进行裁剪与重新归一化，缓解浮点误差对 DP 参数的影响
# - 封装公共 ArrayLike 类型别名，统一处理 Python 序列与 numpy 数组

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple, Union

import numpy as np

ArrayLike = Union[Sequence[float], np.ndarray]


def logsumexp(values: ArrayLike, axis: Optional[int] = None, keepdims: bool = False) -> np.ndarray:
    """Stable log(sum(exp(values)))."""
    # 使用“减去最大值”的技巧实现数值稳定的 logsumexp
    arr = np.asarray(values, dtype=np.float64)
    max_val = np.max(arr, axis=axis, keepdims=True)
    shifted = arr - max_val
    sum_exp = np.sum(np.exp(shifted), axis=axis, keepdims=True)
    out = np.log(sum_exp) + max_val
    if not keepdims and axis is not None:
        out = np.squeeze(out, axis=axis)
    return out


def softmax(values: ArrayLike, axis: Optional[int] = None) -> np.ndarray:
    """Stable softmax implementation using logsumexp."""
    # 基于 logsumexp 实现 softmax，避免直接 exp 导致的数值不稳定
    arr = np.asarray(values, dtype=np.float64)
    logits = arr - logsumexp(arr, axis=axis, keepdims=True)
    return np.exp(logits)


def stable_mean(values: Iterable[float]) -> float:
    """Return the mean using float64 accumulation."""
    # 使用 float64 精度进行累加，确保在长序列上具有良好的数值稳定性
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        raise ValueError("stable_mean requires at least one value")
    return float(np.sum(arr, dtype=np.float64) / arr.size)


def stable_variance(values: Iterable[float], ddof: int = 1) -> float:
    """Return variance using Welford's algorithm."""
    # Welford 在线算法：单遍扫描计算方差，适用于流式或大规模数据
    mean_val = 0.0
    m2 = 0.0
    count = 0
    for value in values:
        count += 1
        delta = value - mean_val
        mean_val += delta / count
        delta2 = value - mean_val
        m2 += delta * delta2
    if count <= ddof:
        raise ValueError("not enough values to compute variance")
    return m2 / (count - ddof)


def clamp_probabilities(probabilities: ArrayLike, eps: float = 1e-12) -> np.ndarray:
    """Clamp probabilities into [eps, 1-eps] and renormalize."""
    # 将概率裁剪到 [eps, 1-eps]，再重新归一化，避免 0/1 引发的 log() 或比值计算问题
    arr = np.asarray(probabilities, dtype=np.float64)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    clamped = np.clip(arr, eps, 1.0 - eps)
    normalizer = clamped.sum()
    if normalizer == 0.0:
        raise ValueError("probabilities sum to zero after clamping")
    return clamped / normalizer
