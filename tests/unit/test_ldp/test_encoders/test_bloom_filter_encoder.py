"""
Unit tests for the BloomFilterEncoder helper.
"""
# 说明：针对 BloomFilterEncoder 的 Bloom Filter 编码行为进行单元测试。
# 覆盖：
# - Bloom Filter 编码后向量长度与 bit 取值范围
# - 在固定随机种子下相同输入编码结果的一致性
# - 不同输入值对应编码结果在统计意义上的区分能力

import numpy as np
import pytest

from dplib.ldp.encoders.bloom_filter import BloomFilterEncoder


def _to_list(bits):
    # 将编码结果统一转换为 Python list 形式便于断言和统计操作
    # 支持 bitarray 或 list/ndarray 的统一转换
    if hasattr(bits, "tolist"):
        return list(bits.tolist())
    return list(bits)


def test_bloom_filter_encoder_output_length():
    # 验证编码得到的 Bloom Filter 向量长度正确且激活 bit 数不超过 num_hashes
    bloom_size = 32
    num_hashes = 3
    encoder = BloomFilterEncoder(num_bits=bloom_size, num_hashes=num_hashes, seed=1)

    bits = encoder.encode("foo")
    bits_list = _to_list(bits)
    assert len(bits_list) == bloom_size
    assert set(bits_list).issubset({0, 1})
    # Hash collisions may reduce active bits; should not exceed num_hashes.
    assert 0 < sum(bits_list) <= num_hashes


def test_bloom_filter_encoder_deterministic_for_same_input():
    # 验证在固定种子和参数下同一输入多次编码结果保持一致
    encoder = BloomFilterEncoder(num_bits=16, num_hashes=2, seed=7)
    first = _to_list(encoder.encode("bar"))
    second = _to_list(encoder.encode("bar"))
    assert first == second


def test_bloom_filter_encoder_different_inputs():
    # 验证不同输入在同一编码器下通常产生不同的 Bloom Filter 向量
    encoder = BloomFilterEncoder(num_bits=64, num_hashes=4, seed=21)
    foo_bits = np.array(_to_list(encoder.encode("foo")))
    bar_bits = np.array(_to_list(encoder.encode("bar")))
    assert not np.array_equal(foo_bits, bar_bits)
