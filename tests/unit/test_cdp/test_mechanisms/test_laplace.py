"""
Unit tests validating the Laplace mechanism implementation.

Covers:
    * calibration of scale
    * noise addition for scalars and arrays
    * validation, lifecycle guardrails, and serialization roundtrip
"""
# 说明：对拉普拉斯机制进行单元测试。
# 覆盖：
# - 噪声尺度校准
# - 标量与数组的加噪与形状保持
# - 参数校验错误、生命周期约束（未校准禁止使用）、序列化往返一致性

import numpy as np
import pytest
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, ValidationError


@pytest.fixture
def laplace() -> LaplaceMechanism:
    """Fixture returning a Laplace mechanism with non-unit parameters."""
    # 夹具：提供一个非默认参数的 Laplace 机制实例，便于复用
    return LaplaceMechanism(epsilon=2.0, sensitivity=3.0)


def test_calibrate_computes_scale(laplace: LaplaceMechanism) -> None:
    """Calibration should update the Laplace scale using epsilon and sensitivity."""
    # 断言：calibrate() 后 scale == sensitivity / epsilon
    laplace.calibrate()
    assert laplace.scale == pytest.approx(laplace.sensitivity / laplace.epsilon)


def test_randomise_scalar_returns_float(laplace: LaplaceMechanism) -> None:
    """Scalar inputs produce noisy floats drawn from Laplace distribution."""
    # 标量输入应返回 float，且在固定种子下基本不等于原值
    laplace.calibrate()
    laplace.reseed(0)  # 固定 RNG 以减少偶然性
    noisy = laplace.randomise(5.0)
    assert isinstance(noisy, float)
    assert noisy != 5.0  # 极小概率相等，测试依赖已设定随机种子


def test_randomise_vector_input_returns_list(laplace: LaplaceMechanism) -> None:
    """Python lists are processed element-wise and type is preserved."""
    # Python 列表逐元素加噪，且保持类型为 list
    laplace.calibrate()
    values = [0.0, 1.0, 2.0]
    result = laplace.randomise(values)
    assert isinstance(result, list)
    assert len(result) == len(values)  # 长度不变


def test_randomise_numpy_array_preserves_shape(laplace: LaplaceMechanism) -> None:
    """Numpy arrays should preserve shape after adding noise."""
    # Numpy 数组形状在加噪后应保持不变
    laplace.calibrate()
    array = np.zeros((2, 3))
    result = laplace.randomise(array)
    assert isinstance(result, np.ndarray)
    assert result.shape == array.shape


def test_randomise_requires_numeric(laplace: LaplaceMechanism) -> None:
    """Non-numeric data should be rejected."""
    # 非数值数据应触发 ValidationError
    laplace.calibrate()
    with pytest.raises(ValidationError):
        laplace.randomise(["not", "numeric"])


def test_randomise_without_calibration_raises(laplace: LaplaceMechanism) -> None:
    """Calling randomise before calibrate should raise an error."""
    # 未调用 calibrate() 直接 randomise() 应抛出 NotCalibratedError
    with pytest.raises(NotCalibratedError):
        laplace.randomise(1.0)


def test_calibrate_records_distribution_meta(laplace: LaplaceMechanism) -> None:
    """Calibration should record distribution metadata for auditing."""
    # 校准后应在元数据 _meta 中记录分布名称（"laplace"），便于审计检查
    laplace.calibrate()
    assert laplace._meta.get("distribution") == "laplace"


def test_serialize_roundtrip(laplace: LaplaceMechanism) -> None:
    """Serialized Laplace mechanisms should roundtrip with metadata and scale intact."""
    # 序列化→反序列化往返：应保持 sensitivity、scale 以及自定义 meta 一致
    laplace.calibrate()
    laplace._meta["origin"] = "unit-test"  # 添加自定义元数据用于校验
    data = laplace.serialize()
    restored = LaplaceMechanism.deserialize(data)
    assert restored.sensitivity == laplace.sensitivity
    assert restored.scale == laplace.scale
    assert restored._meta == laplace._meta
