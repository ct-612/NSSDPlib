"""
Extended property-based tests for LDP Encoders.
"""
# 说明：扩展本地差分隐私（LDP）编码器（BloomFilter, Hash, Numerical, Sketch）的属性测试。
# 覆盖：
# - BloomFilterEncoder 输出长度与哈希激活上限验证
# - HashEncoder 散列值在桶范围内的分布界限校验
# - NumericalBucketsEncoder 值域裁剪（clip）与编解码边界一致性
# - SketchEncoder 多行哈希桶结构的输出类型验证

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.ldp.encoders.bloom_filter import BloomFilterEncoder
from dplib.ldp.encoders.hashing import HashEncoder
from dplib.ldp.encoders.numerical import NumericalBucketsEncoder
from dplib.ldp.encoders.sketch import SketchEncoder
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- Bloom Filter
@given(st.integers(min_value=16, max_value=64),
       st.integers(min_value=1, max_value=4))
def test_bloom_filter_output(num_bits, num_hashes):
    # 验证布隆过滤器编码器生成的位向量长度准确且激活位总数不超过哈希函数数量
    encoder = BloomFilterEncoder(num_bits=num_bits, num_hashes=num_hashes)
    val = "test_string"
    encoded = encoder.encode(val)

    # 验证返回对象的可迭代性及长度约束
    assert hasattr(encoded, "__iter__") or isinstance(encoded, list)
    encoded_list = list(encoded)
    assert len(encoded_list) == num_bits
    assert sum(encoded_list) <= num_hashes


# ---------------------------------------------------------------- Hashing Encoder
@given(st.integers(min_value=2, max_value=100))
def test_hashing_encoder_domain(domain_size):
    # 验证哈希编码器能将任意输入映射到预设桶大小范围内的合法索引
    encoder = HashEncoder(num_buckets=domain_size)
    val = "any_input"
    encoded = encoder.encode(val)

    assert isinstance(encoded, (int, np.integer))
    assert 0 <= encoded < domain_size


# ---------------------------------------------------------------- Numerical Encoder
@given(st.floats(min_value=-10.0, max_value=10.0),
       st.floats(min_value=1.0, max_value=5.0))
def test_numerical_encoder_bounds(val, width):
    # 验证数值分桶编码器在配置裁剪范围后的编解码值域安全性
    min_val = -10.0
    max_val = min_val + width
    # 初始化 10 个桶并在给定范围内执行 clip
    encoder = NumericalBucketsEncoder(num_buckets=10,
                                      clip_range=(min_val, max_val))
    # 为分桶边缘设定执行数据拟合
    encoder.fit([min_val, max_val])

    encoded = encoder.encode(val)
    assert isinstance(encoded, (int, np.integer))
    decoded = encoder.decode(encoded)
    # 解码值必须落在裁剪边界内
    assert min_val <= decoded <= max_val


# ---------------------------------------------------------------- Sketch Encoder
@given(st.integers(min_value=10, max_value=50))
def test_sketch_encoder_shape(num_buckets):
    # 验证 Sketch 编码器针对单一输入生成的多行哈希索引列表结构
    encoder = SketchEncoder(num_buckets=num_buckets, num_rows=3)
    val = "item"
    encoded = encoder.encode(val)
    assert isinstance(encoded, list)
    # 校验输出规模符合 row 数量
    assert len(encoded) == 3
