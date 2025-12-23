"""
Shared type definitions for the LDP subsystem.

Responsibilities
  - Define report, configuration, and per-user budget tracking types.
  - Provide EncodedValue serialization helpers for JSON transport.
  - Normalize timestamp formats for cross-process integration.
  - Expose LDP-to-CDP mapping payloads for accounting bridges.

Usage Context
  - Use as shared payload types between LDP clients, aggregators, and accounting.
  - Intended for serialization and inter-process transport.

Limitations
  - EncodedValue serialization relies on optional bitarray support when available.
  - Payloads store declared values and do not validate mechanism behavior.
"""
# 说明：LDP 子系统中共享的类型定义与配置/结果载体，覆盖编码载荷与预算跟踪对象。
# 职责：
# - 定义本地报告、聚合估计、客户端/服务端配置以及 per-user 预算统计等关键数据结构
# - 提供 EncodedValue 的序列化与反序列化工具，适配 JSON 传输与可选 bitarray 依赖
# - 处理时间戳的 ISO 格式转换与解析，方便跨进程与跨语言集成
# - 提供 LDP 到 CDP 的映射载体用于会计桥接场景

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

try:
    from bitarray import bitarray as _BitArrayRuntime
except Exception:  # pragma: no cover - optional dependency may be absent
    # 可选依赖 bitarray 缺失时退化为 None，并通过类型 Any 保持接口可用
    _BitArrayRuntime = None  # type: ignore

if TYPE_CHECKING:
    from bitarray import bitarray as BitArrayType
else:
    BitArrayType = Any


EncodedValue = Union[int, float, np.ndarray, "BitArrayType", Sequence[int]]
# 表示在 encoders -> mechanisms -> aggregators 之间传递的编码或扰动后的数值载体


def _serialize_encoded(value: EncodedValue) -> Tuple[Any, Optional[str]]:
    """Convert EncodedValue into a JSON-friendly payload with a type tag."""
    # 将 EncodedValue 规范化为 JSON 友好的基础类型并携带类型标签便于还原
    if isinstance(value, np.ndarray):
        return value.tolist(), "ndarray"
    if _BitArrayRuntime is not None and isinstance(value, _BitArrayRuntime):
        return [int(v) for v in value.tolist()], "bitarray"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value), "sequence"
    return value, None


def _deserialize_encoded(payload: Any, encoded_type: Optional[str]) -> EncodedValue:
    """Restore EncodedValue from a JSON-friendly payload using the type tag."""
    # 根据类型标签与载荷内容将 JSON 友好的表示恢复为 EncodedValue 约定的格式
    if encoded_type == "ndarray":
        return np.asarray(payload)
    if encoded_type == "bitarray":
        if _BitArrayRuntime is not None:
            ba = _BitArrayRuntime()
            ba.extend(payload)
            return ba
        return list(payload)
    if encoded_type == "sequence":
        return list(payload)
    if isinstance(payload, list):
        try:
            return np.asarray(payload)
        except Exception:
            return payload
    return payload


def _timestamp_to_iso(ts: Optional[datetime]) -> Optional[str]:
    # 将可选 datetime 转换为 ISO8601 字符串以便 JSON 序列化
    return ts.isoformat() if isinstance(ts, datetime) else None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    # 尝试从多种输入类型中解析出 datetime 对象，失败时返回 None
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


