"""
Unit tests for the Geometric mechanism.
"""
# 说明：GeometricMechanism（几何机制）的单元测试。
# 覆盖：
# - calibrate(...) 对衰减系数 decay 与成功概率 success_prob 的标定逻辑
# - randomise(...) 在标量/数组输入上的行为（整数类型保持与形状保持）
# - 未校准时调用 randomise 的保护（NotCalibratedError）
# - 敏感度非法（如 0）时的校验错误（ValidationError）
# - 序列化/反序列化往返对核心参数（sensitivity/decay/success_prob）的一致性

import math

import numpy as np
import pytest

from dplib.cdp.mechanisms.geometric import GeometricMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, ValidationError


@pytest.fixture
def geometric() -> GeometricMechanism:
    # 提供一个带默认 ε 与敏感度的几何机制实例，供各测试复用
    return GeometricMechanism(epsilon=1.0, sensitivity=1.0)


def test_calibrate_sets_decay_and_prob(geometric: GeometricMechanism) -> None:
    # 校准后应根据 ε/敏感度计算衰减系数和成功概率，并保证衰减系数位于 (0, 1) 区间
    geometric.calibrate()
    expected_prob = 1.0 - math.exp(-geometric.epsilon / geometric.sensitivity)
    assert geometric.success_prob == pytest.approx(expected_prob)
    assert 0.0 < geometric.decay < 1.0  # type: ignore[operator]


def test_randomise_preserves_integer_output(geometric: GeometricMechanism) -> None:
    # 对整数标量加噪后仍应返回整数类型（通过内部整数恢复逻辑保证）
    geometric.calibrate()
    geometric.reseed(123)
    noisy = geometric.randomise(5)
    assert isinstance(noisy, int)


def test_randomise_preserves_array_shape(geometric: GeometricMechanism) -> None:
    # 数组输入加噪后应保持维度与形状不变
    geometric.calibrate()
    arr = np.zeros((2, 3), dtype=int)
    result = geometric.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape


def test_randomise_requires_calibration() -> None:
    # 未校准的机制不允许调用 randomise，应抛出 NotCalibratedError
    mech = GeometricMechanism(epsilon=1.0, sensitivity=1.0)
    with pytest.raises(NotCalibratedError):
        mech.randomise(1)


def test_invalid_sensitivity_raises(geometric: GeometricMechanism) -> None:
    # 校准时若提供非法敏感度（如 0），应触发 ValidationError
    with pytest.raises(ValidationError):
        geometric.calibrate(sensitivity=0.0)


def test_serialize_roundtrip(geometric: GeometricMechanism) -> None:
    # 序列化→反序列化往返后，敏感度与几何参数应保持一致
    geometric.calibrate()
    data = geometric.serialize()
    restored = GeometricMechanism.deserialize(data)
    assert restored.sensitivity == geometric.sensitivity
    assert restored.decay == geometric.decay
    assert restored.success_prob == geometric.success_prob
