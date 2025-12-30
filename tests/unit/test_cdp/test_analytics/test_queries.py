"""
Unit tests for privacy-preserving analytics query primitives.
"""
# 说明：隐私保护分析查询组件（count/sum/mean/variance/histogram/range）的单元测试。
# 覆盖：
# - 计数查询在带谓词与自定义 Laplace 机制下的噪声一致性
# - 求和查询在有界裁剪后的噪声路径与手工裁剪结果的一致性
# - 均值查询通过 DP 求和与 DP 计数组合得到结果的数值行为
# - 方差查询在带噪一阶与二阶矩、ddof 调整和上界裁剪下的实现逻辑
# - 直方图查询对分箱计数向量加噪、非负截断以及分箱边界保持
# - 区间查询在 sum/count/mean 度量下通过带噪前缀和回答多区间的行为
# - 均值查询对空输入时抛出 ParamValidationError 的错误分支

from __future__ import annotations

import numpy as np
import pytest

from dplib.cdp.analytics.queries import (
    PrivateCountQuery,
    PrivateHistogramQuery,
    PrivateMeanQuery,
    PrivateRangeQuery,
    PrivateSumQuery,
    PrivateVarianceQuery,
)
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.cdp.mechanisms.vector import VectorMechanism
from dplib.core.utils.param_validation import ParamValidationError


def _laplace(seed: int, epsilon: float, sensitivity: float) -> LaplaceMechanism:
    # 使用指定随机种子与灵敏度构造并校准 Laplace 机制以获得可重现噪声
    mech = LaplaceMechanism(
        epsilon=epsilon,
        sensitivity=sensitivity,
        rng=np.random.default_rng(seed),
    )
    mech.calibrate()
    return mech


def _vector(seed: int, epsilon: float, sensitivity: float) -> VectorMechanism:
    # 使用指定随机种子构造基于 Laplace 的 VectorMechanism 以向量化加噪
    mech = VectorMechanism(
        epsilon=epsilon,
        sensitivity=sensitivity,
        distribution="laplace",
        norm="l1",
        rng=np.random.default_rng(seed),
    )
    mech.calibrate()
    return mech


def test_private_count_query_with_predicate() -> None:
    # 验证带谓词的计数查询在注入同源机制时与预期噪声输出一致
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
    # 验证求和查询会先按边界裁剪数据再加噪并与手工裁剪路径保持一致
    data = [0.0, 5.0, 10.0]
    bounds = (0.0, 4.0)
    clipped_sum = 8.0  # [0, 4, 4]

    mech_query = _laplace(seed=7, epsilon=1.0, sensitivity=bounds[1] - bounds[0])
    mech_expected = _laplace(seed=7, epsilon=1.0, sensitivity=bounds[1] - bounds[0])
    query = PrivateSumQuery(epsilon=1.0, bounds=bounds, mechanism=mech_query)

    expected = mech_expected.randomise(clipped_sum)
    assert query.evaluate(data) == pytest.approx(expected)


def test_private_mean_query_composes_sum_and_count() -> None:
    # 验证均值查询通过 DP 求和与 DP 计数组合得到结果且数值路径与手工实现一致
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


def test_private_variance_query_combines_moments() -> None:
    # 验证方差查询在带噪一阶矩和二阶矩基础上按实现公式组合并裁剪到理论上界
    data = [0.0, 5.0, 10.0]
    bounds = (0.0, 5.0)
    # 准备裁剪后的样本、平方样本以及对应的一阶和、平方和、样本数量
    clipped = np.clip(np.asarray(data), *bounds)
    squared = np.square(clipped)
    true_sum = float(clipped.sum())
    true_squares = float(squared.sum())
    true_count = float(len(clipped))

    # 为一阶矩、二阶矩和计数分别构造对应的 Laplace 噪声机制
    sum_mech = _laplace(seed=3, epsilon=0.4, sensitivity=bounds[1] - bounds[0])
    sum_mech_expected = _laplace(seed=3, epsilon=0.4, sensitivity=bounds[1] - bounds[0])
    squares_mech = _laplace(seed=4, epsilon=0.4, sensitivity=(bounds[1] ** 2))
    squares_mech_expected = _laplace(seed=4, epsilon=0.4, sensitivity=(bounds[1] ** 2))
    count_mech = _laplace(seed=5, epsilon=0.2, sensitivity=1.0)
    count_mech_expected = _laplace(seed=5, epsilon=0.2, sensitivity=1.0)

    # 将三类机制注入到求和、平方和、计数查询中以构造方差查询对象
    sum_query = PrivateSumQuery(epsilon=0.4, bounds=bounds, mechanism=sum_mech)
    squares_query = PrivateSumQuery(epsilon=0.4, bounds=(0.0, bounds[1] ** 2), mechanism=squares_mech)
    count_query = PrivateCountQuery(epsilon=0.2, mechanism=count_mech)
    variance_query = PrivateVarianceQuery(
        epsilon=1.0,
        bounds=bounds,
        sum_query=sum_query,
        squares_query=squares_query,
        count_query=count_query,
    )

    # 手工复现方差查询内部的带噪矩计算、ddof 调整和方差上界裁剪逻辑
    dp_sum = sum_mech_expected.randomise(true_sum)
    dp_squares = squares_mech_expected.randomise(true_squares)
    dp_count = count_mech_expected.randomise(true_count)
    stable_count = max(dp_count, variance_query.min_count)
    mean_estimate = dp_sum / stable_count
    second_moment = dp_squares / stable_count
    raw_variance = max(second_moment - mean_estimate ** 2, 0.0)
    denom = max(stable_count - variance_query.ddof, variance_query.min_count)
    mean_for_bound = np.clip(mean_estimate, bounds[0], bounds[1])
    variance_bound = (bounds[1] - mean_for_bound) * (mean_for_bound - bounds[0])
    expected = np.clip(raw_variance * (stable_count / denom), 0.0, variance_bound)

    assert variance_query.evaluate(data) == pytest.approx(expected)


