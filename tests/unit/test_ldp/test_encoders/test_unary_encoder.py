"""
Unit tests for the UnaryEncoder/BinaryEncoder used in LDP bit-vector encoders.
"""
# 说明：针对 UnaryEncoder/ BinaryEncoder 的编码与解码行为进行单元测试。
# 覆盖：
# - Unary：合法索引往返一致性、one-hot 结构、越界抛异常
# - Binary：合法数值往返一致性、越界/长度校验抛异常

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.encoders.unary import BinaryEncoder, UnaryEncoder
from dplib.ldp.ldp_utils import count_ones


def test_unary_encoder_encode_decode_round_trip():
    # 验证多个合法索引经过编码与解码后能准确还原原始索引
    encoder = UnaryEncoder(length=5)
    for idx in [0, 2, 4]:
        encoded = encoder.encode(idx)
        decoded = encoder.decode(encoded)
        assert decoded == idx


def test_unary_encoder_output_vector_is_one_hot():
    # 验证编码结果为 one-hot 向量且激活位置与输入索引一致
    domain_size = 5
    encoder = UnaryEncoder(length=domain_size)
    idx = 3
    encoded = encoder.encode(idx)

    bits = list(encoded)
    assert len(bits) == domain_size
    assert count_ones(encoded) == 1
    assert bits[idx] == 1
    assert sum(bits) == 1


def test_unary_encoder_invalid_index():
    # 验证对负索引或超出长度范围的索引进行编码时抛出 ParamValidationError
    encoder = UnaryEncoder(length=4)
    with pytest.raises(ParamValidationError):
        encoder.encode(-1)
    with pytest.raises(ParamValidationError):
        encoder.encode(5)


def test_binary_encoder_encode_decode_round_trip():
    # 验证在位宽范围内的数值编码后可正确解码且长度符合预期
    encoder = BinaryEncoder(num_bits=4)
    for value in [0, 5, 15]:
        encoded = encoder.encode(value)
        assert len(encoded) == 4
        decoded = encoder.decode(encoded)
        assert decoded == value


def test_binary_encoder_invalid_value_and_length():
    # 验证负值、超出位宽或错误长度输入抛出 ParamValidationError
    encoder = BinaryEncoder(num_bits=3)
    with pytest.raises(ParamValidationError):
        encoder.encode(-1)
    with pytest.raises(ParamValidationError):
        encoder.encode(8)  # 超过 3bit 可表示上界
    with pytest.raises(ParamValidationError):
        encoder.decode([1, 0])  # 长度不匹配
