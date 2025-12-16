"""
Unit tests for the OUE LDP mechanism.
"""
# 说明：针对优化一元编码（OUE）本地差分隐私机制的单元测试。
# 覆盖：
# - 验证在 epsilon 为零或 p/q 超出合法概率区间时是否抛出预期异常
# - 检查随机化输出的比特向量长度是否与输入一致
# - 通过大样本模拟验证目标位置比特被置为 1 的概率高于其他位置

from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.discrete.oue import OUEMechanism


def test_oue_invalid_params() -> None:
    # 验证 OUE 机制在非法 epsilon 或 p/q 参数配置时抛出预期异常
    with pytest.raises(ParamValidationError):
        OUEMechanism(epsilon=0.0)
    with pytest.raises(ParamValidationError):
        OUEMechanism(epsilon=1.0, p=1.5)
    with pytest.raises(ParamValidationError):
        OUEMechanism(epsilon=1.0, q=-0.1)


def test_oue_output_length() -> None:
    # 检查 OUE 随机化后的比特向量长度是否与输入一致以保证形状不变
    bits = np.zeros(8, dtype=int)
    bits[3] = 1
    mech = OUEMechanism(epsilon=1.0)
    out = mech.randomise(bits)
    out_list = out.tolist() if hasattr(out, "tolist") else list(out)
    assert len(out_list) == len(bits)


def test_oue_empirical_bit_probabilities() -> None:
    # 通过重复采样统计目标索引与其他索引的 1 频率并验证目标索引概率更高
    bits = np.zeros(6, dtype=int)
    true_idx = 2
    bits[true_idx] = 1
    mech = OUEMechanism(epsilon=1.0)
    n = 20000
    ones_true = 0
    ones_other = np.zeros(len(bits) - 1, dtype=int)
    other_indices = [i for i in range(len(bits)) if i != true_idx]
    for _ in range(n):
        out = mech.randomise(bits)
        out_arr = np.asarray(out, dtype=int)
        ones_true += out_arr[true_idx]
        ones_other += out_arr[other_indices]
    freq_true = ones_true / n
    freq_other = ones_other.mean() / n
    assert 0.0 < freq_other < 1.0
    assert 0.0 < freq_true < 1.0
    assert freq_true > freq_other
