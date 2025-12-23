"""
Variance estimator for continuous LDP reports.

Supports optional noise-variance subtraction when provided, and records both observed
and de-noised estimates for downstream use.

Responsibilities
  - Compute sample variance from encoded numeric reports.
  - Optionally subtract a known noise variance.
  - Provide metadata describing variance adjustment behavior.

Usage Context
  - Use for continuous LDP mechanisms that report numeric values.
  - Intended for server-side aggregation of LDPReport batches.

Limitations
  - Variance is set to zero for a single report.
  - Noise variance subtraction is a simple approximation.
"""
# 说明：针对连续型 LDP 报告估计观测方差并在可用时减去噪声方差以得到去噪方差估计。
# 职责：
# - 计算加噪观测值的样本方差并支持基于外部给定噪声方差的简单去噪
# - 在元数据中记录报告数量/截断区间/噪声方差与是否做去噪等信息，便于下游分析和调试

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np

from .base import StatelessAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


class VarianceAggregator(StatelessAggregator):
    """
    Aggregate numeric LDP reports by computing optional de-noised sample variance.

    - Configuration
      - clip_range: Optional clip range recorded in metadata.
      - noise_variance: Optional noise variance used for variance correction.

    - Behavior
      - Computes sample variance and optionally subtracts noise variance.
      - Records whether noise adjustment was applied.

    - Usage Notes
      - Expects encoded values to be numeric.
    """

    def __init__(self, clip_range: Optional[Tuple[float, float]] = None, noise_variance: Optional[float] = None):
        # 初始化方差聚合器，记录可选的截断区间以及用于后续去噪的噪声方差配置
        self.clip_range = clip_range
        self.noise_variance = noise_variance

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 从一批 LDPReport 中提取数值计算样本方差并在提供噪声方差时进行简单去噪
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        values = np.asarray([r.encoded for r in reports], dtype=float)
        mean = float(np.mean(values))
        observed_variance = float(np.var(values, ddof=1)) if len(values) > 1 else 0.0
        variance = observed_variance
        noise_adjusted = False
        if self.noise_variance is not None:
            variance = max(observed_variance - float(self.noise_variance), 0.0)
            noise_adjusted = True

        metadata: Mapping[str, Any] = {
            "n_reports": len(reports),
            "clip_range": self.clip_range,
            "mean": mean,
            "noise_variance": self.noise_variance,
            "observed_variance": observed_variance,
            "noise_adjusted": noise_adjusted,
        }

        return Estimate(metric="variance", point=variance, variance=None, confidence_interval=None, metadata=metadata)

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回聚合器类型以及当前截断区间和噪声方差设置，便于重建或序列化配置
        return {"type": "variance", "clip_range": self.clip_range, "noise_variance": self.noise_variance}
