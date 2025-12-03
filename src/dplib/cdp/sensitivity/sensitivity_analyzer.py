"""
Sensitivity analyzer for common CDP queries.

Provides light wrappers over core data sensitivity utilities to
automatically or manually compute sensitivities for standard queries and
local/smooth estimates.
"""
# 说明：针对常见中心差分隐私查询提供敏感度计算与封装的分析器组件。
# 职责：
# - 基于核心数据层的全局敏感度函数为标准查询构造统一的敏感度报告
# - 提供局部敏感度和平滑敏感度等估计形式并暴露元数据用于调试和文档
# - 通过字符串化的 analyze 分发接口支持按查询类型动态选择分析路径

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

from dplib.core.data.domain import ContinuousDomain
from dplib.core.data.sensitivity import (
    count_global_sensitivity,
    histogram_global_sensitivity,
    local_sensitivity,
    mean_global_sensitivity,
    range_global_sensitivity,
    smooth_sensitivity_mean,
    sum_global_sensitivity,
    variance_global_sensitivity,
)
from dplib.core.utils.param_validation import ParamValidationError


@dataclass
class SensitivityReport:
    """Structured sensitivity result."""

    query: str
    sensitivity: float
    metadata: Mapping[str, float]


class SensitivityAnalyzer:
    """Analyze sensitivities for standard queries or delegate to custom calculators."""

    def count(self, *, max_contribution: int = 1) -> SensitivityReport:
        # 针对计数查询在给定单用户最大贡献次数约束下计算全局敏感度并生成报告
        sens = count_global_sensitivity(max_contribution=max_contribution)
        return SensitivityReport(
            query="count",
            sensitivity=sens,
            metadata={"max_contribution": float(max_contribution)},
        )

    def sum(self, domain: ContinuousDomain, *, max_contribution: int = 1) -> SensitivityReport:
        # 针对有界连续域上的求和查询计算全局敏感度并记录贡献上界
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
        # 针对均值查询在给定样本量与贡献上界条件下计算全局敏感度
        sens = mean_global_sensitivity(domain, sample_size=sample_size, max_contribution=max_contribution)
        return SensitivityReport(
            query="mean",
            sensitivity=sens,
            metadata={"sample_size": float(sample_size), "max_contribution": float(max_contribution)},
        )

    def variance(
        self,
        domain: ContinuousDomain,
        *,
        sample_size: int,
        ddof: int = 1,
        max_contribution: int = 1,
    ) -> SensitivityReport:
        # 针对方差查询计算全局敏感度并保留样本量与自由度信息
        sens = variance_global_sensitivity(
            domain,
            sample_size=sample_size,
            ddof=ddof,
            max_contribution=max_contribution,
        )
        return SensitivityReport(
            query="variance",
            sensitivity=sens,
            metadata={
                "sample_size": float(sample_size),
                "ddof": float(ddof),
                "max_contribution": float(max_contribution),
            },
        )

    def histogram(self, *, max_contribution: int = 1) -> SensitivityReport:
        # 针对直方图计数向量返回每个 bin 的全局敏感度上界
        sens = histogram_global_sensitivity(max_contribution=max_contribution)
        return SensitivityReport(
            query="histogram",
            sensitivity=sens,
            metadata={"max_contribution": float(max_contribution)},
        )

    def range(
        self,
        domain: ContinuousDomain,
        *,
        window: int,
        max_contribution: int = 1,
        metric: str,
    ) -> SensitivityReport:
        # 针对固定窗口长度的区间查询（sum/count/mean）计算全局敏感度
        sens = range_global_sensitivity(domain, window=window, max_contribution=max_contribution, metric=metric)
        return SensitivityReport(
            query=f"range_{metric}",
            sensitivity=sens,
            metadata={"window": float(window), "max_contribution": float(max_contribution), "metric": metric},
        )

    def local(self, values: Iterable[float], *, metric: str = "l1") -> SensitivityReport:
        # 根据样本值与度量类型计算局部敏感度，用于 tighter 的经验估计
        sens = local_sensitivity(list(values), metric=metric)
        return SensitivityReport(query="local", sensitivity=sens, metadata={"metric": metric})

    def smooth_mean(self, values: Iterable[float], *, beta: float) -> SensitivityReport:
        # 基于样本值与 beta 参数计算均值查询的平滑敏感度估计
        estimate = smooth_sensitivity_mean(list(values), beta=beta)
        return SensitivityReport(
            query="smooth_mean",
            sensitivity=estimate.estimate,
            metadata={"beta": float(beta)},
        )

    def analyze(self, query: str, **kwargs) -> SensitivityReport:
        """Dispatch to a built-in analyzer by query name."""
        # 统一入口根据查询名分派到对应分析方法并校验所需参数是否齐全
        q = query.lower()
        if q == "count":
            return self.count(max_contribution=kwargs.get("max_contribution", 1))
        if q == "sum":
            domain = self._require_domain(kwargs.get("domain"), "sum")
            return self.sum(domain, max_contribution=kwargs.get("max_contribution", 1))
        if q == "mean":
            domain = self._require_domain(kwargs.get("domain"), "mean")
            sample_size = self._require_param(kwargs.get("sample_size"), "sample_size", "mean")
            return self.mean(domain, sample_size=sample_size, max_contribution=kwargs.get("max_contribution", 1))
        if q == "variance":
            domain = self._require_domain(kwargs.get("domain"), "variance")
            sample_size = self._require_param(kwargs.get("sample_size"), "sample_size", "variance")
            return self.variance(
                domain,
                sample_size=sample_size,
                ddof=kwargs.get("ddof", 1),
                max_contribution=kwargs.get("max_contribution", 1),
            )
        if q == "histogram":
            return self.histogram(max_contribution=kwargs.get("max_contribution", 1))
        if q == "range":
            domain = self._require_domain(kwargs.get("domain"), "range")
            window = self._require_param(kwargs.get("window"), "window", "range")
            return self.range(domain, window=window, max_contribution=kwargs.get("max_contribution", 1), metric=kwargs.get("metric", "sum"))
        if q == "local":
            values = self._require_param(kwargs.get("values"), "values", "local")
            return self.local(values, metric=kwargs.get("metric", "l1"))
        if q == "smooth_mean":
            values = self._require_param(kwargs.get("values"), "values", "smooth_mean")
            beta = self._require_param(kwargs.get("beta"), "beta", "smooth_mean")
            return self.smooth_mean(values, beta=beta)
        raise ParamValidationError(f"unsupported query type '{query}'")

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _require_domain(domain: Optional[ContinuousDomain], name: str) -> ContinuousDomain:
        # 辅助校验 domain 参数是否为 ContinuousDomain 并在缺失时抛出统一错误信息
        if domain is None or not isinstance(domain, ContinuousDomain):
            raise ParamValidationError(f"domain (ContinuousDomain) is required for {name} sensitivity")
        return domain

    @staticmethod
    def _require_param(value: Optional[float], param: str, name: str) -> float:
        # 辅助校验某个标量参数非空用于 reduce analyze 分支中的重复判定逻辑
        if value is None:
            raise ParamValidationError(f"{param} is required for {name} sensitivity")
        return value
