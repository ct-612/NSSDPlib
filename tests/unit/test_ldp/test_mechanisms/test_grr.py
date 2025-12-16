"""
Unit tests for the GRR LDP mechanism.
"""
# 说明：k-ary 本地随机响应（GRR）机制的单元测试。
# 覆盖：
# - 验证非法 epsilon 与域大小或类别配置时抛出的异常类型
# - 验证随机响应输出是否始终落在有限离散域范围内
# - 通过大样本经验分布检验理论 p/q 概率公式的近似正确性
# - 检查在不同真实取值下机制输出分布的一致性与稳定性

from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.mechanisms.discrete.grr import GRRMechanism


def test_grr_invalid_params() -> None:
    # 验证在 epsilon 为零或域大小/类别配置非法时 GRRMechanism 会抛出预期异常
    with pytest.raises(ParamValidationError):
        GRRMechanism(epsilon=0.0, domain_size=3)
    with pytest.raises(ParamValidationError):
        GRRMechanism(epsilon=1.0, domain_size=1)
    with pytest.raises(ParamValidationError):
        GRRMechanism(epsilon=1.0, categories=[])


def test_grr_output_domain() -> None:
    # 检查随机响应输出的类别索引是否始终位于 [0, k) 的有限域范围内
    k = 4
    mech = GRRMechanism(epsilon=1.0, domain_size=k)
    outputs = [mech.randomise(2) for _ in range(1000)]
    assert all(0 <= o < k for o in outputs)


def test_grr_empirical_distribution_matches_formula() -> None:
    # 通过大样本模拟检验经验分布是否与理论 p/q 概率公式在容忍误差范围内一致
    k = 4
    eps = 1.0
    true_value = 1
    mech = GRRMechanism(epsilon=eps, domain_size=k)
    p = math.exp(eps) / (math.exp(eps) + k - 1)
    q = 1.0 / (math.exp(eps) + k - 1)

    n = 20000
    counts = Counter(mech.randomise(true_value) for _ in range(n))
    probs = {k: v / n for k, v in counts.items()}
    assert probs[true_value] == pytest.approx(p, rel=0.1)
    for cat in range(k):
        if cat == true_value:
            continue
        assert probs.get(cat, 0.0) == pytest.approx(q, rel=0.2)


@pytest.mark.parametrize("true_value", [0, 1, 2, 3])
def test_grr_stable_across_values(true_value: int) -> None:
    # 针对多个真实类别检查机制输出是否始终受限于同一有限域并保持基本稳定
    k = 4
    mech = GRRMechanism(epsilon=0.7, domain_size=k)
    outputs = [mech.randomise(true_value) for _ in range(500)]
    assert set(outputs).issubset(set(range(k)))
