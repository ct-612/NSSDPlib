"""
Unit tests for the Gaussian mechanism.

Covers:
    * calibration of sigma and delta overrides
    * noise addition for scalars and arrays
    * validation errors, lifecycle guarantees, and serialization
"""
# 说明：对高斯机制进行单元测试。
# 覆盖：
# - calibrate 根据 (ε, δ, sensitivity) 计算 σ，以及 delta 覆盖更新逻辑
# - randomise 对标量和 NumPy 数组添加噪声时的返回类型与形状保持
# - 非数值输入、未校准调用等情况下的 ValidationError / NotCalibratedError 分支
# - 校准阶段在内部元数据中标记分布类型，以及 serialize/deserialize 往返保持参数与元数据一致性

import numpy as np
import pytest
from dplib.cdp.mechanisms.gaussian import GaussianMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, ValidationError


@pytest.fixture
def gaussian() -> GaussianMechanism:
    # 夹具：提供一个带非平凡参数的 Gaussian 机制实例，供各测试复用
    return GaussianMechanism(epsilon=1.0, delta=1e-4, sensitivity=2.0)


def test_calibrate_sets_sigma(gaussian: GaussianMechanism) -> None:
    # 校验 calibrate 是否按解析公式正确设置 σ
    # 校准后应计算出 σ，公式：σ = Δf * sqrt(2 ln(1.25/δ)) / ε
    gaussian.calibrate()
    assert gaussian.sigma is not None
    expected = gaussian.sensitivity * np.sqrt(2.0 * np.log(1.25 / gaussian.delta)) / gaussian.epsilon
    assert gaussian.sigma == pytest.approx(expected)


def test_calibrate_with_delta_override(gaussian: GaussianMechanism) -> None:
    # 支持在 calibrate 调用时覆盖 delta，并写回到内部状态
    gaussian.calibrate(delta=1e-5)
    assert gaussian.delta == 1e-5


def test_calibrate_with_zero_delta_errors(gaussian: GaussianMechanism) -> None:
    # 高斯机制要求 δ > 0，否则应触发 ValidationError
    with pytest.raises(ValidationError):
        gaussian.calibrate(delta=0.0)


def test_calibrate_records_distribution_meta(gaussian: GaussianMechanism) -> None:
    # 校准后在内部 _meta 中标记 distribution 为 "gaussian"
    gaussian.calibrate()
    assert gaussian._meta.get("distribution") == "gaussian"  # noqa: SLF001


def test_randomise_scalar(gaussian: GaussianMechanism) -> None:
    # 对标量输入添加噪声，应返回 float 类型
    gaussian.calibrate()
    gaussian.reseed(0)
    noisy = gaussian.randomise(0.0)
    assert isinstance(noisy, float)


def test_randomise_numpy_array(gaussian: GaussianMechanism) -> None:
    # 对 NumPy 数组添加噪声时，应保持形状与 ndarray 类型不变
    gaussian.calibrate()
    arr = np.zeros((4,))
    result = gaussian.randomise(arr)
    assert isinstance(result, np.ndarray)
    assert result.shape == arr.shape


def test_randomise_requires_numeric(gaussian: GaussianMechanism) -> None:
    # 非数值类型输入（如字符串列表）应触发 ValidationError
    gaussian.calibrate()
    with pytest.raises(ValidationError):
        gaussian.randomise(["a", "b"])


def test_randomise_without_calibration(gaussian: GaussianMechanism) -> None:
    # 未调用 calibrate 校准前直接 randomise 应抛 NotCalibratedError
    with pytest.raises(NotCalibratedError):
        gaussian.randomise(1.0)


def test_serialize_roundtrip(gaussian: GaussianMechanism) -> None:
    # serialize / deserialize 往返应保持 sensitivity、delta、sigma 与 _meta 元数据一致性
    gaussian.calibrate()
    gaussian._meta["origin"] = "unit-test"  # 添加自定义元数据用于校验
    data = gaussian.serialize()
    restored = GaussianMechanism.deserialize(data)
    assert restored.sensitivity == gaussian.sensitivity
    assert restored.delta == gaussian.delta
    assert restored.sigma == gaussian.sigma
    assert restored._meta == gaussian._meta
