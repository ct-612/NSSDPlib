"""
Unit tests for serialization utilities.
"""
# 说明：序列化与敏感字段掩码相关工具的单元测试。
# 覆盖：
# - mask_sensitive_data：对指定键进行掩码替换
# - serialize_to_json / deserialize_from_json：支持 dataclass、敏感字段掩码的 JSON 往返
# - VersionedPayload：带 version + payload 结构的序列化/反序列化一致性

import dataclasses

from dplib.core.utils import (
    VersionedPayload,
    deserialize_from_json,
    mask_sensitive_data,
    serialize_to_json,
)


@dataclasses.dataclass
class Sample:
    a: int
    secret: str


def test_mask_sensitive_data() -> None:
    # 验证指定敏感字段会被统一替换为掩码字符串
    payload = {"a": 1, "secret": "value"}
    masked = mask_sensitive_data(payload, ["secret"])
    assert masked["secret"] == "***"


def test_serialize_and_deserialize_dataclass() -> None:
    # 验证 dataclass 对象序列化时敏感字段被掩码，反序列化后结构保持一致
    obj = Sample(a=5, secret="hidden")
    text = serialize_to_json(obj, sensitive_fields=["secret"])
    data = deserialize_from_json(text)
    assert data["a"] == 5
    assert data["secret"] == "***"


def test_versioned_payload_roundtrip() -> None:
    # 验证 VersionedPayload 的 JSON 序列化与 from_json 恢复过程往返一致
    payload = VersionedPayload(version="1.0", payload={"foo": "bar"})
    text = payload.to_json()
    restored = VersionedPayload.from_json(text)
    assert restored.version == "1.0"
    assert restored.payload["foo"] == "bar"
