"""
Unit tests for the Vector mechanism.
"""
# 说明：VectorMechanism（向量机制）的单元测试。
# 覆盖：
# - Laplace 向量机制的标定逻辑（scale = sensitivity / epsilon）与加噪后形状保持
# - Gaussian 向量机制的标定逻辑（sigma 的解析计算公式）
# - Gaussian 分布下 delta ∈ (0,1) 的必要性（否则抛 MechanismError）
# - 未校准情况下 randomise(...) 的保护（NotCalibratedError）
# - 序列化/反序列化往返对 distribution/norm/sensitivity 等关键配置的一致性

import math

import numpy as np
import pytest

from dplib.cdp.mechanisms.vector import VectorMechanism
from dplib.core.privacy.base_mechanism import MechanismError, NotCalibratedError


@pytest.fixture
def laplace_vector() -> VectorMechanism:
    # 提供 Laplace 分布、L1 范数配置的向量机制实例，供相关测试复用
    return VectorMechanism(epsilon=2.0, delta=0.0, sensitivity=3.0, distribution="laplace", norm="l1")


@pytest.fixture
def gaussian_vector() -> VectorMechanism:
    # 提供 Gaussian 分布、L2 范数配置的向量机制实例，便于测试 sigma 标定与序列化
    return VectorMechanism(epsilon=1.0, delta=1e-5, sensitivity=2.0, distribution="gaussian", norm="l2")


def test_calibrate_laplace_sets_scale(laplace_vector: VectorMechanism) -> None:
    # Laplace 模式下 calibrate 应按 sensitivity/epsilon 设置 scale
    laplace_vector.calibrate()
    assert laplace_vector.scale == pytest.approx(laplace_vector.sensitivity / laplace_vector.epsilon)


def test_laplace_randomise_preserves_shape(laplace_vector: VectorMechanism) -> None:
    # Laplace 加噪应保持输入 ndarray 的形状不变
    laplace_vector.calibrate()
    arr = np.zeros((2, 2))
    result = laplace_vector.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape


def test_gaussian_calibration_sets_sigma(gaussian_vector: VectorMechanism) -> None:
    # Gaussian 模式下 calibrate 应按解析公式计算 sigma
    gaussian_vector.calibrate()
    expected = gaussian_vector.sensitivity * math.sqrt(
        2.0 * math.log(1.25 / gaussian_vector.delta)
    ) / gaussian_vector.epsilon
    assert gaussian_vector.sigma == pytest.approx(expected)


def test_gaussian_requires_positive_delta() -> None:
    # Gaussian 向量机制要求 delta ∈ (0,1)，否则校准时抛 MechanismError
    mech = VectorMechanism(epsilon=1.0, delta=1e-5, sensitivity=1.0, distribution="gaussian")
    with pytest.raises(MechanismError):
        mech.calibrate(delta=0.0)


def test_vector_requires_calibration() -> None:
    # 未调用 calibrate() 的向量机制不允许 randomise，应抛 NotCalibratedError
    mech = VectorMechanism(epsilon=1.0, delta=0.0, sensitivity=1.0, distribution="laplace")
    with pytest.raises(NotCalibratedError):
        mech.randomise([1.0, 2.0])


def test_serialize_roundtrip(gaussian_vector: VectorMechanism) -> None:
    # 序列化→反序列化往返后，应保持分布类型、范数及敏感度等配置一致
    gaussian_vector.calibrate()
    data = gaussian_vector.serialize()
    restored = VectorMechanism.deserialize(data)
    assert restored.distribution == gaussian_vector.distribution
    assert restored.norm == gaussian_vector.norm
    assert restored.sensitivity == gaussian_vector.sensitivity
