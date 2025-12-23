"""
Marginals estimation pipeline for multi-dimensional categorical data.

Responsibilities
  - Build per-dimension encoders and GRR perturbation.
  - Aggregate per-dimension frequency estimates into a marginals summary.
  - Expose metadata for each dimension to aid downstream analysis.

Usage Context
  - Use for per-dimension marginal estimation under local DP.
  - Intended for end-to-end client/aggregator pipelines.

Limitations
  - Each dimension is reported independently without joint estimation.
  - Only GRR is supported in the current implementation.
"""
# 说明：封装多维离散特征的逐维频率估计应用。
# 职责：
# - 为每个维度构建编码器与 GRR 扰动流程并输出独立 LDPReport
# - 服务端按维度聚合频率估计并打包为 marginals 输出
# - 通过 metadata 标记维度名称以支持分组聚合

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.consistency import ConsistencyPostProcessor
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.encoders import CategoricalEncoder, NumericalBucketsEncoder
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.types import Estimate, LDPReport


@dataclass
class MarginalSpec:
    """
    Specification for a single marginal dimension.

    - Configuration
      - name: Dimension name used in input records.
      - type: "categorical" or "numerical".
      - categories: Optional categories for categorical dimensions.
      - num_buckets: Optional bucket count for numerical dimensions.
      - clip_range: Optional clipping range for numerical dimensions.

    - Behavior
      - Validates configuration for the selected dimension type.

    - Usage Notes
      - Numerical dimensions require num_buckets and an optional clip_range.
    """

    name: str
    type: str = "categorical"
    categories: Optional[Sequence[Any]] = None
    num_buckets: Optional[int] = None
    clip_range: Optional[Tuple[float, float]] = None

    def __post_init__(self) -> None:
        # 校验维度名称与类型并检查数值分桶配置
        if not self.name:
            raise ParamValidationError("marginal name must be non-empty")
        self.type = str(self.type).lower()
        if self.type not in {"categorical", "numerical"}:
            raise ParamValidationError("marginal type must be 'categorical' or 'numerical'")
        if self.categories is not None and len(self.categories) == 0:
            raise ParamValidationError("categories must be non-empty when provided")
        if self.type == "numerical":
            if self.num_buckets is None or self.num_buckets <= 0:
                raise ParamValidationError("num_buckets must be positive for numerical marginals")
            if self.clip_range is not None and self.clip_range[0] >= self.clip_range[1]:
                raise ParamValidationError("clip_range must satisfy min < max")


@dataclass
class MarginalsClientConfig:
    """
    Client-side configuration for marginals.

    - Configuration
      - epsilon_per_dimension: Privacy budget for each dimension.
      - marginals: Sequence of MarginalSpec entries.
      - mechanism: Mechanism identifier; currently only "grr".

    - Behavior
      - Validates epsilon and mechanism identifiers.

    - Usage Notes
      - Each marginal is reported independently.
    """

    epsilon_per_dimension: float
    marginals: Sequence[MarginalSpec]
    mechanism: str = "grr"

    def __post_init__(self) -> None:
        # 校验 epsilon 与维度列表并规范机制标识
        ensure_epsilon(self.epsilon_per_dimension)
        if len(self.marginals) == 0:
            raise ParamValidationError("marginals must be non-empty")
        if not self.mechanism:
            raise ParamValidationError("mechanism must be non-empty")
        self.mechanism = str(self.mechanism).lower()
        if self.mechanism not in {"grr"}:
            raise ParamValidationError("unsupported mechanism for marginals")


@dataclass
class MarginalsServerConfig:
    """
    Server-side configuration for marginals.

    - Configuration
      - normalize: Whether to apply consistency post-processing.

    - Behavior
      - Controls whether a post-processor wraps per-dimension aggregators.

    - Usage Notes
      - Normalization is a post-processing step and does not affect privacy.
    """

    normalize: bool = True


