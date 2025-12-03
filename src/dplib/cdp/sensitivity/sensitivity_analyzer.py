"""
Sensitivity analyzer for common CDP queries.

Provides light wrappers over core data sensitivity utilities to
automatically or manually compute sensitivities for count/sum/mean and
local/smooth estimates.
"""
# 说明：为常见中心差分隐私查询提供基于核心数据层的敏感度分析与封装工具。
# 职责：
# - 针对 count/sum/mean 等标准查询统一调用底层全局敏感度计算函数并结构化返回
# - 支持局部敏感度与平滑敏感度等高级估计形式并携带计算元数据
# - 通过 analyze 入口按字符串查询名进行分发提供配置驱动的敏感度分析能力

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    SensitivityError,
    count_global_sensitivity,
    local_sensitivity,
    mean_global_sensitivity,
    smooth_sensitivity_mean,
    sum_global_sensitivity,
)
from dplib.core.utils.param_validation import ParamValidationError, ensure


@dataclass
class SensitivityReport:
    """Structured sensitivity result."""

    query: str
    sensitivity: float
    metadata: Mapping[str, float]


class SensitivityAnalyzer:
    """Analyze sensitivities for standard queries or delegate to custom calculators."""

    def count(self, *, max_contribution: int = 1) -> SensitivityReport:
        # 针对计数查询在给定单用户最大贡献次数约束下计算全局敏感度并打包为报告
        sens = count_global_sensitivity(max_contribution=max_contribution)
        return SensitivityReport(
            query="count",
            sensitivity=sens,
            metadata={"max_contribution": float(max_contribution)},
        )

    def sum(self, domain: ContinuousDomain, *, max_contribution: int = 1) -> SensitivityReport:
        # 针对数值求和查询结合 ContinuousDomain 与贡献上界计算全局敏感度
        sens = sum_global_sensitivity(domain, max_contribution=max_contribution)
        return SensitivityReport(
            query="sum",
            sensitivity=sens,
            metadata={"max_contribution": float(max_contribution)},
        )

    def mean(
        self,
        domain: ContinuousDomain,
        *,
        sample_size: int,
        max_contribution: int = 1,
    ) -> SensitivityReport:
        # 在给定样本量与贡献上界条件下计算均值查询的全局敏感度
        sens = mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)
        return SensitivityReport(
            query="mean",
            sensitivity=sens,
            metadata={"sample_size": float(sample_size), "max_contribution": float(max_contribution)},
        )

    def local(self, values: Iterable[float], *, metric: str = "l1") -> SensitivityReport:
        # 对给定样本值序列计算局部敏感度支持按 metric 选择 L1/L2 等度量
        sens = local_sensitivity(list(values), metric=metric)
        return SensitivityReport(query="local", sensitivity=sens, metadata={"metric": metric})

    def smooth_mean(self, values: Iterable[float], *, beta: float) -> SensitivityReport:
        # 计算均值查询的平滑敏感度估计并返回估计值及 beta 参数元数据
        estimate = smooth_sensitivity_mean(list(values), beta=beta)
        return SensitivityReport(
            query="smooth_mean",
            sensitivity=estimate.estimate,
            metadata={"beta": float(beta)},
        )

    def analyze(self, query: str, **kwargs) -> SensitivityReport:
        """Dispatch to a built-in analyzer by query name."""
        # 通过字符串查询名在内置分析器之间分发并对缺失参数执行显式校验
        q = query.lower()
        if q == "count":
            return self.count(max_contribution=kwargs.get("max_contribution", 1))
        if q == "sum":
            domain = kwargs.get("domain")
            if domain is None or not isinstance(domain, ContinuousDomain):
                raise ParamValidationError("domain (ContinuousDomain) is required for sum sensitivity")
            return self.sum(domain, max_contribution=kwargs.get("max_contribution", 1))
        if q == "mean":
            domain = kwargs.get("domain")
            sample_size = kwargs.get("sample_size")
            if domain is None or not isinstance(domain, ContinuousDomain):
                raise ParamValidationError("domain (ContinuousDomain) is required for mean sensitivity")
            if sample_size is None:
                raise ParamValidationError("sample_size is required for mean sensitivity")
            return self.mean(domain, sample_size=sample_size, max_contribution=kwargs.get("max_contribution", 1))
        if q == "local":
            values = kwargs.get("values")
            if values is None:
                raise ParamValidationError("values are required for local sensitivity")
            return self.local(values, metric=kwargs.get("metric", "l1"))
        if q == "smooth_mean":
            values = kwargs.get("values")
            beta = kwargs.get("beta")
            if values is None or beta is None:
                raise ParamValidationError("values and beta are required for smooth_mean sensitivity")
            return self.smooth_mean(values, beta=beta)
        raise ParamValidationError(f"unsupported query type '{query}'")


__all__ = ["SensitivityAnalyzer", "SensitivityReport", "SensitivityError"]
