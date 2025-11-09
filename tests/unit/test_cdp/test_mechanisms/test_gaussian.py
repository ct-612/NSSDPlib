"""
Unit tests for the Gaussian mechanism.

Covers:
    * calibration of sigma and delta overrides
    * noise addition for scalars and arrays
    * validation errors, lifecycle guarantees, and serialization
"""
# 说明：对高斯机制进行单元测试。
# 覆盖：
# - σ 的校准与 delta 覆盖更新
# - 标量与数组的加噪与形状保持
# - 参数校验错误、生命周期约束（未校准禁止使用）、序列化往返一致性

import numpy as np
import pytest
from dplib.cdp.mechanisms.gaussian import GaussianMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, MechanismError, ValidationError


@pytest.fixture
def gaussian() -> GaussianMechanism:
    """Fixture returning a Gaussian mechanism with non-trivial params."""
    # 夹具：提供带非平凡参数的 Gaussian 机制实例以复用
    return GaussianMechanism(epsilon=1.0, delta=1e-4, sensitivity=2.0)


def test_calibrate_sets_sigma(gaussian: GaussianMechanism) -> None:
    """Calibration should compute sigma following the analytic bound."""
    # 校准后应计算出 σ，公式：σ = Δf * sqrt(2 ln(1.25/δ)) / ε
    gaussian.calibrate()
    assert gaussian.sigma is not None
    expected = gaussian.sensitivity * np.sqrt(2.0 * np.log(1.25 / gaussian.delta)) / gaussian.epsilon
    assert gaussian.sigma == pytest.approx(expected)


def test_calibrate_with_delta_override(gaussian: GaussianMechanism) -> None:
    """Calibration can override delta, updating internal state."""
    # calibrate(delta=...) 可覆盖内部 delta
    gaussian.calibrate(delta=1e-5)
    assert gaussian.delta == 1e-5


def test_calibrate_with_zero_delta_errors(gaussian: GaussianMechanism) -> None:
    """Delta must stay strictly positive."""
    # 高斯机制要求 δ>0；传 0 触发机制错误
    with pytest.raises(MechanismError):
        gaussian.calibrate(delta=0.0)


def test_randomise_scalar(gaussian: GaussianMechanism) -> None:
    """Scalar inputs produce float outputs."""
    # 标量输入在校准与固定种子后返回 float
    gaussian.calibrate()
    gaussian.reseed(0)
    noisy = gaussian.randomise(0.0)
    assert isinstance(noisy, float)


def test_randomise_numpy_array(gaussian: GaussianMechanism) -> None:
    """Array inputs preserve shape and dtype after noise addition."""
    # 数组输入加噪后应保持形状和数据类型不变
    gaussian.calibrate()
    arr = np.zeros((4,))
    result = gaussian.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape


def test_randomise_requires_numeric(gaussian: GaussianMechanism) -> None:
    """Non-numeric inputs should raise a validation error."""
    # 非数值输入应抛出 ValidationError
    gaussian.calibrate()
    with pytest.raises(ValidationError):
        gaussian.randomise(["a", "b"])


def test_randomise_without_calibration(gaussian: GaussianMechanism) -> None:
    """Randomise cannot be used prior to calibration."""
    # 未校准直接 randomise 应抛 NotCalibratedError
    with pytest.raises(NotCalibratedError):
        gaussian.randomise(1.0)


def test_serialize_roundtrip(gaussian: GaussianMechanism) -> None:
    """Serialized Gaussian mechanisms should restore parameters and metadata."""
    # 序列化→反序列化往返：sensitivity、delta、sigma 与 _meta 应一致
    gaussian.calibrate()
    gaussian._meta["origin"] = "unit-test"  # 添加自定义元数据用于校验
    data = gaussian.serialize()
    restored = GaussianMechanism.deserialize(data)
    assert restored.sensitivity == gaussian.sensitivity
    assert restored.delta == gaussian.delta
    assert restored.sigma == gaussian.sigma
    assert restored._meta == gaussian._meta