def test_private_histogram_query_adds_noise() -> None:
    # 验证直方图查询对真实计数向量加噪并截断为非负值且保持原始分箱边界
    data = [0.5, 1.5, 2.5, 4.0]
    bins = (0.0, 2.0, 4.0)
    mech_query = _vector(seed=8, epsilon=0.7, sensitivity=1.0)
    mech_expected = _vector(seed=8, epsilon=0.7, sensitivity=1.0)
    query = PrivateHistogramQuery(epsilon=0.7, bins=bins, mechanism=mech_query)

    expected_counts = mech_expected.randomise(np.asarray([2.0, 2.0]))
    noisy_counts, edges = query.evaluate(data)
    assert edges == bins
    assert noisy_counts == pytest.approx(np.maximum(expected_counts, 0.0))


def test_private_range_query_prefix_and_ranges() -> None:
    # 验证区间查询通过带噪前缀和回答多区间求和且与手工构造路径结果一致
    data = [1.0, 2.0, 3.0]
    bounds = (0.0, 5.0)
    ranges = [(0, 2), (1, 3)]

    mech_query = _vector(seed=21, epsilon=1.0, sensitivity=1.0)
    mech_expected = _vector(seed=21, epsilon=1.0, sensitivity=1.0)
    query = PrivateRangeQuery(epsilon=1.0, bounds=bounds, mechanism=mech_query)

    # 手工构造真实前缀和并基于值域跨度和长度计算敏感度
    prefix = [0.0, 1.0, 3.0, 6.0]
    sensitivity = (bounds[1] - bounds[0]) * (len(prefix) - 1)
    mech_expected.calibrate(sensitivity=sensitivity)
    noisy_prefix = np.asarray(mech_expected.randomise(prefix), dtype=float)
    # 通过差分带噪前缀和得到各区间的预期输出
    expected = [
        noisy_prefix[2] - noisy_prefix[0],
        noisy_prefix[3] - noisy_prefix[1],
    ]

    assert query.evaluate(data, ranges=ranges) == pytest.approx(expected)


def test_private_range_query_count_metric() -> None:
    # 验证区间查询在 count 度量下通过计数前缀和和相应敏感度校准得到带噪计数区间
    data = [1.0, 2.0, 3.0]
    bounds = (0.0, 5.0)
    ranges = [(0, 2), (1, 3)]

    mech_query = _vector(seed=31, epsilon=1.0, sensitivity=1.0)
    mech_expected = _vector(seed=31, epsilon=1.0, sensitivity=1.0)
    query = PrivateRangeQuery(epsilon=1.0, bounds=bounds, mechanism=mech_query, metric="count")

    # 构造计数前缀和并以宽度作为 count 度量的敏感度
    prefix = [0.0, 1.0, 2.0, 3.0]
    width = len(prefix) - 1
    mech_expected.calibrate(sensitivity=width)  # count metric sensitivity
    noisy_prefix = np.asarray(mech_expected.randomise(prefix), dtype=float)
    # 差分带噪计数前缀和得到各区间计数的预期结果
    expected = [
        noisy_prefix[2] - noisy_prefix[0],
        noisy_prefix[3] - noisy_prefix[1],
    ]

    assert query.evaluate(data, ranges=ranges, metric="count") == pytest.approx(expected)


def test_private_range_query_mean_metric() -> None:
    # 验证区间查询在 mean 度量下复用 sum 和 count 的带噪前缀和路径得到区间均值并裁剪到值域
    data = [1.0, 2.0, 3.0]
    bounds = (0.0, 5.0)
    ranges = [(0, 3)]

    mech_query = _vector(seed=41, epsilon=1.0, sensitivity=1.0)
    mech_expected = _vector(seed=41, epsilon=1.0, sensitivity=1.0)
    query = PrivateRangeQuery(epsilon=1.0, bounds=bounds, mechanism=mech_query, metric="mean")

    # 先对数据进行裁剪并构造 sum 的前缀和序列
    clipped = np.clip(np.asarray(data), *bounds)
    prefix_sum = [0.0, 1.0, 3.0, 6.0]
    width = len(prefix_sum) - 1
    span = bounds[1] - bounds[0]

    # 为 sum 前缀和校准 span*width 的敏感度并生成带噪和
    mech_expected.calibrate(sensitivity=span * width)
    noisy_sum = np.asarray(mech_expected.randomise(prefix_sum), dtype=float)

    # 为 count 前缀和校准 width 的敏感度并组合出区间均值估计
    prefix_count = [0.0, 1.0, 2.0, 3.0]
    mech_expected.calibrate(sensitivity=width)
    noisy_count = np.asarray(mech_expected.randomise(prefix_count), dtype=float)

    dp_sum = noisy_sum[3] - noisy_sum[0]
    dp_count = noisy_count[3] - noisy_count[0]
    expected = float(np.clip(dp_sum / max(dp_count, query.min_count), bounds[0], bounds[1]))

    assert query.evaluate(data, ranges=ranges, metric="mean") == pytest.approx([expected])


def test_mean_query_rejects_empty_input() -> None:
    # 确认均值查询在空输入时抛出 ParamValidationError 以避免未定义行为
    query = PrivateMeanQuery(epsilon=1.0, bounds=(0.0, 1.0))
    with pytest.raises(ParamValidationError):
        query.evaluate([])
