"""
Unit tests for the Exponential mechanism.
"""
# 说明：ExponentialMechanism（指数机制）的单元测试。
# 覆盖：
# - calibrate(...) 对敏感度与默认候选集的更新行为
# - 基于 mapping / utility_fn 等多种输入形式的 randomise 采样逻辑
# - 未校准时调用 randomise 的保护（NotCalibratedError）
# - 序列化/反序列化往返对参数与采样元数据的保持
# - 空候选集及候选集/分数长度不匹配时的校验错误

import numpy as np
import pytest

from dplib.cdp.mechanisms.exponential import ExponentialMechanism
from dplib.core.privacy.base_mechanism import NotCalibratedError, ValidationError


@pytest.fixture
def exp_mechanism() -> ExponentialMechanism:
    # 提供带固定 ε/敏感度/候选集的指数机制实例，供各测试复用
    return ExponentialMechanism(epsilon=1.0, sensitivity=2.0, candidates=["red", "blue", "green"])


def test_calibrate_updates_state(exp_mechanism: ExponentialMechanism) -> None:
    # 校准时可以同时更新敏感度与默认候选集，并正确反映到内部状态
    exp_mechanism.calibrate(sensitivity=3.0, candidates=["a", "b"])
    assert exp_mechanism.sensitivity == pytest.approx(3.0)
    assert exp_mechanism.default_candidates == ("a", "b")


def test_randomise_with_mapping_sets_probabilities(exp_mechanism: ExponentialMechanism) -> None:
    # 当输入为 {candidate: utility} 映射时，应正确采样并记录归一化概率向量
    exp_mechanism.calibrate()
    exp_mechanism.reseed(0)
    choice = exp_mechanism.randomise({"red": 0.0, "blue": 1.0})
    assert choice in {"red", "blue"}
    assert exp_mechanism._last_probabilities is not None  # noqa: SLF001 - test visibility
    assert exp_mechanism._last_probabilities.sum() == pytest.approx(1.0)
    assert len(exp_mechanism._last_probabilities) == 2


def test_randomise_supports_utility_fn() -> None:
    # 当提供 utility_fn 时，应基于上下文按 exp(ε·u/2Δ) 计算得分并采样
    def util(ctx: dict[str, float], cand: str) -> float:
        return ctx[cand]

    mech = ExponentialMechanism(
        epsilon=2.0,
        sensitivity=1.0,
        utility_fn=util,
        candidates=["x", "y"],
    )
    mech.calibrate()
    mech.reseed(1)
    context = {"x": -1.0, "y": 3.0}
    mech.randomise(context)
    probs = mech._last_probabilities  # noqa: SLF001 - test visibility
    assert probs is not None
    beta = mech.epsilon / (2 * mech.sensitivity)
    expected = np.exp(beta * np.array([context["x"], context["y"]]))
    expected = expected / expected.sum()
    assert probs[1] == pytest.approx(expected[1])


def test_randomise_requires_calibration() -> None:
    # 未调用 calibrate() 的机制不允许 randomise，应抛出 NotCalibratedError
    mech = ExponentialMechanism(epsilon=1.0, sensitivity=1.0, candidates=["only"])
    with pytest.raises(NotCalibratedError):
        mech.randomise({"only": 0.0})


def test_serialize_roundtrip_preserves_candidates(exp_mechanism: ExponentialMechanism) -> None:
    # 序列化→反序列化往返应保留敏感度、默认候选集以及最近一次采样概率
    exp_mechanism.calibrate()
    exp_mechanism.randomise({"red": 0.0, "blue": 1.0})
    data = exp_mechanism.serialize()
    restored = ExponentialMechanism.deserialize(data)
    assert restored.sensitivity == exp_mechanism.sensitivity
    assert restored.default_candidates == exp_mechanism.default_candidates
    assert restored._last_probabilities is not None  # noqa: SLF001 - test visibility


def test_invalid_empty_candidates_raise(exp_mechanism: ExponentialMechanism) -> None:
    # 空候选集或候选集与 scores 长度不匹配应触发 ValidationError
    with pytest.raises(ValidationError):
        exp_mechanism.calibrate(candidates=[])
    exp_mechanism.calibrate()
    with pytest.raises(ValidationError):
        exp_mechanism.randomise(None, candidates=["a", "b"], scores=[1.0])
