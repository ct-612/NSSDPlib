"""
Unit tests for the OLH LDP mechanism.
"""
# 说明：针对优化局部哈希（OLH）本地差分隐私机制的参数校验与输出行为进行测试。
# 覆盖：
# - 验证非法 epsilon、domain_size 与 hash_range 组合时是否抛出预期异常
# - 检查随机化输出是否始终落在预期哈希区间 [0, hash_range) 内
# - 通过重复采样验证扰动输出不为常数以体现随机化特性

from __future__ import annotations

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.discrete.olh import OLHMechanism


def test_olh_invalid_params() -> None:
    # 验证在 epsilon 为零或域大小/哈希空间配置非法时会抛出相应异常
    with pytest.raises(ParamValidationError):
        OLHMechanism(epsilon=0.0, domain_size=4, hash_range=4)
    with pytest.raises(ParamValidationError):
        OLHMechanism(epsilon=1.0, domain_size=1, hash_range=4)
    with pytest.raises(ParamValidationError):
        OLHMechanism(epsilon=1.0, domain_size=4, hash_range=1)


def test_olh_output_range() -> None:
    # 检查对多个原始类别值随机化后输出是否始终位于 [0, hash_range) 的哈希空间
    hash_range = 8
    mech = OLHMechanism(epsilon=1.0, domain_size=10, hash_range=hash_range)
    values = [0, 3, 7]
    outputs = []
    for v in values:
        outputs.extend(mech.randomise(v) for _ in range(300))
    assert all(0 <= o < hash_range for o in outputs)


def test_olh_randomised_output_is_not_constant() -> None:
    # 通过重复对同一输入值采样检查输出取值是否多样化以验证随机性
    mech = OLHMechanism(epsilon=1.0, domain_size=10, hash_range=5)
    outs = [mech.randomise(2) for _ in range(300)]
    assert len(set(outs)) > 1