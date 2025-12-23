"""
Sequence analysis pipeline for event streams under LDP.

Responsibilities
  - Encode event sequences and perturb each position under GRR.
  - Aggregate unigram distributions per position or across positions.
  - Provide extension points for bigram or n-gram analysis.

Usage Context
  - Use for event sequence analysis with per-position reporting.
  - Intended for end-to-end client/aggregator pipelines.

Limitations
  - Only unigram statistics are supported in the current implementation.
  - Bigram estimation is not implemented.
"""
# 说明：封装事件序列的 LDP 上报与位置频率统计应用。
# 职责：
# - 对序列事件逐位置编码并使用 GRR 扰动
# - 服务端按位置统计 unigram 分布或整体分布
# - 预留 bigram 或 n-gram 统计的扩展入口

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.types import Estimate, LDPReport


@dataclass
class SequenceAnalysisClientConfig:
    """
    Client-side configuration for sequence analysis.

    - Configuration
      - epsilon_per_event: Privacy budget per event position.
      - max_length: Maximum number of positions to report.
      - categories: Optional categories for the encoder.

    - Behavior
      - Validates epsilon, max_length, and categories.

    - Usage Notes
      - Categories must be provided or the encoder must be fitted elsewhere.
    """

    epsilon_per_event: float
    max_length: int
    categories: Optional[Sequence[Any]] = None

    def __post_init__(self) -> None:
        # 校验 epsilon 与最大序列长度配置
        ensure_epsilon(self.epsilon_per_event)
        if self.max_length <= 0:
            raise ParamValidationError("max_length must be positive")
        if self.categories is not None and len(self.categories) == 0:
            raise ParamValidationError("categories must be non-empty when provided")


@dataclass
class SequenceAnalysisServerConfig:
    """
    Server-side configuration for sequence analysis.

    - Configuration
      - estimate_unigram: Whether to estimate unigram distributions.
      - estimate_bigram: Whether to estimate bigram distributions.

    - Behavior
      - Controls which sequence statistics are enabled.

    - Usage Notes
      - Bigram estimation is not implemented and will raise if enabled.
    """

    estimate_unigram: bool = True
    estimate_bigram: bool = False


class SequenceAggregator(BaseAggregator):
    """
    Aggregate per-position unigram distributions.

    - Configuration
      - per_position: Mapping of positions to frequency aggregators.

    - Behavior
      - Aggregates reports per position and returns a combined estimate.
      - Records per-position metadata and missing positions.

    - Usage Notes
      - Expects each report to include a "position" metadata field.
    """

    def __init__(self, per_position: Mapping[int, FrequencyAggregator]) -> None:
        # 记录每个位置的聚合器以生成按位置统计结果
        if not per_position:
            raise ParamValidationError("per_position aggregators must be non-empty")
        self.per_position = dict(per_position)

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 按位置分组报告并生成 unigram 分布估计
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        grouped: Dict[int, list[LDPReport]] = {pos: [] for pos in self.per_position}
        for report in reports:
            meta = report.metadata or {}
            position = meta.get("position")
            if position is None:
                raise ParamValidationError("report missing position metadata")
            pos_key = int(position)
            if pos_key not in grouped:
                raise ParamValidationError(f"position '{pos_key}' exceeds configured max_length")
            grouped[pos_key].append(report)

        points: Dict[int, Any] = {}
        per_position_metadata: Dict[int, Any] = {}
        missing_positions = []
        for pos, aggregator in self.per_position.items():
            reports_for_pos = grouped.get(pos, [])
            if not reports_for_pos:
                missing_positions.append(pos)
                continue
            estimate = aggregator.aggregate(reports_for_pos)
            points[pos] = estimate.point
            per_position_metadata[pos] = estimate.metadata

        metadata: Mapping[str, Any] = {
            "positions": list(self.per_position.keys()),
            "missing_positions": missing_positions,
            "per_position": per_position_metadata,
        }

        return Estimate(
            metric="sequence_unigram",
            point=points,
            variance=None,
            confidence_interval=None,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 汇总位置列表与内部聚合器元数据
        return {
            "type": "sequence",
            "positions": list(self.per_position.keys()),
            "aggregators": {pos: agg.get_metadata() for pos, agg in self.per_position.items()},
        }

    def reset(self) -> None:
        # 将重置操作传递给位置聚合器
        for aggregator in self.per_position.values():
            aggregator.reset()
        return None


class SequenceAnalysisApplication(BaseLDPApplication):
    """
    End-to-end sequence analysis application for event streams.

    - Configuration
      - client_config: Client configuration for sequence perturbation.
      - server_config: Server configuration for aggregation.

    - Behavior
      - Builds a client that perturbs events per position with GRR.
      - Builds a server-side aggregator for per-position unigram estimates.

    - Usage Notes
      - Bigram estimation will raise until implemented.
    """

    def __init__(self, client_config: SequenceAnalysisClientConfig, server_config: Optional[SequenceAnalysisServerConfig] = None) -> None:
        # 保存配置并准备事件编码器
        self.client_config = client_config
        self.server_config = server_config or SequenceAnalysisServerConfig()
        self._encoder = CategoricalEncoder(categories=client_config.categories)
        self._mechanism: Optional[GRRMechanism] = None

    def _ensure_encoder_fitted(self) -> None:
        # 确保事件编码器已完成拟合
        if not self._encoder.is_fitted:
            raise ParamValidationError("categories must be provided or encoder must be fitted")

    def _get_or_create_mechanism(self) -> GRRMechanism:
        # 获取或创建 GRR 机制实例用于序列扰动
        if self._mechanism is None:
            self._ensure_encoder_fitted()
            domain_size = len(self._encoder.index_to_value)
            if domain_size <= 1:
                raise ParamValidationError("domain_size must be at least 2")
            self._mechanism = GRRMechanism(
                epsilon=self.client_config.epsilon_per_event,
                domain_size=domain_size,
            )
        return self._mechanism

    def build_client(self) -> Callable[[Sequence[Any], str], Sequence[LDPReport]]:
        # 构建客户端侧的序列上报函数
        if self.server_config.estimate_bigram:
            raise ParamValidationError("bigram estimation is not implemented yet")
        self._ensure_encoder_fitted()
        encoder = self._encoder
        mechanism = self._get_or_create_mechanism()
        base_metadata = {
            "application": "sequence_analysis",
            "type": "unigram",
            "domain_size": mechanism.domain_size,
            "num_categories": mechanism.domain_size,
            "prob_true": mechanism.prob_true,
            "prob_false": mechanism.prob_false,
            "mechanism": mechanism.mechanism_id,
        }

        def client(events: Sequence[Any], user_id: str) -> Sequence[LDPReport]:
            # 按位置编码并生成 LDPReport 列表
            reports: list[LDPReport] = []
            for idx, event in enumerate(list(events)[: self.client_config.max_length]):
                encoded = encoder.encode(event)
                metadata = dict(base_metadata)
                metadata["position"] = idx
                reports.append(mechanism.generate_report(encoded, user_id=user_id, metadata=metadata))
            return reports

        return client

    def build_aggregator(self) -> BaseAggregator:
        # 构建按位置统计的频率聚合器
        if not self.server_config.estimate_unigram:
            raise ParamValidationError("unigram estimation must be enabled")
        if self.server_config.estimate_bigram:
            raise ParamValidationError("bigram estimation is not implemented yet")

        num_categories = len(self._encoder.index_to_value) if self._encoder.is_fitted else None
        per_position = {
            pos: FrequencyAggregator(num_categories=num_categories, mechanism="grr")
            for pos in range(self.client_config.max_length)
        }
        return SequenceAggregator(per_position)
