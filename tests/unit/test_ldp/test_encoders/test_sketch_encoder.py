"""
Unit tests for the SketchEncoder used in LDP pipelines.
"""
# 说明：针对 SketchEncoder 将输入值映射为 (row, bucket) 对结构的行为进行单元测试。
# 覆盖：
# - 编码结果的列表长度及每个元素的行索引、桶索引是否落在合法范围内
# - 相同输入在固定随机种子下编码结果是否保持确定性
# - 不同输入在相同配置下是否产生不同的编码结构以降低跨行碰撞概率

import pytest

from dplib.ldp.encoders.sketch import SketchEncoder


def test_sketch_encoder_structure_shape():
    # 验证编码得到的 (row_idx, bucket_idx) 列表长度应与行数一致且索引均在有效范围内
    num_rows = 4
    num_buckets = 64
    encoder = SketchEncoder(num_rows=num_rows, num_buckets=num_buckets, seed=0)

    encoded = encoder.encode("foo")
    assert isinstance(encoded, list)
    assert len(encoded) == num_rows
    for row_idx, bucket_idx in encoded:
        assert 0 <= row_idx < num_rows
        assert 0 <= bucket_idx < num_buckets


def test_sketch_encoder_deterministic_for_same_input():
    # 验证在相同配置与输入下编码结果是确定性的，便于重放和调试
    encoder = SketchEncoder(num_rows=3, num_buckets=32, seed=42)
    first = encoder.encode("bar")
    second = encoder.encode("bar")
    assert first == second


def test_sketch_encoder_different_inputs_vary():
    # 验证不同输入在相同 hash 配置下产生差异编码结构，避免跨行完全碰撞
    encoder = SketchEncoder(num_rows=3, num_buckets=256, seed=99)
    first = encoder.encode("alpha")
    second = encoder.encode("beta")
    assert first != second, "hash collisions across rows are unlikely for different inputs"
