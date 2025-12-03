"""
Global sensitivity helpers for common CDP queries (wrapping core data layer).
"""
# 说明：为常见中心差分隐私查询提供基于核心数据层的全局敏感度便捷封装。
# 职责：
# - 将 count/sum/mean/variance/histogram/range 等查询的全局敏感度计算以轻量函数导出
# - 统一暴露 ContinuousDomain 与 max_contribution 等参数接口便于上层 CDP 机制复用
# - 提供 PRESETS 映射方便在配置或元数据中引用底层敏感度实现名称

from __future__ import annotations

from typing import Dict

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    count_global_sensitivity,
    histogram_global_sensitivity,
    mean_global_sensitivity,
    range_global_sensitivity,
    sum_global_sensitivity,
    variance_global_sensitivity,
)


def count(max_contribution: int = 1) -> float:
    # 返回计数查询在限定单个主体最大贡献次数条件下的全局 L1 敏感度
    return count_global_sensitivity(max_contribution=max_contribution)


def sum(domain: ContinuousDomain, *, max_contribution: int = 1) -> float:
    # 返回求和查询在有界连续数值域上最大贡献次数约束下的全局敏感度
    return sum_global_sensitivity(domain, max_contribution=max_contribution)


def mean(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> float:
    # 返回均值查询在给定样本量与贡献上界下的全局敏感度
    return mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)


def variance(
    domain: ContinuousDomain,
    *,
    sample_size: int,
    ddof: int = 1,
    max_contribution: int = 1,
) -> float:
    # 返回方差查询在有界连续域上的全局敏感度上界并考虑 ddof 与贡献约束
    return variance_global_sensitivity(
        domain,
        sample_size=sample_size,
        ddof=ddof,
        max_contribution=max_contribution,
    )


def histogram(max_contribution: int = 1) -> float:
    # 返回直方图计数向量每个 bin 的全局 L1 敏感度
    return histogram_global_sensitivity(max_contribution=max_contribution)


def range(
    domain: ContinuousDomain,
    *,
    window: int,
    max_contribution: int = 1,
    metric: str = "sum",
) -> float:
    # 返回区间查询（sum/count/mean）的全局敏感度
    return range_global_sensitivity(
        domain,
        window=window,
        max_contribution=max_contribution,
        metric=metric,
    )


# 为常见查询类型提供名称到底层敏感度实现函数名的映射
PRESETS: Dict[str, str] = {
    "count": "count_global_sensitivity",
    "sum": "sum_global_sensitivity",
    "mean": "mean_global_sensitivity",
    "variance": "variance_global_sensitivity",
    "histogram": "histogram_global_sensitivity",
    "range": "range_global_sensitivity",
}
