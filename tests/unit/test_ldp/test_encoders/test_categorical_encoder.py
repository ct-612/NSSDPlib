"""
Unit tests for the CategoricalEncoder used in LDP pipelines.
"""
# 说明：针对 CategoricalEncoder 的编码/解码行为与未知类别处理策略进行单元测试。
# 覆盖：
# - fit 之后的 encode/decode 往返一致性与整数索引类型约束
# - 未知类别在未配置特殊 token 时的异常行为
# - 配置 "<UNK>" 占位符时未知类别映射逻辑
# - one-hot 编码与解码的形状、类型与索引一致性

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.encoders.categorical import CategoricalEncoder


def test_categorical_encoder_fit_and_encode_decode_round_trip():
    # 验证在已知类别集合上 fit 后，encode/decode 可保持值级往返一致且编码为整数索引
    categories = ["A", "B", "C"]
    encoder = CategoricalEncoder().fit(categories)

    inputs = ["A", "B", "A", "C"]
    encoded = [encoder.encode(v) for v in inputs]
    decoded = [encoder.decode(e) for e in encoded]

    assert decoded == inputs
    assert all(isinstance(e, (int, np.integer)) for e in encoded)


def test_categorical_encoder_unknown_category_behavior_raises():
    # 验证在未配置 unknown_value 时，编码未见过的类别会触发异常
    encoder = CategoricalEncoder().fit(["A", "B"])
    with pytest.raises(ParamValidationError):
        encoder.encode("C")


def test_categorical_encoder_unknown_category_maps_to_token():
    # 验证当显式提供 "<UNK>" 类别时，未知类别会映射到该占位符
    encoder = CategoricalEncoder(categories=["A", "B", "<UNK>"])
    # unknown_value 默认 "<UNK>"
    encoded = encoder.encode("C")
    decoded = encoder.decode(encoded)
    assert decoded == "<UNK>"


def test_categorical_encoder_output_shape_and_type():
    # 验证编码得到的整数索引与 one-hot 向量的形状、类型和 argmax 一致
    encoder = CategoricalEncoder(categories=["x", "y", "z"])
    idx = encoder.encode("y")
    assert isinstance(idx, (int, np.integer))
    assert idx == 1

    one_hot = encoder.encode_one_hot("y")
    assert isinstance(one_hot, np.ndarray)
    assert one_hot.shape == (3,)
    assert one_hot.dtype == int
    assert np.sum(one_hot) == 1
    assert np.argmax(one_hot) == idx
    assert encoder.decode_one_hot(one_hot) == "y"
