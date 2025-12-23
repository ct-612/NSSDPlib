"""
Aggregates empirical quantiles from numeric locally differentially private (LDP) reports.
Returns an Estimate object with point estimates for the requested quantile levels.

Responsibilities
  - Compute empirical quantiles over encoded numeric report values.
  - Optionally apply bias corrections when supported noise parameters are available.
  - Record noise configuration and adjustment status in returned metadata.

Usage Context
  - Intended for post-collection aggregation after local privatization has produced reports.
  - Expects numeric encoded values and does not validate privacy guarantees.

Limitations
  - Noise adjustment is supported only for Laplace and Gaussian models.
  - Gaussian adjustment requires SciPy; otherwise raw quantiles are returned.
  - Noise metadata is inferred only from the first report when not provided explicitly.
"""
# 说明：针对连续型 LDP 报告的分位数估计器，支持在给定噪声模型时对分位数做去噪修正。
# 职责：
# - 基于一批数值型 LDPReport 计算给定分位点的经验分位数
# - 通过构造参数或 metadata 自动解析噪声类型与标准差并尝试进行噪声感知的分位数修正
# - 在元数据中记录噪声配置和是否成功去噪的原因便于调试和下游分析

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np

from .base import StatelessAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


class QuantileAggregator(StatelessAggregator):
    """
    Estimate specified quantiles from numeric ``LDPReport`` values with optional noise adjustment.

    - Configuration
      - quantiles: Sequence of quantile probabilities to estimate in the returned order.
      - method: Identifier for the quantile estimation method.
      - noise_std: Optional standard deviation of the additive noise model.
      - noise_type: Optional noise model name such as ``"laplace"`` or ``"gaussian"``.

    - Behavior
      - Computes empirical quantiles over the report ``encoded`` values.
      - Applies bias corrections for Laplace or Gaussian noise when supported parameters are available.
      - Returns unadjusted quantiles when noise parameters are missing or unsupported and records the reason in metadata.
      - If ``noise_std`` is not provided, attempts to resolve ``noise_std`` and ``noise_type`` from the first report's metadata.

    - Usage Notes
      - The instance stores configuration but maintains no per-call state for independent batches.
      - Gaussian adjustment requires SciPy to be installed.
    """

    def __init__(
        self,
        quantiles: Sequence[float],
        method: str = "linear",
        noise_std: Optional[float] = None,
        noise_type: Optional[str] = None,
    ):
        # 初始化分位数估计器，记录目标分位点、列表插值方法以及可选的噪声标准差和噪声类型
        if len(quantiles) == 0:
            raise ParamValidationError("quantiles must be non-empty")
        self.quantiles = tuple(float(q) for q in quantiles)
        self.method = method
        if noise_std is not None and noise_std < 0:
            raise ParamValidationError("noise_std must be non-negative when provided")
        self.noise_std = noise_std
        self.noise_type = noise_type.lower() if noise_type else None

    def _resolve_noise(self, reports: Sequence[LDPReport]) -> tuple[Optional[float], Optional[str]]:
        # 优先使用构造参数中的噪声配置，若未指定则尝试从首个报告的 metadata 中解析噪声标准差与类型
        std = self.noise_std
        ntype = self.noise_type
        if std is None and reports and reports[0].metadata:
            meta = reports[0].metadata
            if "noise_std" in meta:
                try:
                    candidate = float(meta.get("noise_std"))
                    if candidate >= 0:
                        std = candidate
                except Exception:
                    std = None
            if ntype is None and "noise_type" in meta:
                try:
                    ntype = str(meta.get("noise_type")).lower()
                except Exception:
                    ntype = None
        return std, ntype

    def _debias_quantiles(
        self,
        q_values: np.ndarray,
        noise_std: float,
        noise_type: Optional[str],
    ) -> tuple[np.ndarray, bool, str]:
        # 根据噪声分布类型对分位数做闭式偏移修正，当前支持 Laplace 与 Gaussian 模型
        noise_type = (noise_type or "gaussian").lower()
        if noise_std <= 0:
            return q_values, False, "noise_std_non_positive"

        if noise_type in {"laplace", "lap"}:
            b = noise_std / np.sqrt(2.0)
            shifts = []
            for q in self.quantiles:
                if q < 0.5:
                    shifts.append(-b * np.log(max(2 * q, 1e-12)))
                else:
                    shifts.append(b * np.log(max(2 * (1 - q), 1e-12)))
            return q_values - np.asarray(shifts, dtype=float), True, "laplace"

        if noise_type in {"gaussian", "normal"}:
            try:
                from scipy.stats import norm  # type: ignore
            except Exception:
                return q_values, False, "scipy_missing"
            shifts = noise_std * norm.ppf(self.quantiles)
            return q_values - shifts, True, "gaussian"

        return q_values, False, "noise_type_unsupported"

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 聚合一批 LDP 报告，计算经验分位数并在解析到噪声模型时尝试执行去噪调整
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        values = np.asarray([r.encoded for r in reports], dtype=float)
        q_values = np.quantile(values, self.quantiles, method=self.method)

        noise_std, noise_type = self._resolve_noise(reports)
        adjusted = q_values
        noise_adjusted = False
        noise_reason = None
        if noise_std is not None:
            adjusted, noise_adjusted, noise_reason = self._debias_quantiles(q_values, noise_std, noise_type)

        metadata: Mapping[str, Any] = {
            "quantiles": list(self.quantiles),
            "n_reports": len(reports),
            "method": self.method,
            "noise_std": noise_std,
            "noise_type": noise_type,
            "noise_adjusted": noise_adjusted,
            "noise_adjustment_reason": noise_reason,
        }

        return Estimate(metric="quantile", point=adjusted, variance=None, confidence_interval=None, metadata=metadata)

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回当前量化聚合器的分位点列表、插值方法与噪声配置等元信息
        return {
            "type": "quantile",
            "quantiles": list(self.quantiles),
            "method": self.method,
            "noise_std": self.noise_std,
            "noise_type": self.noise_type,
        }
