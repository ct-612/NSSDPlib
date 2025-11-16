"""
Sensitivity helpers for common queries.

Responsibilities:
    * Implements closed-form global sensitivity 
    * Implements lightweight estimators for local/smooth sensitivity based on sample statistics
"""
# 说明：常见查询的敏感度辅助工具。
# 职责：
# - 提供常见查询（计数、求和、均值）的敏感度（sensitivity）工具函数
# - 包含封闭形式的全局敏感度以及基于样本统计的局部/平滑敏感度轻量估计

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence

from .domain import ContinuousDomain, DomainError
from .statistics import mean


class SensitivityError(ValueError):
    """Raised when sensitivity cannot be computed."""
    # 敏感度相关的参数或数据非法时抛出的异常（如 sample_size<=0、空样本等）


def count_global_sensitivity(max_contribution: int = 1) -> float:
    """Global L1 sensitivity for count queries."""
    # 计数查询的全局 L1 敏感度：等于每个个体的最大贡献次数
    if max_contribution <= 0:
        raise SensitivityError("max_contribution must be positive")
    return float(max_contribution)


def sum_global_sensitivity(domain: ContinuousDomain, *, max_contribution: int = 1) -> float:
    """Global sensitivity for sum queries over a bounded continuous domain."""
    # 求和查询（在有界连续域上）的全局敏感度：
    #   span = (max - min)，单个个体最多影响为 span；
    #   若每个个体最多贡献 max_contribution 次，则灵敏度为 span * max_contribution
    if domain.minimum is None or domain.maximum is None:
        raise SensitivityError("continuous domain must specify min/max for sum sensitivity")
    span = domain.maximum - domain.minimum
    return span * max_contribution


def mean_global_sensitivity(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> float:
    """Global sensitivity bound for mean queries."""
    # 均值查询的全局敏感度上界：等于求和敏感度 / 样本量
    if sample_size <= 0:
        raise SensitivityError("sample_size must be positive")
    return sum_global_sensitivity(domain, max_contribution=max_contribution) / sample_size


def local_sensitivity(values: Sequence[float], *, metric: str = "l1") -> float:
    """Compute local sensitivity by inspecting neighbouring datasets."""
    # 局部敏感度（local sensitivity）简化估计：
    # - 对样本排序，计算相邻差分的最大值作为 L1 情况的估计；
    # - 若 metric="l2"，则返回相同的结果（标量输出时 L2 敏感度与 L1 相同）
    if not values:
        raise SensitivityError("values cannot be empty")
    metric = metric.lower()
    if metric not in {"l1", "l2"}:
        raise SensitivityError("unsupported metric")
    sorted_vals = sorted(values)
    diffs = [abs(sorted_vals[i] - sorted_vals[i - 1]) for i in range(1, len(sorted_vals))]
    if not diffs:
        return 0.0
    max_diff = max(diffs)
    if metric == "l1":
        return max_diff
    # 对标量输出而言，L2 敏感度与 L1 相同（均为最大绝对差）
    return max_diff


@dataclass
class SmoothSensitivityEstimate:
    """Result of smooth sensitivity computation."""
    # 平滑灵敏度（smooth sensitivity）估计结果的容器：包含 β 与估计值

    beta: float
    estimate: float


def smooth_sensitivity_mean(values: Sequence[float], *, beta: float) -> SmoothSensitivityEstimate:
    """
    Simple smooth sensitivity estimator for mean queries based on Nissim et al.

    Args:
        values: Sample from which to compute smooth sensitivity.
        beta: Smoothness parameter (typically epsilon / (2 ln(1/delta))).
    """
    # 均值查询的平滑敏感度简化估计（基于 Nissim 等人的思想）：
    # - 对样本排序，考虑不同“距离 k”下的相邻数据集影响，按 e^{-βk}（此处用 2^{-βk} 近似）衰减；
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
