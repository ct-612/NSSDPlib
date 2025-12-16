"""
Unit tests for the RAPPOR LDP mechanism.
"""
# 说明：简化单阶段 RAPPOR 本地差分隐私机制的单元测试。
# 覆盖：
# - 验证非法 epsilon 与 p/q 参数配置时的异常抛出行为
# - 检查随机化后比特向量的长度与形状是否与输入一致
# - 验证输出比特模式既不会总为全零也几乎不会为全一

from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.discrete.rappor import RAPPORMechanism


def test_rappor_invalid_params() -> None:
    # 验证在 epsilon 为零或 p/q 超出合法概率范围时 RAPPOR 机制会抛出预期异常
    with pytest.raises(ParamValidationError):
        RAPPORMechanism(epsilon=0.0)
    with pytest.raises(ParamValidationError):
        RAPPORMechanism(epsilon=1.0, p=1.5)
    with pytest.raises(ParamValidationError):
        RAPPORMechanism(epsilon=1.0, q=-0.1)


def test_rappor_output_length() -> None:
    # 检查随机化后输出的比特数组形状是否与输入完全一致
    bits = np.array([1, 0, 0, 1, 0, 0, 1, 0], dtype=int)
    mech = RAPPORMechanism(epsilon=1.0)
    out = mech.randomise(bits)
    out_arr = np.asarray(out, dtype=int)
    assert out_arr.shape == bits.shape


def test_rappor_output_not_all_zero_or_one() -> None:
    # 通过多次采样检查输出既不是长期全零也几乎不会出现全为 1 的极端情况
    bits = np.array([0, 1, 0, 0, 1, 0, 0, 0], dtype=int)
    mech = RAPPORMechanism(epsilon=1.0)
    nonzero = 0
    nonone = 0
    n = 200
    for _ in range(n):
        out = np.asarray(mech.randomise(bits), dtype=int)
        if out.any():
            nonzero += 1
        if not out.all():
            nonone += 1
    # 期望样本中有相当比例至少包含一个被置 1 的比特，并且几乎所有样本都不应是所有比特都为 1 的向量
    assert nonzero > n * 0.2
    assert nonone >= n - 2
