"""
Unit tests for privacy-preserving analytics queries.
"""
# 说明：针对隐私分析查询（计数、求和、均值）的单元测试。
# 目标：验证谓词计数、裁剪求和、均值组合（求和/计数）、以及空输入校验等行为。

from __future__ import annotations
import numpy as np
import pytest
from dplib.cdp.analytics.queries import (
    PrivateCountQuery,
    PrivateSumQuery,
    PrivateMeanQuery,
)
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.core.privacy.base_mechanism import ValidationError


def _laplace(seed: int, epsilon: float, sensitivity: float) -> LaplaceMechanism:
    # 辅助：构造固定 RNG 的拉普拉斯机制并校准，用于期望值生成
    mech = LaplaceMechanism(
        epsilon=epsilon,
        sensitivity=sensitivity,
        rng=np.random.default_rng(seed),
    )
    mech.calibrate()
    return mech


def test_private_count_query_with_predicate() -> None:
    # 计数查询应在给定谓词下返回与“相同随机源”期望一致的噪声计数
    data = [1, 2, 3, 4, 5]
    predicate = lambda x: x % 2 == 0
    true_count = 2.0

    # query 与 expected 的机制使用相同的种子与参数，确保噪声可复现
    mech_query = _laplace(seed=42, epsilon=0.5, sensitivity=1.0)
    mech_expected = _laplace(seed=42, epsilon=0.5, sensitivity=1.0)
    query = PrivateCountQuery(epsilon=0.5, mechanism=mech_query, predicate=predicate)

    expected = mech_expected.randomise(true_count)
    assert query.evaluate(data) == pytest.approx(expected)


def test_private_sum_query_clips_values() -> None:
    # 求和查询应对数据先按 bounds 裁剪，再加噪
    data = [0.0, 5.0, 10.0]
    bounds = (0.0, 4.0)
    clipped_sum = 8.0  # [0, 4, 4] 的和

    mech_query = _laplace(seed=7, epsilon=1.0, sensitivity=bounds[1] - bounds[0])
    mech_expected = _laplace(seed=7, epsilon=1.0, sensitivity=bounds[1] - bounds[0])
    query = PrivateSumQuery(epsilon=1.0, bounds=bounds, mechanism=mech_query)

    expected = mech_expected.randomise(clipped_sum)
    assert query.evaluate(data) == pytest.approx(expected)


def test_private_mean_query_composes_sum_and_count() -> None:
    # 均值查询应由 DP 求和 与 DP 计数组合，且遵守最小计数稳定化与结果裁剪
    data = [0.0, 5.0, 10.0]
    bounds = (0.0, 4.0)
    clipped = np.clip(np.asarray(data), *bounds)
    true_sum = float(clipped.sum())
    true_count = float(len(clipped))

    # 固定种子分别用于求和机制与计数机制，保证期望可复现
    sum_mech = _laplace(seed=1, epsilon=0.6, sensitivity=bounds[1] - bounds[0])
    sum_mech_expected = _laplace(seed=1, epsilon=0.6, sensitivity=bounds[1] - bounds[0])
    count_mech = _laplace(seed=2, epsilon=0.4, sensitivity=1.0)
    count_mech_expected = _laplace(seed=2, epsilon=0.4, sensitivity=1.0)

    # 将准备好的机制注入查询器，避免内部默认拆分 ε 带来的偏差
    sum_query = PrivateSumQuery(epsilon=0.6, bounds=bounds, mechanism=sum_mech)
    count_query = PrivateCountQuery(epsilon=0.4, mechanism=count_mech)
    mean_query = PrivateMeanQuery(
        epsilon=1.0,
        bounds=bounds,
        sum_query=sum_query,
        count_query=count_query,
    )

    # 期望：dp_mean = clip( dp_sum / max(dp_count, min_count), bounds )
    dp_sum = sum_mech_expected.randomise(true_sum)
    dp_count = count_mech_expected.randomise(true_count)
    expected = np.clip(dp_sum / max(dp_count, mean_query.min_count), *bounds)
    assert mean_query.evaluate(data) == pytest.approx(expected)


def test_mean_query_rejects_empty_input() -> None:
    # 空输入应被拒绝并抛出 ValidationError
    query = PrivateMeanQuery(epsilon=1.0, bounds=(0.0, 1.0))
    with pytest.raises(ValidationError):
        query.evaluate([])
