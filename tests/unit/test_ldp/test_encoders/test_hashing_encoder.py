"""
Unit tests for the HashEncoder used in LDP pipelines.
"""
# 说明：针对 HashEncoder 的哈希编码行为进行单元测试。
# 覆盖：
# - 多哈希与单哈希配置下编码结果的类型与长度
# - 不同输入在相同配置下通常映射到不同哈希编码
# - 固定 num_buckets/num_hashes/seed 时编码结果的确定性

import pytest

from dplib.ldp.encoders.hashing import HashEncoder


def test_hashing_encoder_output_shape():
    # 验证多哈希与单哈希配置下编码输出的形态与取值范围
    num_buckets = 1024
    encoder = HashEncoder(num_buckets=num_buckets, num_hashes=2, seed=1)

    encoded = encoder.encode("foo")
    assert isinstance(encoded, list)
    assert len(encoded) == 2
    for idx in encoded:
        assert 0 <= idx < num_buckets

    encoder_single = HashEncoder(num_buckets=num_buckets, num_hashes=1, seed=2)
    encoded_single = encoder_single.encode("foo")
    assert isinstance(encoded_single, int)
    assert 0 <= encoded_single < num_buckets


def test_hashing_encoder_different_inputs_give_different_codes():
    # 验证在固定哈希参数下不同输入字符串通常得到不同的哈希编码
    encoder = HashEncoder(num_buckets=4096, num_hashes=2, seed=123)
    code_foo = encoder.encode("foo")
    code_bar = encoder.encode("bar")
    assert code_foo != code_bar, "hash collisions for both hashes are extremely unlikely"


def test_hashing_encoder_is_deterministic_for_same_input():
    # 验证相同输入在相同 num_buckets/num_hashes/seed 下编码结果具有确定性
    encoder = HashEncoder(num_buckets=2048, num_hashes=3, seed=7)
    first = encoder.encode("baz")
    second = encoder.encode("baz")
    assert first == second
