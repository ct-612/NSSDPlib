"""Shared type definitions for the LDP subsystem."""
# 说明：LDP 子系统中共享的类型定义与配置/结果载体，实现编码值与报表对象的统一建模。
# 职责：
# - 定义本地报告、聚合估计以及客户端/服务端配置等关键数据结构
# - 提供 EncodedValue 的序列化与反序列化工具，适配 JSON 传输与可选 bitarray 依赖
# - 处理时间戳的 ISO 格式转换与解析，方便跨进程与跨语言集成

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
    """Structured local LDP report exchanged between client and aggregator."""
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
    """Container for aggregated estimates such as frequency, mean, variance, or quantile."""
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
    """Client-side configuration bundling encoder and mechanism choices."""
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
    """Server-side aggregation configuration, covering metric and aggregator parameters."""
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
