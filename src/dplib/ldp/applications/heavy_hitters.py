"""
Heavy hitters pipeline for categorical data under LDP.

Responsibilities:
    * build client-side encoding and GRR perturbation for categorical values
    * build server-side frequency aggregation for heavy hitters analysis
    * provide a helper to extract top-k categories from frequency estimates

Notes:
    The current implementation only supports GRR; OUE/OLH/RAPPOR can be added later.
"""
# 说明：封装类别值到 LDP 频率估计与 top-k 输出的端到端应用。
# 职责：
# - 组合 CategoricalEncoder 与 GRR 机制形成客户端上报函数
# - 构建频率聚合器供服务端统计高频类别
# - 提供 top-k 提取辅助函数以便输出重频项

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.applications.base import BaseLDPApplication
from dplib.ldp.aggregators.base import BaseAggregator
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.types import Estimate, LDPReport


@dataclass
class HeavyHittersClientConfig:
    """Client-side configuration for heavy hitters."""

    epsilon: float
    categories: Optional[Sequence[Any]] = None
    top_k: int = 10
    mechanism: str = "grr"

    def __post_init__(self) -> None:
        # 校验 epsilon 与 top_k 并规范机制标识
        ensure_epsilon(self.epsilon)
        if self.categories is not None and len(self.categories) == 0:
            raise ParamValidationError("categories must be non-empty when provided")
        if self.top_k <= 0:
            raise ParamValidationError("top_k must be positive")
        if not self.mechanism:
            raise ParamValidationError("mechanism must be non-empty")
        self.mechanism = str(self.mechanism).lower()
        if self.mechanism not in {"grr"}:
            raise ParamValidationError("unsupported mechanism for heavy hitters")


@dataclass
class HeavyHittersServerConfig:
    """Server-side configuration for heavy hitters."""

    top_k: int = 10
    min_support: float = 0.0

    def __post_init__(self) -> None:
        # 校验 top_k 与 min_support 取值范围
        if self.top_k <= 0:
            raise ParamValidationError("top_k must be positive")
        if self.min_support < 0:
            raise ParamValidationError("min_support must be non-negative")


class HeavyHittersAggregator(BaseAggregator):
    """Wrap FrequencyAggregator and attach category metadata."""

    def __init__(self, inner_aggregator: FrequencyAggregator, categories: Optional[Sequence[Any]] = None) -> None:
        # 组合频率聚合器并可选附加类别元数据
        if inner_aggregator is None:
            raise ParamValidationError("inner_aggregator is required")
        self.inner_aggregator = inner_aggregator
        self.categories = list(categories) if categories is not None else None

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 调用频率聚合器并在结果元数据中补充类别列表
        estimate = self.inner_aggregator.aggregate(reports)
        metadata = dict(estimate.metadata)
        if self.categories is not None:
            metadata.setdefault("categories", list(self.categories))
        return Estimate(
            metric=estimate.metric,
            point=estimate.point,
            variance=estimate.variance,
            confidence_interval=estimate.confidence_interval,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 汇总内部聚合器元数据并补充类别信息
        metadata = dict(self.inner_aggregator.get_metadata())
        if self.categories is not None:
            metadata["categories"] = list(self.categories)
        return metadata

    def reset(self) -> None:
        # 将重置动作传递给内部聚合器
        self.inner_aggregator.reset()
        return None


def extract_top_k(est: Estimate, top_k: int, min_support: float = 0.0) -> List[Tuple[Any, float]]:
    # 从频率估计中筛选 top-k 类别并可选过滤低支持度项
    if top_k <= 0:
        raise ParamValidationError("top_k must be positive")
    if min_support < 0:
        raise ParamValidationError("min_support must be non-negative")
    if est.metric != "frequency":
        raise ParamValidationError("estimate metric must be 'frequency'")

    frequencies = np.asarray(est.point, dtype=float).ravel()
    if frequencies.size == 0:
        return []

    metadata = est.metadata or {}
    categories = None
    meta_categories = metadata.get("categories")
    if isinstance(meta_categories, Sequence) and not isinstance(meta_categories, (str, bytes, bytearray)):
        categories = list(meta_categories)
    if categories is None:
        encoder_meta = metadata.get("encoder")
        if isinstance(encoder_meta, Mapping) and "categories" in encoder_meta:
            categories = list(encoder_meta.get("categories"))
    if categories is None or len(categories) != frequencies.size:
        categories = list(range(frequencies.size))

    pairs = [
        (category, float(freq))
        for category, freq in zip(categories, frequencies)
        if float(freq) >= min_support
    ]
    pairs.sort(key=lambda item: item[1], reverse=True)
    return pairs[:top_k]


class HeavyHittersApplication(BaseLDPApplication):
    """
    End-to-end heavy hitters application.

    Notes:
        The current implementation only supports GRR.

    TODO:
        * add OUE/OLH/RAPPOR and hashing-based encoders
        * decide whether to expose encoder fit helpers or accept pre-fitted encoder injection with validation rules
    """

    def __init__(self, client_config: HeavyHittersClientConfig, server_config: Optional[HeavyHittersServerConfig] = None) -> None:
        # 保存客户端与服务端配置并准备类别编码器
        self.client_config = client_config
        self.server_config = server_config or HeavyHittersServerConfig(top_k=client_config.top_k)
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
            "application": "heavy_hitters",
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
        # 构建服务端频率聚合器并附加类别元数据
        num_categories = len(self._encoder.index_to_value) if self._encoder.is_fitted else None
        frequency_aggregator = FrequencyAggregator(
            num_categories=num_categories,
            mechanism=self.client_config.mechanism,
        )
        categories = list(self._encoder.index_to_value) if self._encoder.is_fitted else None
        return HeavyHittersAggregator(frequency_aggregator, categories)
