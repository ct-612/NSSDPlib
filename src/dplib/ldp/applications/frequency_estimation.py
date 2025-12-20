"""
Frequency estimation pipeline for categorical data under LDP.

Responsibilities:
    * build client-side encoding and GRR perturbation
    * build server-side frequency aggregation with optional normalization

Notes:
    Heavy hitters can be derived by applying top-k selection to the output.
"""
# 说明：封装类别值到完整频率分布估计的 LDP 端到端应用。
# 职责：
# - 构建客户端编码与 GRR 扰动流程输出 LDPReport
# - 构建服务端频率聚合器并可选执行一致性后处理
# - 提供完整频率分布输出作为通用频率估计入口

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.consistency import ConsistencyPostProcessor
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.types import LDPReport


@dataclass
class FrequencyEstimationClientConfig:
    """Client-side configuration for frequency estimation."""

    epsilon: float
    categories: Optional[Sequence[Any]] = None
    mechanism: str = "grr"

    def __post_init__(self) -> None:
        # 校验 epsilon 并规范机制标识
        ensure_epsilon(self.epsilon)
        if self.categories is not None and len(self.categories) == 0:
            raise ParamValidationError("categories must be non-empty when provided")
        if not self.mechanism:
            raise ParamValidationError("mechanism must be non-empty")
        self.mechanism = str(self.mechanism).lower()
        if self.mechanism not in {"grr"}:
            raise ParamValidationError("unsupported mechanism for frequency estimation")


@dataclass
class FrequencyEstimationServerConfig:
    """Server-side configuration for frequency estimation."""

    normalize: bool = True


class FrequencyEstimationApplication(BaseLDPApplication):
    """
    End-to-end frequency estimation application.

    Notes:
        The current implementation only supports GRR.

    TODO:
        * add OUE/OLH/RAPPOR mechanisms and hashing encoders
        * decide whether to expose encoder fit helpers or accept pre-fitted encoder injection with validation rules
    """

    def __init__(self, client_config: FrequencyEstimationClientConfig, server_config: Optional[FrequencyEstimationServerConfig] = None) -> None:
        # 保存客户端与服务端配置并准备类别编码器
        self.client_config = client_config
        self.server_config = server_config or FrequencyEstimationServerConfig()
        self._encoder = CategoricalEncoder(categories=client_config.categories)
        self._mechanism: Optional[GRRMechanism] = None

    def _ensure_encoder_fitted(self) -> None:
        # 确保类别编码器已完成拟合以便获取稳定词表
        if not self._encoder.is_fitted:
            raise ParamValidationError("categories must be provided or encoder must be fitted")

    def _get_domain_size(self) -> int:
        # 计算 GRR 使用的类别数并校验至少包含两个类别
        self._ensure_encoder_fitted()
        domain_size = len(self._encoder.index_to_value)
        if domain_size <= 1:
            raise ParamValidationError("domain_size must be at least 2")
        return domain_size

    def _get_or_create_mechanism(self) -> GRRMechanism:
        # 在首次使用时构造 GRR 机制并缓存
        if self._mechanism is None:
            domain_size = self._get_domain_size()
            self._mechanism = GRRMechanism(epsilon=self.client_config.epsilon, domain_size=domain_size)
        return self._mechanism

    def build_client(self) -> Callable[[Any, str], LDPReport]:
        # 构建客户端侧的类别上报函数
        self._ensure_encoder_fitted()
        encoder = self._encoder
        mechanism = self._get_or_create_mechanism()
        encoder_metadata = encoder.get_metadata()
        base_metadata = {
            "application": "frequency_estimation",
            "encoder": encoder_metadata,
            "domain_size": mechanism.domain_size,
            "num_categories": mechanism.domain_size,
            "prob_true": mechanism.prob_true,
            "prob_false": mechanism.prob_false,
            "mechanism": mechanism.mechanism_id,
        }

        def client(raw_value: Any, user_id: str) -> LDPReport:
            # 对单个类别值做编码与 GRR 扰动并生成 LDPReport
            encoded = encoder.encode(raw_value)
            metadata = dict(base_metadata)
            return mechanism.generate_report(encoded, user_id=user_id, metadata=metadata)

        return client

    def build_aggregator(self) -> BaseAggregator:
        # 构建服务端频率聚合器并按需附加一致性后处理
        num_categories = len(self._encoder.index_to_value) if self._encoder.is_fitted else None
        frequency_aggregator = FrequencyAggregator(
            num_categories=num_categories,
            mechanism=self.client_config.mechanism,
        )
        if self.server_config.normalize:
            return ConsistencyPostProcessor(frequency_aggregator)
        return frequency_aggregator
