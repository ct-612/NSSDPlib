"""
Range query pipeline for numeric data under LDP.

Responsibilities
  - Build client-side clipping and local Laplace perturbation.
  - Build server-side mean and quantile estimators for numeric summaries.
  - Provide an end-to-end numeric query application.

Usage Context
  - Use for numeric range summaries under local DP.
  - Intended for end-to-end client/aggregator pipelines.

Limitations
  - Only Laplace noise is supported in the current implementation.
  - Bucket-based range counts are not implemented.
"""
# 说明：封装数值型数据的区间统计与均值分位数估计的 LDP 端到端应用。
# 职责：
# - 在客户端执行裁剪并使用本地 Laplace 机制扰动数值
# - 在服务端构建均值与分位数聚合器输出统计估计
# - 预留基于分桶的区间计数与更多连续机制扩展空间

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.aggregators.quantile import QuantileAggregator
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.continuous import LocalLaplaceMechanism
from dplib.ldp.types import Estimate, LDPReport


def _laplace_noise_stats(epsilon: float, clip_range: Tuple[float, float]) -> Tuple[float, float, float]:
    # 基于裁剪区间与 epsilon 计算 Laplace 机制的尺度与噪声统计量
    scale = (clip_range[1] - clip_range[0]) / float(epsilon)
    noise_variance = 2.0 * scale * scale
    noise_std = math.sqrt(2.0) * scale
    return scale, noise_std, noise_variance


@dataclass
class RangeQueriesClientConfig:
    """
    Client-side configuration for range queries.

    - Configuration
      - epsilon: Privacy budget for local perturbation.
      - clip_range: Tuple specifying min and max clipping bounds.
      - mechanism: Mechanism identifier; currently only "laplace".

    - Behavior
      - Validates epsilon, clip range, and mechanism identifiers.

    - Usage Notes
      - clip_range must satisfy min < max.
    """

    epsilon: float
    clip_range: Tuple[float, float]
    mechanism: str = "laplace"

    def __post_init__(self) -> None:
        # 校验 epsilon、裁剪区间与机制标识
        ensure_epsilon(self.epsilon)
        if self.clip_range[0] >= self.clip_range[1]:
            raise ParamValidationError("clip_range must satisfy min < max")
        if not self.mechanism:
            raise ParamValidationError("mechanism must be non-empty")
        self.mechanism = str(self.mechanism).lower()
        if self.mechanism not in {"laplace"}:
            raise ParamValidationError("unsupported mechanism for range queries")


@dataclass
class RangeQueriesServerConfig:
    """
    Server-side configuration for range queries.

    - Configuration
      - estimate_mean: Whether to compute a mean estimate.
      - estimate_quantiles: Optional quantiles to estimate.

    - Behavior
      - Validates that at least one estimator is enabled.

    - Usage Notes
      - Quantiles are computed over encoded values.
    """

    estimate_mean: bool = True
    estimate_quantiles: Optional[Sequence[float]] = None

    def __post_init__(self) -> None:
        # 校验服务端统计配置是否至少启用一种估计
        if not self.estimate_mean and not self.estimate_quantiles:
            raise ParamValidationError("at least one estimator must be enabled")
        if self.estimate_quantiles is not None and len(self.estimate_quantiles) == 0:
            raise ParamValidationError("estimate_quantiles must be non-empty when provided")


