"""
Unit tests for the UnaryRandomizer LDP mechanism.
"""
# 说明：针对通用一元随机响应本地差分隐私机制的单元测试。
# 覆盖：
# - 验证非法 epsilon 或 p/q 超出合法概率区间时是否抛出预期异常
# - 检查随机化输出比特向量的形状是否与输入一致
# - 通过大样本模拟验证目标索引的置 1 频率明显高于其他索引

from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.discrete.unary_randomizer import UnaryRandomizer


def test_unary_randomizer_invalid_params() -> None:
    # 验证在 epsilon 为零或 p/q 超出 [0, 1] 时会抛出预期异常
    with pytest.raises(ParamValidationError):
        UnaryRandomizer(epsilon=0.0, p=0.5, q=0.5)
    with pytest.raises(ParamValidationError):
        UnaryRandomizer(epsilon=1.0, p=1.2, q=0.5)
    with pytest.raises(ParamValidationError):
        UnaryRandomizer(epsilon=1.0, p=0.5, q=-0.1)


def test_unary_randomizer_output_shape() -> None:
    # 检查随机化后输出比特数组的形状是否与输入保持一致
    x = np.zeros(5, dtype=int)
    x[2] = 1
    mech = UnaryRandomizer(epsilon=1.0, p=0.8, q=0.2)
    y = mech.randomise(x)
    y_arr = np.asarray(y, dtype=int)
    assert y_arr.shape == x.shape


def test_unary_randomizer_empirical_behavior() -> None:
    # 通过多次采样比较目标索引与其他索引被置 1 的经验频率以验证 (p, q) 行为差异
    x = np.zeros(6, dtype=int)
    true_idx = 4
    x[true_idx] = 1
    mech = UnaryRandomizer(epsilon=1.0, p=0.9, q=0.1)
    n = 20000
    ones_true = 0
    ones_other = np.zeros(len(x) - 1, dtype=int)
    other_indices = [i for i in range(len(x)) if i != true_idx]
    for _ in range(n):
        out = mech.randomise(x)
        out_arr = np.asarray(out, dtype=int)
        ones_true += out_arr[true_idx]
        ones_other += out_arr[other_indices]
    freq_true = ones_true / n
    freq_other = ones_other.mean() / n
    assert freq_true > freq_other + 0.1
