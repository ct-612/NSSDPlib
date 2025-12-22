"""
Property-based tests for the Local Differential Privacy (LDP) value encoders.
"""
# 说明：本地差分隐私（LDP）数值编码器（Unary, Binary）的属性测试。
# 覆盖：
# - UnaryEncoder 与 BinaryEncoder 的无损编码/解码往返一致性验证
# - 编码器对非法索引（负数、越界）与非法数值类型的边界防御
# - 编码结果的位向量长度及内容特征验证

import pytest
from hypothesis import given, strategies as st
from dplib.ldp.encoders.unary import UnaryEncoder, BinaryEncoder
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- UnaryEncoder
@given(st.data(), st.integers(min_value=1, max_value=100))
def test_unary_encoder_roundtrip(data, length):
    # 验证 Unary 编码在给定向量长度内能将整数索引转换为位向量并精准解码还原
    encoder = UnaryEncoder(length)
    # 基于生成的向量长度动态采样一个合法的目标索引
    i = data.draw(st.integers(min_value=0, max_value=length - 1))
    encoded = encoder.encode(i)
    decoded = encoder.decode(encoded)
    assert i == decoded


@given(st.integers(min_value=1, max_value=100))
def test_unary_encoder_invalid_index(length):
    # 确保 Unary 编码器能够拒绝对 [0, length) 范围外索引的编码请求
    encoder = UnaryEncoder(length)
    with pytest.raises(ParamValidationError):
        encoder.encode(-1)
    with pytest.raises(ParamValidationError):
        encoder.encode(length)


# --------------------------------------------------------------- BinaryEncoder
@given(st.data(), st.integers(min_value=1, max_value=10))
def test_binary_encoder_roundtrip(data, num_bits):
    # 验证二进制编码器在指定比特位宽下对所有可选整数值的编解码稳健性
    encoder = BinaryEncoder(num_bits)
    # 计算当前位宽能表示的最大整数上限
    max_val = (1 << num_bits) - 1
    val = data.draw(st.integers(min_value=0, max_value=max_val))
    encoded = encoder.encode(val)
    decoded = encoder.decode(encoded)
    assert val == decoded


@given(st.integers(min_value=1, max_value=10))
def test_binary_encoder_invalid_value(num_bits):
    # 检查二进制编码器是否能识别并拦截超出其位元表示能力的数值输入
    encoder = BinaryEncoder(num_bits)
    max_val = (1 << num_bits)
    with pytest.raises(ParamValidationError):
        encoder.encode(max_val)
    with pytest.raises(ParamValidationError):
        encoder.encode(-1)


def test_binary_encoder_output_length():
    # 确认二进制编码器生成的位向量（数组形式）长度严格符合预设的 bit 宽度
    encoder = BinaryEncoder(4)
    encoded = encoder.encode(5)
    assert len(encoded) == 4