class RangeQueriesAggregator(BaseAggregator):
    """
    Aggregate numeric reports into mean and quantile estimates.

    - Configuration
      - mean_aggregator: Optional mean aggregator instance.
      - quantile_aggregator: Optional quantile aggregator instance.

    - Behavior
      - Aggregates mean and quantile estimates in a single output.
      - Returns combined metadata for each estimator.

    - Usage Notes
      - Expects numeric encoded values in reports.
    """

    def __init__(self, mean_aggregator: Optional[MeanAggregator] = None, quantile_aggregator: Optional[QuantileAggregator] = None) -> None:
        # 组合均值与分位数聚合器用于一次性输出多种统计量
        if mean_aggregator is None and quantile_aggregator is None:
            raise ParamValidationError("at least one aggregator must be provided")
        self.mean_aggregator = mean_aggregator
        self.quantile_aggregator = quantile_aggregator

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 同时聚合均值与分位数并返回组合后的 Estimate
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        point: dict[str, Any] = {}
        metadata: Mapping[str, Any] = {"n_reports": len(reports)}
        if self.mean_aggregator is not None:
            mean_est = self.mean_aggregator.aggregate(reports)
            point["mean"] = mean_est.point
            metadata = {**metadata, "mean": mean_est.metadata}
        if self.quantile_aggregator is not None:
            quantile_est = self.quantile_aggregator.aggregate(reports)
            point["quantiles"] = quantile_est.point
            metadata = {**metadata, "quantiles": quantile_est.metadata}

        return Estimate(
            metric="range_queries",
            point=point,
            variance=None,
            confidence_interval=None,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 汇总内部聚合器元数据便于外部追踪
        metadata: dict[str, Any] = {"type": "range_queries"}
        if self.mean_aggregator is not None:
            metadata["mean"] = self.mean_aggregator.get_metadata()
        if self.quantile_aggregator is not None:
            metadata["quantiles"] = self.quantile_aggregator.get_metadata()
        return metadata

    def reset(self) -> None:
        # 将重置操作转发给内部聚合器
        if self.mean_aggregator is not None:
            self.mean_aggregator.reset()
        if self.quantile_aggregator is not None:
            self.quantile_aggregator.reset()
        return None


class RangeQueriesApplication(BaseLDPApplication):
    """
    End-to-end range query application for numeric data.

    - Configuration
      - client_config: Client configuration for clipping and perturbation.
      - server_config: Server configuration for aggregation.

    - Behavior
      - Builds a client that clips values and applies local Laplace noise.
      - Builds a server-side aggregator for mean and optional quantiles.

    - Usage Notes
      - Quantile estimation uses noise parameters derived from the client config.
    """

    def __init__(self, client_config: RangeQueriesClientConfig, server_config: Optional[RangeQueriesServerConfig] = None) -> None:
        # 保存客户端与服务端配置
        self.client_config = client_config
        self.server_config = server_config or RangeQueriesServerConfig()

    def build_client(self) -> Callable[[float, str], LDPReport]:
        # 构建客户端侧的数值裁剪与扰动上报函数
        clip_range = self.client_config.clip_range
        mechanism = LocalLaplaceMechanism(
            epsilon=self.client_config.epsilon,
            clip_range=clip_range,
        )
        _, noise_std, _ = _laplace_noise_stats(self.client_config.epsilon, clip_range)
        base_metadata = {
            "application": "range_queries",
            "clip_range": clip_range,
            "noise_type": "laplace",
            "noise_std": noise_std,
            "mechanism": mechanism.mechanism_id,
        }

        def client(raw_value: float, user_id: str) -> LDPReport:
            # 对数值进行裁剪并生成带噪声的 LDPReport
            value = float(raw_value)
            clipped = max(min(value, clip_range[1]), clip_range[0])
            metadata = dict(base_metadata)
            return mechanism.generate_report(clipped, user_id=user_id, metadata=metadata)

        return client

    def build_aggregator(self) -> BaseAggregator:
        # 构建服务端均值与分位数聚合器组合
        clip_range = self.client_config.clip_range
        _, noise_std, noise_variance = _laplace_noise_stats(self.client_config.epsilon, clip_range)

        mean_aggregator = None
        if self.server_config.estimate_mean:
            mean_aggregator = MeanAggregator(clip_range=clip_range, noise_variance=noise_variance)

        quantile_aggregator = None
        if self.server_config.estimate_quantiles is not None:
            quantile_aggregator = QuantileAggregator(
                quantiles=self.server_config.estimate_quantiles,
                noise_std=noise_std,
                noise_type="laplace",
            )

        if mean_aggregator is not None and quantile_aggregator is None:
            return mean_aggregator
        if mean_aggregator is None and quantile_aggregator is not None:
            return quantile_aggregator
        return RangeQueriesAggregator(mean_aggregator, quantile_aggregator)
