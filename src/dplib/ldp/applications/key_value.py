"""
Key-value telemetry pipeline for LDP.

Responsibilities
  - Report key frequencies with categorical GRR.
  - Optionally report numeric values with local Laplace noise.
  - Aggregate key frequency and value mean estimates on the server.

Usage Context
  - Use for key-value telemetry under local DP.
  - Intended for end-to-end client/aggregator pipelines.

Limitations
  - Value estimation returns overall mean only.
  - Per-key value statistics are not implemented.
"""
# 说明：封装 key-value 遥测的 LDP 端到端应用。
# 职责：
# - 针对 key 构建类别编码与 GRR 扰动上报
# - 可选对 value 进行裁剪并使用本地 Laplace 机制上报
# - 在服务端聚合 key 频率与 value 均值估计

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Optional, Sequence, Tuple

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.continuous import LocalLaplaceMechanism
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.types import Estimate, LDPReport


@dataclass
class KeyValueClientConfig:
    """
    Client-side configuration for key-value telemetry.

    - Configuration
      - epsilon_key: Privacy budget for key perturbation.
      - epsilon_value: Optional privacy budget for value perturbation.
      - categories: Optional list of key categories.
      - value_clip_range: Optional clipping range for numeric values.

    - Behavior
      - Validates epsilon values and clipping bounds.

    - Usage Notes
      - value_clip_range is required when epsilon_value is set.
    """

    epsilon_key: float
    epsilon_value: Optional[float] = None
    categories: Optional[Sequence[Any]] = None
    value_clip_range: Optional[Tuple[float, float]] = None

    def __post_init__(self) -> None:
        # 校验 epsilon 与裁剪区间配置
        ensure_epsilon(self.epsilon_key)
        if self.categories is not None and len(self.categories) == 0:
            raise ParamValidationError("categories must be non-empty when provided")
        if self.epsilon_value is not None:
            ensure_epsilon(self.epsilon_value)
        if self.value_clip_range is not None and self.value_clip_range[0] >= self.value_clip_range[1]:
            raise ParamValidationError("value_clip_range must satisfy min < max")


@dataclass
class KeyValueServerConfig:
    """
    Server-side configuration for key-value telemetry.

    - Configuration
      - estimate_key_frequency: Whether to estimate key frequencies.
      - estimate_value_mean: Whether to estimate value mean.

    - Behavior
      - Validates that at least one estimator is enabled.

    - Usage Notes
      - Enable value mean estimation only when value reports are collected.
    """

    estimate_key_frequency: bool = True
    estimate_value_mean: bool = False

    def __post_init__(self) -> None:
        # 校验服务端是否至少启用一种估计
        if not self.estimate_key_frequency and not self.estimate_value_mean:
            raise ParamValidationError("at least one estimator must be enabled")


