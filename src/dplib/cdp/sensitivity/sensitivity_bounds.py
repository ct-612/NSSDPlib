"""
Sensitivity bounds helpers for common CDP queries.

Provides upper/lower estimates and lightweight proof metadata to aid
testing and documentation.
"""
# 说明：为常见中心差分隐私查询提供敏感度上下界封装与简要证明说明。
# 职责：
# - 基于核心敏感度函数为各类查询构造下界与上界容器
# - 通过 SensitivityBounds 携带证明提示便于测试与文档引用
# - 提供 tighten 接口结合观测局部敏感度对上界进行收紧

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    count_global_sensitivity,
    histogram_global_sensitivity,
    mean_global_sensitivity,
    range_global_sensitivity,
    sum_global_sensitivity,
    variance_global_sensitivity,
)
from dplib.core.utils.param_validation import ensure_type


@dataclass(frozen=True)
class SensitivityBounds:
    """Container for lower/upper bounds and optional proof note."""

    lower: float
    upper: float
    proof: Optional[str] = None

    def to_dict(self) -> Dict[str, float]:
        # 以普通字典形式导出当前敏感度上下界便于序列化或调试
        return {"lower": float(self.lower), "upper": float(self.upper)}


def count_bounds(max_contribution: int = 1) -> SensitivityBounds:
    # 针对 count 查询基于全局敏感度构造下界为 0 的敏感度区间
    upper = count_global_sensitivity(max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="global bound; lower bound by definition >=0")


def sum_bounds(domain: ContinuousDomain, *, max_contribution: int = 1) -> SensitivityBounds:
    # 针对求和查询在有界连续域和贡献上界条件下给出敏感度上下界与证明说明
    upper = sum_global_sensitivity(domain, max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="bounded continuous domain span * contribution")


def mean_bounds(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> SensitivityBounds:
    # 针对均值查询通过 sum 全局敏感度与样本量构造上下界并记录 sum/sample_size 关系
    upper = mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="sum bound / sample_size")


def variance_bounds(
    domain: ContinuousDomain,
    *,
    sample_size: int,
    ddof: int = 1,
    max_contribution: int = 1,
) -> SensitivityBounds:
    # 针对方差查询在有界域、样本量与 ddof 约束下构造敏感度上下界
    upper = variance_global_sensitivity(
        domain,
        sample_size=sample_size,
        ddof=ddof,
        max_contribution=max_contribution,
    )
    return SensitivityBounds(lower=0.0, upper=upper, proof="bounded variable variance <= span^2/4")


def histogram_bounds(max_contribution: int = 1) -> SensitivityBounds:
    # 针对直方图计数向量的每个 bin 给出基于贡献次数的敏感度上下界
    upper = histogram_global_sensitivity(max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="each record contributes to one bin")


def range_bounds(
    domain: ContinuousDomain,
    *,
    window: int,
    max_contribution: int = 1,
    metric: str = "sum",
) -> SensitivityBounds:
    # 针对固定窗口长度的区间查询（sum/count/mean）给出对应的敏感度上下界
    upper = range_global_sensitivity(
        domain,
        window=window,
        max_contribution=max_contribution,
        metric=metric,
    )
    proof = {
        "sum": "range sum bound = span * window * contribution",
        "mean": "range mean bound = (span * window * contribution)/window",
        "count": "range count bound = max_contribution",
    }.get(metric, "range bound")
    return SensitivityBounds(lower=0.0, upper=upper, proof=proof)


def tighten(bounds: SensitivityBounds, *, observed: float) -> SensitivityBounds:
    """
    Optionally tighten bounds using an observed sensitivity (e.g., local estimate).
    """
    # 使用观测敏感度值对既有敏感度区间的上界进行收紧，保持下界与证明说明不变
    ensure_type(observed, (int, float), label="observed")
    upper = min(bounds.upper, float(observed))
    return SensitivityBounds(lower=bounds.lower, upper=upper, proof=bounds.proof)
