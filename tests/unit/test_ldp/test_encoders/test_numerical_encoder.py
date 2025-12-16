"""
Unit tests for the NumericalBucketsEncoder used in LDP pipelines.
"""
# 说明：针对 NumericalBucketsEncoder 的数值分桶编码与解码行为进行单元测试。
# 覆盖：
# - 验证拟合后单值编码结果的索引类型且索引值在合法范围内
# - 验证解码得到的代表值是否位于对应分桶区间内部
# - 对落在原始范围之外输入的边界进行截断并验证桶索引映射逻辑
# - 批量编码/解码时输出形状与 dtype 是否符合预期
# - 基于 quantile 策略的分桶边界与各桶样本数分布是否合理

import numpy as np
import pytest

from dplib.ldp.encoders.numerical import NumericalBucketsEncoder


def test_numerical_encoder_fit_and_encode():
    # 验证在已拟合分桶边界下，若干典型数值被映射为合法整型桶索引
    data = np.array([0.0, 1.0, 2.0, 3.0])
    encoder = NumericalBucketsEncoder(num_buckets=4)
    encoder.fit(data)

    for val in [0.0, 0.5, 2.5, 3.0]:
        idx = encoder.encode(val)
        assert isinstance(idx, (int, np.integer))
        assert 0 <= idx < encoder.num_buckets


def test_numerical_encoder_decode_returns_bucket_representative():
    # 验证 decode 返回的代表值是否位于对应桶的区间 [edges[idx], edges[idx+1]] 内
    encoder = NumericalBucketsEncoder(num_buckets=4)
    encoder.fit([0.0, 1.0, 2.0, 3.0])

    idx = 2
    decoded = encoder.decode(idx)
    # 分桶的中心点应该落在该桶的边界之内
    edges = encoder.edges
    assert edges is not None
    assert edges[idx] <= decoded <= edges[idx + 1]


def test_numerical_encoder_out_of_range_handling():
    # 验证远小于/大于训练数据范围的输入应被映射到首桶或末桶索引
    encoder = NumericalBucketsEncoder(num_buckets=4)
    encoder.fit([0.0, 1.0, 2.0, 3.0])

    low_idx = encoder.encode(-10.0)
    high_idx = encoder.encode(100.0)
    assert low_idx == 0
    assert high_idx == encoder.num_buckets - 1


def test_numerical_encoder_batch_encode_decode_shape():
    # 验证批量编码与解码后的形状保持一致且 dtype 分别为整型/浮点型
    encoder = NumericalBucketsEncoder(num_buckets=4)
    encoder.fit([0.0, 1.0, 2.0, 3.0])

    values = np.array([0.1, 1.5, 2.6])
    encoded = np.array([encoder.encode(v) for v in values])
    decoded = np.array([encoder.decode(i) for i in encoded])

    assert encoded.shape == values.shape
    assert decoded.shape == values.shape
    assert encoded.dtype.kind in {"i", "u"}
    assert decoded.dtype.kind == "f"


def test_numerical_encoder_quantile_strategy_balances_counts():
    # 验证基于分位数的自适应桶分配使得不同区间的数量更加平衡
    data = np.array([0.0] * 20 + [1.0] * 20 + [2.0] * 20 + [10.0] * 40)
    encoder = NumericalBucketsEncoder(num_buckets=4, strategy="quantile")
    encoder.fit(data)

    edges = encoder.edges
    assert edges is not None
    # 分位数边界允许个别重复（尾部分布陡峭），但应保持非减且覆盖原始范围
    assert np.all(np.diff(edges) >= 0)
    assert edges[0] <= data.min() + 1e-12 and edges[-1] >= data.max() - 1e-12
    assert len(np.unique(edges)) > 1

    assignments = np.array([encoder.encode(v) for v in data])
    counts = np.bincount(assignments, minlength=encoder.num_buckets)
    # 各桶数量不能为 0 且不应过于失衡
    assert counts.min() > 0
    assert counts.max() / counts.min() < 3.0
