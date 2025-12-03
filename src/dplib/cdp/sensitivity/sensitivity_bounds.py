"""
Sensitivity bounds helpers for common CDP queries.

Provides upper/lower estimates and lightweight proof metadata to aid
testing and documentation.
"""
# 说明：为常见中心差分隐私查询提供全局敏感度上下界与证明备注的辅助工具。
# 职责：
# - 基于核心敏感度实现为 count/sum/mean 构造下界与上界的统一封装
# - 通过 SensitivityBounds 结构体携带上下界数值与简要证明说明便于测试与文档引用
# - 提供 tighten 工具基于观测局部敏感度对原有上界进行可选收紧

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    SensitivityError,
    count_global_sensitivity,
    mean_global_sensitivity,
    sum_global_sensitivity,
)
from dplib.core.utils.param_validation import ensure_type


@dataclass(frozen=True)
class SensitivityBounds:
    """Container for lower/upper bounds and optional proof note."""

    lower: float
    upper: float
    proof: Optional[str] = None

    def to_dict(self) -> Dict[str, float]:
        # 以普通字典形式导出上下界数值方便序列化或与配置对接
        return {"lower": float(self.lower), "upper": float(self.upper)}


def count_bounds(max_contribution: int = 1) -> SensitivityBounds:
    # 针对计数查询给出全局敏感度上界并将下界固定为 0 构造成界对象
    upper = count_global_sensitivity(max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="global bound; lower bound by definition >=0")


def sum_bounds(domain: ContinuousDomain, *, max_contribution: int = 1) -> SensitivityBounds:
    # 针对求和查询在有界连续域与最大贡献约束下生成敏感度上下界与简要证明说明
    upper = sum_global_sensitivity(domain, max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="bounded continuous domain span * contribution")


def mean_bounds(domain: ContinuousDomain, *, sample_size: int, max_contribution: int = 1) -> SensitivityBounds:
    # 针对均值查询基于 sum 全局敏感度与样本量推导出上下界并记录 sum/sample_size 关系
    upper = mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)
    return SensitivityBounds(lower=0.0, upper=upper, proof="sum bound / sample_size")


def tighten(bounds: SensitivityBounds, *, observed: float) -> SensitivityBounds:
    """
    Optionally tighten bounds using an observed sensitivity (e.g., local estimate).
    """
    # 使用观测到的敏感度值对原上界进行收紧但保持下界与证明说明不变
    ensure_type(observed, (int, float), label="observed")
    upper = min(bounds.upper, float(observed))
    return SensitivityBounds(lower=bounds.lower, upper=upper, proof=bounds.proof)


__all__ = ["SensitivityBounds", "count_bounds", "sum_bounds", "mean_bounds", "tighten", "SensitivityError"]