class KeyValueAggregator(BaseAggregator):
    """
    Aggregate key frequency and value mean estimates.

    - Configuration
      - frequency_aggregator: Aggregator for key frequencies.
      - mean_aggregator: Aggregator for value means.

    - Behavior
      - Splits reports by metric and aggregates each group.
      - Returns a combined estimate with per-metric metadata.

    - Usage Notes
      - Expects reports to carry a "metric" tag in metadata.
    """

    def __init__(self, frequency_aggregator: Optional[FrequencyAggregator] = None, mean_aggregator: Optional[MeanAggregator] = None) -> None:
        # 保存 key 与 value 的聚合器配置
        if frequency_aggregator is None and mean_aggregator is None:
            raise ParamValidationError("at least one aggregator must be provided")
        self.frequency_aggregator = frequency_aggregator
        self.mean_aggregator = mean_aggregator

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 按 metric 分组报告并输出 key 频率与 value 均值估计
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        key_reports: list[LDPReport] = []
        value_reports: list[LDPReport] = []
        for report in reports:
            metric = (report.metadata or {}).get("metric", "key")
            if metric == "value":
                value_reports.append(report)
            else:
                key_reports.append(report)

        point: dict[str, Any] = {}
        metadata: Mapping[str, Any] = {"n_reports": len(reports)}

        if self.frequency_aggregator is not None and key_reports:
            freq_est = self.frequency_aggregator.aggregate(key_reports)
            point["frequency"] = freq_est.point
            metadata = {**metadata, "frequency": freq_est.metadata}

        if self.mean_aggregator is not None and value_reports:
            mean_est = self.mean_aggregator.aggregate(value_reports)
            point["value_mean"] = mean_est.point
            metadata = {**metadata, "value_mean": mean_est.metadata}

        return Estimate(
            metric="key_value",
            point=point,
            variance=None,
            confidence_interval=None,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 汇总内部聚合器元数据
        metadata: dict[str, Any] = {"type": "key_value"}
        if self.frequency_aggregator is not None:
            metadata["frequency"] = self.frequency_aggregator.get_metadata()
        if self.mean_aggregator is not None:
            metadata["value_mean"] = self.mean_aggregator.get_metadata()
        return metadata

    def reset(self) -> None:
        # 将重置操作转发给内部聚合器
        if self.frequency_aggregator is not None:
            self.frequency_aggregator.reset()
        if self.mean_aggregator is not None:
            self.mean_aggregator.reset()
        return None


class KeyValueApplication(BaseLDPApplication):
    """
    End-to-end key-value telemetry application.

    - Configuration
      - client_config: Client configuration for key and value reporting.
      - server_config: Server configuration for aggregation.

    - Behavior
      - Builds a client that reports keys and optional values.
      - Builds a server-side aggregator for key frequencies and value mean.

    - Usage Notes
      - Value reporting requires epsilon_value and value_clip_range.
    """

    def __init__(self, client_config: KeyValueClientConfig, server_config: Optional[KeyValueServerConfig] = None) -> None:
        # 保存配置并准备 key 编码器
        self.client_config = client_config
        self.server_config = server_config or KeyValueServerConfig()
        if self.server_config.estimate_value_mean and self.client_config.epsilon_value is None:
            raise ParamValidationError("epsilon_value must be provided when estimating value mean")
        if self.client_config.epsilon_value is not None and self.client_config.value_clip_range is None:
            raise ParamValidationError("value_clip_range must be provided when epsilon_value is set")
        self._encoder = CategoricalEncoder(categories=client_config.categories)
        self._key_mechanism: Optional[GRRMechanism] = None

    def _ensure_encoder_fitted(self) -> None:
        # 确保 key 编码器已完成拟合
        if not self._encoder.is_fitted:
            raise ParamValidationError("categories must be provided or encoder must be fitted")

    def _get_or_create_key_mechanism(self) -> GRRMechanism:
        # 获取或创建 key 的 GRR 机制实例
        if self._key_mechanism is None:
            self._ensure_encoder_fitted()
            domain_size = len(self._encoder.index_to_value)
            if domain_size <= 1:
                raise ParamValidationError("domain_size must be at least 2")
            self._key_mechanism = GRRMechanism(
                epsilon=self.client_config.epsilon_key,
                domain_size=domain_size,
            )
        return self._key_mechanism

    def build_client(self) -> Callable[[Tuple[Any, Optional[float]], str], Sequence[LDPReport]]:
        # 构建客户端侧 key 与 value 的 LDP 上报函数
        self._ensure_encoder_fitted()
        encoder = self._encoder
        key_mechanism = self._get_or_create_key_mechanism()
        key_metadata = {
            "application": "key_value",
            "metric": "key",
            "encoder": encoder.get_metadata(),
            "domain_size": key_mechanism.domain_size,
            "num_categories": key_mechanism.domain_size,
            "prob_true": key_mechanism.prob_true,
            "prob_false": key_mechanism.prob_false,
            "mechanism": key_mechanism.mechanism_id,
        }

        value_mechanism = None
        value_metadata = None
        if self.client_config.epsilon_value is not None:
            clip_range = self.client_config.value_clip_range
            value_mechanism = LocalLaplaceMechanism(
                epsilon=self.client_config.epsilon_value,
                clip_range=clip_range,
            )
            scale = (clip_range[1] - clip_range[0]) / float(self.client_config.epsilon_value)
            noise_std = math.sqrt(2.0) * scale
            value_metadata = {
                "application": "key_value",
                "metric": "value",
                "clip_range": clip_range,
                "noise_type": "laplace",
                "noise_std": noise_std,
                "mechanism": value_mechanism.mechanism_id,
            }

        def client(pair: Tuple[Any, Optional[float]], user_id: str) -> Sequence[LDPReport]:
            # 将单条 key-value 记录转换为一组 LDPReport
            key, value = pair
            reports: list[LDPReport] = []
            encoded_key = encoder.encode(key)
            reports.append(key_mechanism.generate_report(encoded_key, user_id=user_id, metadata=dict(key_metadata)))
            if value_mechanism is not None and value is not None:
                clipped = max(min(float(value), value_metadata["clip_range"][1]), value_metadata["clip_range"][0])
                reports.append(
                    value_mechanism.generate_report(
                        clipped,
                        user_id=user_id,
                        metadata=dict(value_metadata),
                    )
                )
            return reports

        return client

    def build_aggregator(self) -> BaseAggregator:
        # 构建服务端 key 频率与 value 均值聚合器
        frequency_aggregator = None
        if self.server_config.estimate_key_frequency:
            num_categories = len(self._encoder.index_to_value) if self._encoder.is_fitted else None
            frequency_aggregator = FrequencyAggregator(
                num_categories=num_categories,
                mechanism="grr",
            )

        mean_aggregator = None
        if self.server_config.estimate_value_mean:
            clip_range = self.client_config.value_clip_range
            scale = (clip_range[1] - clip_range[0]) / float(self.client_config.epsilon_value)
            noise_variance = 2.0 * scale * scale
            mean_aggregator = MeanAggregator(clip_range=clip_range, noise_variance=noise_variance)

        return KeyValueAggregator(frequency_aggregator, mean_aggregator)
