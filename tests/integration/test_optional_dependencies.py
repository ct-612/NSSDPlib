"""
Integration tests for LDP optional dependency helpers.
"""
# 说明：LDP 可选依赖与哈希编码器的集成测试
# 覆盖：
# - 哈希依赖缺失时的异常处理
# - Hash Bloom Sketch 编码器的输出形态
# - bitarray 存在与缺失时的降级行为
from __future__ import annotations

import pytest

from dplib.ldp import ldp_utils
from dplib.ldp.encoders import BloomFilterEncoder, HashEncoder, SketchEncoder


def _to_list(bits):
    # 将 bitarray 或数组统一转为 list 便于断言
    if hasattr(bits, "tolist"):
        return list(bits.tolist())
    return list(bits)


def test_hash_to_range_requires_hash_libs(monkeypatch) -> None:
    # 验证缺失哈希库时 hash_to_range 抛出 ImportError
    # 模拟哈希库不可用
    monkeypatch.setattr(ldp_utils, "xxhash", None)
    monkeypatch.setattr(ldp_utils, "mmh3", None)
    with pytest.raises(ImportError):
        ldp_utils.hash_to_range("value", seed=1, num_buckets=8)


def test_hash_encoders_work_with_hash_backend() -> None:
    # 验证哈希后端可用时编码器输出格式正确
    # 无可用后端时跳过
    if ldp_utils.xxhash is None and ldp_utils.mmh3 is None:
        pytest.skip("hash backend unavailable")

    # 构造哈希相关编码器并校验输出
    hash_encoder = HashEncoder(num_buckets=16, num_hashes=2, seed=1)
    encoded = hash_encoder.encode("alpha")
    assert isinstance(encoded, list)
    assert all(0 <= value < 16 for value in encoded)

    bloom_encoder = BloomFilterEncoder(num_bits=32, num_hashes=3, seed=2)
    bloom_bits = _to_list(bloom_encoder.encode("beta"))
    assert len(bloom_bits) == 32
    assert set(bloom_bits).issubset({0, 1})

    sketch_encoder = SketchEncoder(num_rows=4, num_buckets=8, seed=3)
    coords = sketch_encoder.encode("gamma")
    assert len(coords) == 4
    assert all(0 <= bucket < 8 for _, bucket in coords)


def test_make_bitarray_prefers_bitarray_when_available() -> None:
    # 验证 bitarray 可用时使用 bitarray 类型
    # 依赖缺失时跳过测试
    bitarray = pytest.importorskip("bitarray")
    bits = ldp_utils.make_bitarray(3, [0, 2])
    assert isinstance(bits, bitarray.bitarray)
    assert list(bits.tolist()) == [1, 0, 1]


def test_make_bitarray_fallback_to_list(monkeypatch) -> None:
    # 验证 bitarray 缺失时退化为 list
    # 模拟运行时未加载 bitarray
    monkeypatch.setattr(ldp_utils, "_BitArrayRuntime", None)
    bits = ldp_utils.make_bitarray(4, [1, 3])
    assert isinstance(bits, list)
    assert bits == [0, 1, 0, 1]
