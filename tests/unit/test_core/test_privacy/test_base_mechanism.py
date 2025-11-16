"""
Unit tests for the BaseMechanism abstractions.
"""
# 说明：使用 DummyMechanism 验证 BaseMechanism 的通用行为与约束。
# 覆盖：
# - 参数校验：epsilon>0、delta≥0
# - 校准生命周期：calibrate() 置位、返回 self、scale 计算与敏感度校验
# - 调用前置条件：未校准时 randomise() 抛 NotCalibratedError
# - 类型与形状保持：标量、ndarray、list、tuple 的输出类型/形状不变
# - 标识派生：mechanism_id 去除 “Mechanism” 后缀
# - 序列化往返：serialize()/to_json()/from_json() 保留元数据与状态
# - RNG 复现性：reseed(seed) 后随机序列可重复

from typing import Optional

import numpy as np
import pytest

from dplib.core.privacy.base_mechanism import (
    BaseMechanism,
    CalibrationError,
    NotCalibratedError,
    ValidationError,
)


class DummyMechanism(BaseMechanism):
    """Light-weight mechanism used to validate BaseMechanism behaviour."""
    # 轻量机制：用于验证 BaseMechanism 的通用行为与生命周期。

    def __init__(self, epsilon: float = 1.0, delta: float = 0.0, rng=None, name: Optional[str] = None):
        # 传递 ε/δ/RNG/名称给基类；定义简单的敏感度与“尺度”以便测试
        super().__init__(epsilon=epsilon, delta=delta, rng=rng, name=name)
        self.sensitivity = 1.0
        self.scale: Optional[float] = None

    def _calibrate_parameters(self, *, sensitivity=None, **kwargs):
        # 基类 calibrate() 调用的实际校准逻辑：支持更新敏感度，并设置 scale = sensitivity / epsilon
        del kwargs
        if sensitivity is not None:
            self.sensitivity = float(sensitivity)
        self.scale = self.sensitivity / self.epsilon

    def randomise(self, value):
        # 简化的“加噪”实现：只做 +scale，用于验证 require_calibrated()、形状/类型恢复等
        self.require_calibrated()
        if self.scale is None:
            raise CalibrationError("scale must be defined after calibrate()")
        arr, was_scalar = self._coerce_numeric(value)
        result = arr + self.scale
        return self._restore_numeric_like(value, result, was_scalar)


def test_invalid_epsilon_or_delta_raise_validation_error():
    # ε 非正或 δ 为负应触发参数校验错误
    with pytest.raises(ValidationError):
        DummyMechanism(epsilon=0.0)
    with pytest.raises(ValidationError):
        DummyMechanism(epsilon=1.0, delta=-1e-3)


def test_calibrate_sets_flag_and_returns_self():
    # calibrate() 返回 self，置 calibrated=True，并按期望计算 scale
    mech = DummyMechanism(epsilon=2.0)
    assert mech.calibrated is False
    returned = mech.calibrate(sensitivity=3.0)
    assert returned is mech
    assert mech.calibrated is True
    assert mech.scale == pytest.approx(1.5)


def test_calibrate_validates_sensitivity():
    # 负敏感度应触发 ValidationError（由基类校验）
    mech = DummyMechanism()
    with pytest.raises(ValidationError):
        mech.calibrate(sensitivity=-0.5)


def test_randomise_requires_prior_calibration():
    # 未校准时调用 randomise() 应触发 NotCalibratedError
    mech = DummyMechanism()
    with pytest.raises(NotCalibratedError):
        mech.randomise(1.0)


def test_randomise_preserves_input_shape_and_type():
    # randomise() 应保持输入外形与容器类型不变，并逐元素 +scale
    mech = DummyMechanism()
    mech.calibrate(sensitivity=2.0)

    scalar = mech.randomise(1.0)
    assert scalar == pytest.approx(3.0)

    array = mech.randomise(np.array([1.0, 2.0]))
    assert isinstance(array, np.ndarray)
    np.testing.assert_allclose(array, np.array([3.0, 4.0]))

    sequence = mech.randomise([1.0, 2.0])
    assert isinstance(sequence, list)
    assert sequence == [3.0, 4.0]

    tuple_value = mech.randomise((1.0, 2.0))
    assert isinstance(tuple_value, tuple)
    assert tuple_value == (3.0, 4.0)


def test_mechanism_id_strips_mechanism_suffix():
    # mechanism_id 派生自类名，去掉 “Mechanism” 后缀，应为 "dummy"
    mech = DummyMechanism()
    assert mech.mechanism_id == "dummy"


def test_serialize_round_trip_and_meta_copy():
    # 序列化应包含关键字段；meta 应返回拷贝；JSON 往返应保持参数与状态一致
    mech = DummyMechanism(epsilon=1.5, delta=1e-4, name="Dummy")
    mech._meta["notes"] = "v1"
    mech.calibrate()

    payload = mech.serialize()
    assert payload["mechanism"] == "dummy"
    payload["meta"]["notes"] = "mutated"
    assert mech._meta["notes"] == "v1"  # ensure serialize returned a copy

    cloned = DummyMechanism.from_json(mech.to_json())
    assert cloned.epsilon == pytest.approx(mech.epsilon)
    assert cloned.delta == pytest.approx(mech.delta)
    assert cloned.name == mech.name
    assert cloned.calibrated == mech.calibrated


def test_reseed_produces_repeatable_rng_sequences():
    # reseed(seed) 应重置 RNG 序列；相同 seed 产生相同下一个随机数
    mech = DummyMechanism(rng=np.random.default_rng(1))
    initial = mech._rng.random()
    mech.reseed(1234)
    after_reseed = mech._rng.random()
    assert initial != after_reseed

    mech.reseed(1234)
    repeat = mech._rng.random()
    assert repeat == pytest.approx(after_reseed)
