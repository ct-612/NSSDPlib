"""
Unit tests for numerical utilities.
"""
# 说明：数值工具函数的单元测试，验证 logsumexp / softmax / stable_mean / stable_variance /
#       clamp_probabilities 等接口的数值稳定性与基本性质。
# 覆盖：
# - logsumexp：结果是否与数值稳定的 numpy 参考实现一致
# - softmax：输出是否保持形状不变且概率和为 1
# - stable_mean / stable_variance：是否与 numpy 的批量结果一致
# - clamp_probabilities：对 0/1 极端概率向量的截断与重新归一化行为

import numpy as np
import pytest

from dplib.core.utils import (
    clamp_probabilities,
    logsumexp,
    softmax,
    stable_mean,
    stable_variance,
)


def test_logsumexp_matches_numpy() -> None:
    # 检查 logsumexp 计算结果与手工构造的数值稳定参考实现一致
    values = np.array([1000.0, 1001.0, 1002.0])
    expected = np.log(np.sum(np.exp(values - values.max()))) + values.max()
    result = np.asarray(logsumexp(values)).item()
    assert pytest.approx(result) == pytest.approx(expected)


def test_softmax_normalizes() -> None:
    # softmax 输出应与输入形状一致且概率和为 1
    values = np.array([1.0, 2.0, 3.0])
    probs = softmax(values)
    assert probs.shape == values.shape
    assert pytest.approx(probs.sum()) == 1.0


def test_stable_mean_and_variance() -> None:
    # stable_mean / stable_variance 的结果应与 numpy 的批量计算一致
    values = [1.0, 2.0, 3.0, 4.0]
    assert pytest.approx(stable_mean(values)) == 2.5
    assert pytest.approx(stable_variance(values, ddof=1)) == pytest.approx(np.var(values, ddof=1))


def test_clamp_probabilities_prevents_extremes() -> None:
    # clamp_probabilities 应避免 0/1 极端概率，并保持归一化
    probs = clamp_probabilities([0.0, 1.0, 0.0])
    assert (probs > 0).all()
    assert pytest.approx(float(np.sum(probs))) == 1.0
