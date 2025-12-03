"""
Sensitivity helpers for common queries.

Responsibilities:
    * Implements closed-form global sensitivity
    * Implements lightweight estimators for local/smooth sensitivity based on sample statistics
"""
# 说明：为常见查询提供全局敏感度、局部敏感度和平滑敏感度等多种计算形式的工具。
# 职责：
# - 提供 count/sum/mean/variance/histogram/range 等查询的闭式全局敏感度上界计算
# - 支持基于样本排序差分的局部敏感度估计以及基于平滑敏感度思想的均值估计器
# - 为上层 CDP 机制或分析流程提供统一的敏感度接口与错误类型

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .domain import ContinuousDomain


class SensitivityError(ValueError):
    # 表示在参数不合法或无法定义合理敏感度时使用的异常类型
    """Raised when sensitivity cannot be computed."""


def count_global_sensitivity(max_contribution: int = 1) -> float:
    # 针对计数查询在给定单个主体最大贡献次数约束下返回全局 L1 敏感度
    """Global L1 sensitivity for count queries."""
    if max_contribution <= 0:
        raise SensitivityError("max_contribution must be positive")
    return float(max_contribution)


def sum_global_sensitivity(domain: ContinuousDomain, *, max_contribution: int = 1) -> float:
    # 针对有界连续数值域上的求和查询计算全局敏感度与贡献上界成线性关系
    """Global sensitivity for sum queries over a bounded continuous domain."""
    if domain.minimum is None or domain.maximum is None:
        raise SensitivityError("continuous domain must specify min/max for sum sensitivity")
    span = domain.maximum - domain.minimum
    if span <= 0:
        raise SensitivityError("domain span must be positive for sum sensitivity")
    return span * max_contribution


def mean_global_sensitivity(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> float:
    # 将求和查询的全局敏感度按样本量缩放得到均值查询的全局敏感度上界
    """Global sensitivity bound for mean queries."""
    if sample_size <= 0:
        raise SensitivityError("sample_size must be positive")
    return sum_global_sensitivity(domain, max_contribution=max_contribution) / sample_size


def variance_global_sensitivity(
    domain: ContinuousDomain,
    *,
    sample_size: int,
    ddof: int = 1,
    max_contribution: int = 1,
) -> float:
    # 针对有界数值域上的方差查询给出全局敏感度上界并考虑 ddof 与贡献约束
    """Global sensitivity bound for variance queries over bounded domains."""
    if sample_size <= ddof:
        raise SensitivityError("sample_size must exceed ddof")
    if domain.minimum is None or domain.maximum is None:
        raise SensitivityError("continuous domain must specify min/max for variance sensitivity")
    span = domain.maximum - domain.minimum
    if span <= 0:
        raise SensitivityError("domain span must be positive for variance sensitivity")
    denom = max(sample_size - ddof, 1)
    bound = (span * span) / 4.0
    sensitivity = (span * span * max_contribution) / denom
    return float(min(sensitivity, bound))


def histogram_global_sensitivity(max_contribution: int = 1) -> float:
    # 针对直方图计数向量每个 bin 的 L1 敏感度在最大贡献约束下等于 max_contribution
    """L1 sensitivity per-bin for histogram count vectors."""
    if max_contribution <= 0:
        raise SensitivityError("max_contribution must be positive")
    return float(max_contribution)


def range_global_sensitivity(
    domain: ContinuousDomain,
    *,
    window: int,
    max_contribution: int = 1,
    metric: str = "sum",
) -> float:
    # 针对固定窗口长度的区间查询（sum/count/mean）计算全局敏感度
    """Global sensitivity for fixed-length range queries (sum/count/mean)."""
    if window <= 0:
        raise SensitivityError("window must be positive")
    if max_contribution <= 0:
        raise SensitivityError("max_contribution must be positive")

    metric = metric.lower()
    if metric not in {"sum", "count", "mean"}:
        raise SensitivityError("metric must be one of {'sum','count','mean'}")

    if metric == "count":
        return float(max_contribution)

    if domain.minimum is None or domain.maximum is None:
        raise SensitivityError("continuous domain must specify min/max for range sensitivity")
    span = domain.maximum - domain.minimum
    if span <= 0:
        raise SensitivityError("domain span must be positive for range sensitivity")

    sum_sensitivity = span * window * max_contribution
    if metric == "sum":
        return float(sum_sensitivity)
    # metric == "mean"
    return float(sum_sensitivity / window)


def local_sensitivity(values: Sequence[float], *, metric: str = "l1") -> float:
    # 通过排序样本并考察相邻差值来估计局部敏感度支持 L1/L2 等度量
    """Compute local sensitivity by inspecting neighbouring datasets."""
    if not values:
        raise SensitivityError("values cannot be empty")
    metric = metric.lower()
    if metric not in {"l1", "l2"}:
        raise SensitivityError("unsupported metric")
    # 对样本排序，计算相邻差分的最大值作为 L1 情况的估计
    sorted_vals = sorted(values)
    diffs = [abs(sorted_vals[i] - sorted_vals[i - 1]) for i in range(1, len(sorted_vals))]
    if not diffs:
        return 0.0
    max_diff = max(diffs)
    if metric == "l1":
        return max_diff
    # 若 metric="l2"，则返回相同的结果（标量输出时 L2 敏感度与 L1 相同）
    return max_diff


@dataclass
class SmoothSensitivityEstimate:
    """Result of smooth sensitivity computation."""

    beta: float
    estimate: float


def smooth_sensitivity_mean(values: Sequence[float], *, beta: float) -> SmoothSensitivityEstimate:
    """
    Simple smooth sensitivity estimator for mean queries based on Nissim et al.

    Args:
        values: Sample from which to compute smooth sensitivity.
        beta: Smoothness parameter (typically epsilon / (2 ln(1/delta))).
    """
    # 基于 Nissim 等人的平滑敏感度框架对均值查询给出 beta 控制的平滑敏感度估计
    # - 对样本排序，考虑不同“距离 k”下的相邻数据集影响，按 e^{-βk}（此处用 2^{-βk} 近似）衰减
    # - 取所有 k 的最大加权影响，最后除以 n 得到均值的平滑敏感度估计
    if beta <= 0:
        raise SensitivityError("beta must be positive")
    if not values:
        raise SensitivityError("values cannot be empty")
    sorted_vals = sorted(float(v) for v in values)
    n = len(sorted_vals)
    max_smooth = 0.0
    for k in range(n):
        left = sorted_vals[k]
        right = sorted_vals[-k - 1]
        contribution = (right - left) * pow(2.0, -beta * k)
        max_smooth = max(max_smooth, contribution)
    return SmoothSensitivityEstimate(beta=beta, estimate=max_smooth / n)
