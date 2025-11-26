"""
Unit tests for the Staircase mechanism.
"""
# 说明：StaircaseMechanism（阶梯机制）的单元测试。
# 覆盖：
# - calibrate(...) 对 decay / success_prob 的标定与取值范围检查
# - randomise(...) 在数组输入上的形状保持行为
# - 未校准时调用 randomise 的保护（NotCalibratedError）
# - gamma 参数在校准及构造阶段的边界校验
# - 序列化/反序列化往返对阶梯参数的一致性

import numpy as np
import pytest

from dplib.cdp.mechanisms.staircase import StaircaseMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, ValidationError


@pytest.fixture
def staircase() -> StaircaseMechanism:
    # 提供带固定 ε/敏感度/γ 的阶梯机制实例，供各测试复用
    return StaircaseMechanism(epsilon=1.0, sensitivity=1.0, gamma=0.3)


def test_calibrate_sets_decay_and_success(staircase: StaircaseMechanism) -> None:
    # 校准后应生成非空的 decay / success_prob，且成功概率必须落在 (0, 1) 内
    staircase.calibrate()
    assert staircase.decay is not None
    assert staircase.success_prob is not None
    assert 0.0 < staircase.success_prob < 1.0


def test_randomise_preserves_shape(staircase: StaircaseMechanism) -> None:
    # 对 ndarray 加噪后应保持输入的形状不变
    staircase.calibrate()
    array = np.zeros((2,))
    result = staircase.randomise(array)
    assert isinstance(result, np.ndarray)
    assert result.shape == array.shape


def test_randomise_requires_calibration() -> None:
    # 未调用 calibrate() 的机制不允许 randomise，应抛出 NotCalibratedError
    mech = StaircaseMechanism(epsilon=1.0, sensitivity=1.0)
    with pytest.raises(NotCalibratedError):
        mech.randomise(0)


def test_gamma_validation() -> None:
    # gamma 超出 [0,1] 区间时，无论在 calibrate 还是构造阶段都应触发 ValidationError
    mech = StaircaseMechanism(epsilon=1.0, sensitivity=1.0, gamma=0.5)
    with pytest.raises(ValidationError):
        mech.calibrate(gamma=1.5)
    with pytest.raises(ValidationError):
        StaircaseMechanism(epsilon=1.0, sensitivity=1.0, gamma=-0.1)


def test_serialize_roundtrip(staircase: StaircaseMechanism) -> None:
    # 序列化→反序列化往返应保持 γ、decay 与 success_prob 等阶梯参数一致
    staircase.calibrate()
    data = staircase.serialize()
    restored = StaircaseMechanism.deserialize(data)
    assert restored.gamma == staircase.gamma
    assert restored.decay == staircase.decay
    assert restored.success_prob == staircase.success_prob
