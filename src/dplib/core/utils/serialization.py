"""
Serialization helpers for models and configuration.

Provides JSON helpers with optional masking and basic versioned payloads
to ease backwards compatibility.
"""
# 说明：序列化辅助工具，统一 JSON 编解码行为并内置简单的版本封装。
# 职责：
# - mask_sensitive_data：对给定字典中的敏感字段进行掩码处理，避免直接暴露敏感信息
# - serialize_to_json / deserialize_from_json：提供带可选敏感字段掩码与版本包装的 JSON 序列化/反序列化接口
# - 内部 _prepare：支持 dataclass 与自定义对象（实现 to_dict）的统一前处理
# - VersionedPayload：封装 version + payload 结构，提供 to_json / from_json 便捷方法，便于版本化持久化与兼容性演进

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, Iterable, Optional, Sequence

SensitiveFields = Sequence[str]


def mask_sensitive_data(payload: Dict[str, Any], sensitive_fields: SensitiveFields, mask: str = "***") -> Dict[str, Any]:
    # 对 payload 中指定字段进行掩码，返回浅拷贝后的新字典
    masked = dict(payload)
    for field in sensitive_fields:
        if field in masked:
            masked[field] = mask
    return masked


def _prepare(obj: Any) -> Any:
    # 将 dataclass 或实现了 to_dict 的对象转换为可 JSON 序列化的基础结构
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def serialize_to_json(
    obj: Any,
    *,
    sensitive_fields: Optional[SensitiveFields] = None,
    version: Optional[str] = None,
) -> str:
    # 将对象序列化为 JSON 字符串，支持敏感字段掩码与可选 version 包装
    payload = _prepare(obj)
    if isinstance(payload, dict) and sensitive_fields:
        payload = mask_sensitive_data(payload, sensitive_fields)
    if version is not None:
        payload = {"version": version, "payload": payload}
    return json.dumps(payload, default=_prepare, ensure_ascii=False)


def deserialize_from_json(text: str) -> Any:
    # 简单 JSON 反序列化包装，返回原始 Python 结构
    return json.loads(text)


@dataclass
class VersionedPayload:
    version: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        # 将当前实例（version + payload）序列化为 JSON 字符串
        return serialize_to_json({"version": self.version, "payload": self.payload})

    @classmethod
    def from_json(cls, text: str) -> "VersionedPayload":
        # 从 JSON 字符串构造 VersionedPayload，要求包含 version 与 payload 字段
        data = json.loads(text)
        if "version" not in data or "payload" not in data:
            raise ValueError("serialized payload missing version or payload fields")
        return cls(version=data["version"], payload=data["payload"])