@dataclass
class LDPReport:
    """
    Structured local LDP report exchanged between client and aggregator.

    - Configuration
      - user_id: Optional user identifier for per-user accounting.
      - mechanism_id: Identifier of the local mechanism used to perturb data.
      - encoded: Encoded or perturbed value payload.
      - epsilon: Local privacy budget for the report.
      - delta: Optional delta for approximate local DP.
      - round_id: Optional round identifier for repeated collection.
      - timestamp: Optional event timestamp.
      - metadata: Additional metadata for auditing or routing.

    - Behavior
      - Serializes encoded values with a type tag for JSON transport.
      - Restores encoded values and timestamps when deserializing.

    - Usage Notes
      - Use for client-to-aggregator payload exchange.
    """
    # 表示客户端与聚合端之间交换的本地 LDP 报告载体，包含编码值与隐私参数等信息

    user_id: Optional[Union[str, int]]
    mechanism_id: str
    encoded: EncodedValue
    epsilon: float
    delta: float = 0.0
    round_id: Optional[Union[int, str]] = None
    timestamp: Optional[datetime] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将 LDPReport 转换为 JSON 友好的字典表示，包含编码类型标签与时间戳字符串
        encoded_payload, encoded_type = _serialize_encoded(self.encoded)
        return {
            "user_id": self.user_id,
            "mechanism_id": self.mechanism_id,
            "encoded": encoded_payload,
            "encoded_type": encoded_type,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "round_id": self.round_id,
            "timestamp": _timestamp_to_iso(self.timestamp),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LDPReport":
        """Create LDPReport from a dictionary, restoring encoded values and timestamp when possible."""
        # 从字典表示中重建 LDPReport，同时恢复编码载荷与时间戳等字段
        return cls(
            user_id=data.get("user_id"),
            mechanism_id=data["mechanism_id"],
            encoded=_deserialize_encoded(data.get("encoded"), data.get("encoded_type")),
            epsilon=float(data["epsilon"]),
            delta=float(data.get("delta", 0.0)),
            round_id=data.get("round_id"),
            timestamp=_parse_timestamp(data.get("timestamp")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Estimate:
    """
    Container for aggregated estimates such as frequency, mean, variance, or quantile.

    - Configuration
      - metric: Name of the estimated statistic.
      - point: Point estimate value.
      - variance: Optional variance or uncertainty measure.
      - confidence_interval: Optional confidence interval representation.
      - metadata: Additional metadata about the estimate.

    - Behavior
      - Stores estimate components and optionally converts array-like fields to numpy.

    - Usage Notes
      - Use as a standard output container for aggregators.
    """
    # 用于承载聚合后的估计结果，例如频率、均值、方差或分位数等统计量

    metric: str
    point: Any
    variance: Optional[Any] = None
    confidence_interval: Optional[Any] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_numpy(self) -> "Estimate":
        """Convert array-like fields to numpy.ndarray when possible."""
        # 尝试将点估计、方差和置信区间中的数组类字段转换为 numpy.ndarray 形式

        def _convert(value: Any) -> Any:
            if value is None:
                return None
            if isinstance(value, np.ndarray):
                return value
            if isinstance(value, Mapping):
                return {k: _convert(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)) or (
                isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))
            ):
                try:
                    return np.asarray(value)
                except Exception:
                    return value
            return value

        return Estimate(
            metric=self.metric,
            point=_convert(self.point),
            variance=_convert(self.variance),
            confidence_interval=_convert(self.confidence_interval),
            metadata=self.metadata,
        )


@dataclass
class LDPClientConfig:
    """
    Client-side configuration bundling encoder and mechanism choices.

    - Configuration
      - encoder_id: Identifier of the encoder used on raw values.
      - mechanism_id: Identifier of the local mechanism used on encoded values.
      - epsilon: Local privacy budget.
      - delta: Optional delta for approximate local DP.
      - encoder_params: Encoder-specific parameters.
      - mechanism_params: Mechanism-specific parameters.
      - metadata: Optional metadata for client configuration.

    - Behavior
      - Provides JSON-friendly serialization and deserialization helpers.

    - Usage Notes
      - Use to configure client-side encoding and perturbation.
    """
    # 本地客户端配置对象，打包 encoder 与 mechanism 选择及其参数和隐私预算

    encoder_id: str
    mechanism_id: str
    epsilon: float
    delta: float = 0.0
    encoder_params: Mapping[str, Any] = field(default_factory=dict)
    mechanism_params: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 将客户端配置导出为 JSON 友好的字典表示，便于网络传输或持久化
        return {
            "encoder_id": self.encoder_id,
            "mechanism_id": self.mechanism_id,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "encoder_params": dict(self.encoder_params),
            "mechanism_params": dict(self.mechanism_params),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LDPClientConfig":
        # 从字典还原客户端配置对象，并对 epsilon/delta 做基本类型转换
        return cls(
            encoder_id=data["encoder_id"],
            mechanism_id=data["mechanism_id"],
            epsilon=float(data["epsilon"]),
            delta=float(data.get("delta", 0.0)),
            encoder_params=data.get("encoder_params", {}),
            mechanism_params=data.get("mechanism_params", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AggregationConfig:
    """
    Server-side aggregation configuration covering metric and aggregator parameters.

    - Configuration
      - metric: Name of the metric to aggregate.
      - aggregator_id: Identifier of the aggregator implementation.
      - mechanism_id: Optional identifier of the aggregator-side mechanism.
      - params: Aggregator-specific parameters.
      - metadata: Additional metadata for aggregation.

    - Behavior
      - Provides JSON-friendly serialization and deserialization helpers.

    - Usage Notes
      - Use to configure server-side aggregation pipelines.
    """
    # 聚合端的配置对象，用于描述聚合指标、聚合器实现及其参数

    metric: str
    aggregator_id: str
    mechanism_id: Optional[str] = None
    params: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 将聚合配置导出为字典，方便在服务端或控制面之间传递
        return {
            "metric": self.metric,
            "aggregator_id": self.aggregator_id,
            "mechanism_id": self.mechanism_id,
            "params": dict(self.params),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AggregationConfig":
        # 从字典表示恢复聚合配置，并填充缺省参数字段
        return cls(
            metric=data["metric"],
            aggregator_id=data["aggregator_id"],
            mechanism_id=data.get("mechanism_id"),
            params=data.get("params", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class LocalPrivacyUsage:
    """
    Record of per-user epsilon usage for a local DP event.

    - Configuration
      - user_id: Optional user identifier.
      - epsilon: Epsilon spent for the event.
      - round_id: Optional round identifier.
      - metadata: Additional metadata for accounting.

    - Behavior
      - Stores a single usage record without additional validation.

    - Usage Notes
      - Use for per-user accounting summaries.
    """
    # 表示单次 LDP 事件的 epsilon 消耗记录，包含用户、轮次与元数据
    user_id: Optional[str]
    epsilon: float
    round_id: Optional[int] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class LDPBudgetSummary:
    """
    Summary of per-user epsilon usage for LDP accounting.

    - Configuration
      - total_epsilon: Total epsilon spent across all events.
      - per_user_epsilon: Mapping of user IDs to cumulative epsilon.
      - max_user_epsilon: Maximum epsilon spent by any single user.
      - n_events: Total number of events recorded.

    - Behavior
      - Stores summary values for reporting.

    - Usage Notes
      - Use for reporting per-user budget usage.
    """
    # 汇总 LDP 预算使用情况，包含总 epsilon 与 per-user 累计信息
    total_epsilon: float
    per_user_epsilon: Dict[str, float]
    max_user_epsilon: float
    n_events: int


@dataclass
class LDPToCDPEvent:
    """
    Mapping payload for forwarding LDP usage into CDP accounting.

    - Configuration
      - epsilon: Epsilon value for the mapped event.
      - delta: Delta value for the mapped event.
      - description: Optional event description.
      - metadata: Additional metadata for auditing.
      - mechanism: Optional mechanism identifier.
      - parameters: Mechanism parameter mapping.

    - Behavior
      - Carries declared values for downstream CDP accounting.

    - Usage Notes
      - Use when bridging LDP usage into CDP accounting workflows.
    """
    # 表示将 LDP usage 映射到 CDP 会计事件的载体，包含 delta 与机制参数
    epsilon: float
    delta: float = 0.0
    description: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    mechanism: Optional[str] = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
