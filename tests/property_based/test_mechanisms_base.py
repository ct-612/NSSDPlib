"""
Property-based tests for the BaseMechanism abstraction and shared helpers.
"""
# 说明：机制基类抽象（BaseMechanism）及共享辅助工具的属性测试。
# 覆盖：
# - 初始化时对隐私预算参数 (epsilon, delta) 的正性与合法性校验
# - 机制校准生命周期的状态保护拦截功能
# - 数值转换辅助工具在标量与多种容器间的结构保持能力
# - 机制元数据与状态的序列化往返一致性验证

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError, NotCalibratedError


# Concrete implementation for testing BaseMechanism
class MockMechanism(BaseMechanism):
    # 为测试基类提供具体的子类桩实现，避免直接实例化抽象类产生的错误
    def _calibrate_parameters(self,
                              *,
                              sensitivity: float = None,
                              **kwargs) -> None:
        # 记录校准时传入的外部参数以供后续断言验证逻辑使用
        """Subclasses implement their own calibration logic."""
        self.applied_sensitivity = sensitivity
        self.applied_kwargs = kwargs

    def randomise(self, value: any) -> any:
        # 模拟执行随机化逻辑并强制触发基类的校准状态检查
        """Add mechanism specific noise to the provided value."""
        self.require_calibrated()
        return value  # Mock: just return input


# ------------------------------------------------------------- Validation Tests
@given(st.floats(max_value=0))
def test_invalid_epsilon(eps):
    # 验证基类构造函数能够准确识别并拦截非正值的隐私预算参数
    with pytest.raises(ValidationError):
        MockMechanism(epsilon=eps)


@given(st.floats(max_value=-0.00001))
def test_invalid_delta(delta):
    # 验证机制对 delta 参数的非负性要求，确保差分隐私定义的数学边界安全
    with pytest.raises(ValidationError):
        MockMechanism(epsilon=1.0, delta=delta)


@given(st.floats(max_value=0))
def test_invalid_sensitivity(sensitivity):
    # 验证校准方法对敏感度正性的强制性要求逻辑，防止非法的灵敏度配置
    m = MockMechanism(epsilon=1.0)
    with pytest.raises(ValidationError):
        m.calibrate(sensitivity=sensitivity)


# ---------------------------------------------------------------- Lifecycle Tests
def test_uncalibrated_error():
    # 验证未校准的机制对象无法执行随机化操作并正确抛出 NotCalibratedError
    m = MockMechanism(epsilon=1.0)
    with pytest.raises(NotCalibratedError):
        m.randomise(1.0)

    # 验证完成合法校准后机制对象能够顺利通过状态检查并执行逻辑
    m.calibrate(sensitivity=1.0)
    m.randomise(1.0)  # Should not raise


# ------------------------------------------------------------ Numeric Helper Tests
@pytest.mark.parametrize("input_val, expected_type",
                         [(5.0, float), ([1.0, 2.0], list),
                          ((1.0, 2.0), tuple),
                          (np.array([1.0, 2.0]), np.ndarray)])
def test_numeric_restoration_types(input_val, expected_type):
    # 验证机制内部的数据类型规整与还原体系能针对多种 Python 容器保持保真性
    m = MockMechanism(epsilon=1.0)
    arr, was_scalar = m._coerce_numeric(input_val)
    # 将内部数组表示还原回与原始输入一致的容器结构与类型
    restored = m._restore_numeric_like(input_val, arr, was_scalar)
    assert isinstance(restored, expected_type)


@given(
    st.one_of(
        st.floats(allow_nan=False, allow_infinity=False),
        st.lists(st.floats(allow_nan=False, allow_infinity=False),
                 min_size=1,
                 max_size=10)))
def test_numeric_roundtrip_values(val):
    # 验证数值在经过内部强制转换与还原的完整往返路径后其内容无损
    m = MockMechanism(epsilon=1.0)
    arr, was_scalar = m._coerce_numeric(val)
    restored = m._restore_numeric_like(val, arr, was_scalar)
    # 依据容器类型灵活采用 NumPy 近似对比或严格相等对比
    if isinstance(val, list):
        assert np.allclose(val, restored)
    else:
        assert val == restored


# ------------------------------------------------------------ Serialization Tests
@given(st.floats(min_value=0.1, max_value=10),
       st.floats(min_value=0, max_value=0.1))
def test_base_serialization_roundtrip(eps, delta):
    # 验证机制核心属性在状态导出为字典与后续重构过程中保持原子一致性
    m = MockMechanism(epsilon=eps, delta=delta)
    m.calibrate(sensitivity=1.0)

    # 执行序列化与反序列化并对比重构出的对象状态
    state = m.serialize()
    m2 = MockMechanism.deserialize(state)

    assert m2.epsilon == pytest.approx(m.epsilon)
    assert m2.delta == pytest.approx(m.delta)
    assert m2.calibrated == m.calibrated