class MarginalsAggregator(BaseAggregator):
    """
    Aggregate per-dimension reports into a marginals summary.

    - Configuration
      - per_dimension: Mapping of dimension names to aggregators.

    - Behavior
      - Aggregates reports per dimension and returns a combined estimate.
      - Records per-dimension metadata and missing dimensions.

    - Usage Notes
      - Expects each report to include a "dimension" metadata field.
    """

    def __init__(self, per_dimension: Mapping[str, BaseAggregator]) -> None:
        # 记录每个维度的聚合器用于按维度汇总
        if not per_dimension:
            raise ParamValidationError("per_dimension aggregators must be non-empty")
        self.per_dimension = dict(per_dimension)

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 按维度分组报告并输出每个维度的频率估计
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        grouped: Dict[str, list[LDPReport]] = {name: [] for name in self.per_dimension}
        for report in reports:
            meta = report.metadata or {}
            dimension = meta.get("dimension")
            if dimension is None:
                raise ParamValidationError("report missing dimension metadata")
            dim_key = str(dimension)
            if dim_key not in grouped:
                raise ParamValidationError(f"unknown dimension '{dim_key}'")
            grouped[dim_key].append(report)

        points: Dict[str, Any] = {}
        per_dimension_metadata: Dict[str, Any] = {}
        missing_dimensions = []
        for dim_name, aggregator in self.per_dimension.items():
            reports_for_dim = grouped.get(dim_name, [])
            if not reports_for_dim:
                missing_dimensions.append(dim_name)
                continue
            estimate = aggregator.aggregate(reports_for_dim)
            points[dim_name] = estimate.point
            per_dimension_metadata[dim_name] = estimate.metadata

        metadata: Mapping[str, Any] = {
            "dimensions": list(self.per_dimension.keys()),
            "missing_dimensions": missing_dimensions,
            "per_dimension": per_dimension_metadata,
        }

        return Estimate(
            metric="marginals",
            point=points,
            variance=None,
            confidence_interval=None,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 汇总维度列表与内部聚合器类型
        return {
            "type": "marginals",
            "dimensions": list(self.per_dimension.keys()),
            "aggregators": {name: agg.get_metadata() for name, agg in self.per_dimension.items()},
        }

    def reset(self) -> None:
        # 将重置操作转发给各维度聚合器
        for aggregator in self.per_dimension.values():
            aggregator.reset()
        return None


class MarginalsApplication(BaseLDPApplication):
    """
    End-to-end per-dimension marginals application.

    - Configuration
      - client_config: Client configuration for per-dimension reporting.
      - server_config: Server configuration for aggregation.

    - Behavior
      - Builds per-dimension clients and aggregators for marginal estimation.
      - Reports each dimension independently using GRR.

    - Usage Notes
      - Encoders must be fitted or provided with categories as needed.
    """

    def __init__(self, client_config: MarginalsClientConfig, server_config: Optional[MarginalsServerConfig] = None) -> None:
        # 保存配置并为每个维度构建编码器
        self.client_config = client_config
        self.server_config = server_config or MarginalsServerConfig()
        self._per_dimension: Dict[str, Dict[str, Any]] = {}

        for spec in client_config.marginals:
            if spec.name in self._per_dimension:
                raise ParamValidationError(f"duplicate marginal name '{spec.name}'")
            if spec.type == "categorical":
                encoder = CategoricalEncoder(categories=spec.categories)
            else:
                encoder = NumericalBucketsEncoder(
                    num_buckets=spec.num_buckets,
                    clip_range=spec.clip_range,
                )
                if spec.clip_range is not None:
                    encoder.fit([spec.clip_range[0], spec.clip_range[1]])
            self._per_dimension[spec.name] = {
                "spec": spec,
                "encoder": encoder,
                "mechanism": None,
            }

    def _ensure_encoder_ready(self, name: str) -> None:
        # 确保指定维度的编码器已完成拟合
        encoder = self._per_dimension[name]["encoder"]
        if hasattr(encoder, "is_fitted") and not encoder.is_fitted:
            raise ParamValidationError(f"encoder for dimension '{name}' must be fitted")

    def _infer_domain_size(self, name: str) -> int:
        # 推断指定维度的类别数或分桶数量
        spec: MarginalSpec = self._per_dimension[name]["spec"]
        encoder = self._per_dimension[name]["encoder"]
        if spec.type == "numerical":
            return int(spec.num_buckets)
        if not encoder.is_fitted:
            raise ParamValidationError(f"encoder for dimension '{name}' must be fitted")
        return len(encoder.index_to_value)

    def _get_or_create_mechanism(self, name: str) -> GRRMechanism:
        # 获取或创建指定维度的 GRR 机制实例
        if self._per_dimension[name]["mechanism"] is None:
            domain_size = self._infer_domain_size(name)
            if domain_size <= 1:
                raise ParamValidationError("domain_size must be at least 2")
            self._per_dimension[name]["mechanism"] = GRRMechanism(
                epsilon=self.client_config.epsilon_per_dimension,
                domain_size=domain_size,
            )
        return self._per_dimension[name]["mechanism"]

    def build_client(self) -> Callable[[Mapping[str, Any], str], Sequence[LDPReport]]:
        # 构建客户端侧的多维上报函数并按维度生成 LDPReport
        base_metadata: Dict[str, Mapping[str, Any]] = {}
        for name, state in self._per_dimension.items():
            self._ensure_encoder_ready(name)
            spec: MarginalSpec = state["spec"]
            encoder = state["encoder"]
            mechanism = self._get_or_create_mechanism(name)
            base_metadata[name] = {
                "application": "marginals",
                "dimension": spec.name,
                "dimension_type": spec.type,
                "domain_size": mechanism.domain_size,
                "num_categories": mechanism.domain_size,
                "encoder": encoder.get_metadata(),
                "mechanism": mechanism.mechanism_id,
            }

        def client(raw_record: Mapping[str, Any], user_id: str) -> Sequence[LDPReport]:
            # 按维度编码并生成独立的 LDPReport 列表
            reports: list[LDPReport] = []
            for name, state in self._per_dimension.items():
                if name not in raw_record:
                    raise ParamValidationError(f"missing value for dimension '{name}'")
                encoder = state["encoder"]
                mechanism = self._get_or_create_mechanism(name)
                encoded = encoder.encode(raw_record[name])
                metadata = dict(base_metadata[name])
                reports.append(mechanism.generate_report(encoded, user_id=user_id, metadata=metadata))
            return reports

        return client

    def build_aggregator(self) -> BaseAggregator:
        # 构建按维度聚合频率的服务端聚合器
        per_dimension_aggregators: Dict[str, BaseAggregator] = {}
        for name, state in self._per_dimension.items():
            spec: MarginalSpec = state["spec"]
            encoder = state["encoder"]
            if spec.type == "categorical" and encoder.is_fitted:
                num_categories = len(encoder.index_to_value)
            else:
                num_categories = int(spec.num_buckets) if spec.type == "numerical" else None
            frequency_aggregator = FrequencyAggregator(
                num_categories=num_categories,
                mechanism=self.client_config.mechanism,
            )
            if self.server_config.normalize:
                per_dimension_aggregators[name] = ConsistencyPostProcessor(frequency_aggregator)
            else:
                per_dimension_aggregators[name] = frequency_aggregator
        return MarginalsAggregator(per_dimension_aggregators)
