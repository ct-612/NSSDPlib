"""
Mean estimator for continuous LDP reports.

Computes sample mean and variance from noisy reports, with optional noise-variance
subtraction when a known noise variance is provided.
"""
# 说明：针对本地加噪的连续数值报告提供均值与方差估计，并在已知噪声方差时支持简单去噪。
# 职责：
# - 接收一批连续型 LDPReport 并基于 encoded 字段计算样本均值和观测方差
# - 在调用方提供噪声方差先验时执行（observed_variance - noise_variance）的去噪近似并做非负截断
# - 在返回的 Estimate.metadata 中记录样本数裁剪区间与噪声方差信息，以便调试与后续分析

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Tuple

import numpy as np

from .base import StatelessAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


class MeanAggregator(StatelessAggregator):
    """Aggregate numeric LDP reports by computing sample mean and variance."""

    def __init__(self, clip_range: Optional[Tuple[float, float]] = None, noise_variance: Optional[float] = None):
        # 记录连续值的可选裁剪区间以及噪声方差先验，用于后续对观测方差进行近似去噪
        self.clip_range = clip_range
        self.noise_variance = noise_variance

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 聚合一批 LDP 报告，计算样本均值与观测方差并在配置噪声方差时进行简单去噪修正
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        values = np.asarray([r.encoded for r in reports], dtype=float)
        mean = float(np.mean(values))
        observed_variance = float(np.var(values, ddof=1)) if len(values) > 1 else None
        variance: Optional[float] = observed_variance
        if observed_variance is not None and self.noise_variance is not None:
            # 若已知噪声方差则用观测方差减噪声方差并截断为非负以避免数值抖动导致的负值
            variance = max(observed_variance - float(self.noise_variance), 0.0)

        metadata: Mapping[str, Any] = {
            "n_reports": len(reports),
            "clip_range": self.clip_range,
            "noise_variance": self.noise_variance,
            "observed_variance": observed_variance,
        }

        return Estimate(metric="mean", point=mean, variance=variance, confidence_interval=None, metadata=metadata)

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回当前均值聚合器的裁剪区间与噪声方差配置供外部查看
        return {"type": "mean", "clip_range": self.clip_range, "noise_variance": self.noise_variance}
