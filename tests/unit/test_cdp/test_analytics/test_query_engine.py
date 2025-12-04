"""
Unit tests for QueryEngine orchestrating DP analytics queries.
"""
# 说明：围绕 QueryEngine 组合与调度各类隐私分析查询（计数/求和/均值/方差/直方图/区间）的单元测试。
# 覆盖：
# - 验证 QueryEngine.execute 能正确分发到 count 与 sum 查询并复现注入机制的带噪结果
# - 验证在注入预构造的求和与计数查询时 mean 分支的组合行为与手工路径一致
# - 验证 variance 分支在带噪一阶与二阶矩、样本方差修正和方差上界裁剪下的数值逻辑
# - 验证 histogram 分支在向量机制下产生带噪计数并保持非负与分箱边界不变
# - 验证 range 分支在 sum 与 mean 度量下通过带噪前缀和回答区间查询的结果

from __future__ import annotations

import numpy as np
import pytest

from dplib.cdp.analytics.queries import (
    PrivateCountQuery,
    PrivateSumQuery,
    QueryEngine,
)
from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.cdp.mechanisms.vector import VectorMechanism


def _laplace(seed: int, epsilon: float, sensitivity: float) -> LaplaceMechanism:
    # 使用给定随机种子与灵敏度构造并校准 Laplace 机制以生成可重现标量噪声
    mech = LaplaceMechanism(
        epsilon=epsilon,
        sensitivity=sensitivity,
        rng=np.random.default_rng(seed),
    )
    mech.calibrate()
    return mech


def _vector(seed: int, epsilon: float, sensitivity: float) -> VectorMechanism:
    # 使用给定随机种子构造并校准基于 Laplace 的 VectorMechanism 以生成可重现向量噪声
    mech = VectorMechanism(
        epsilon=epsilon,
        sensitivity=sensitivity,
        distribution="laplace",
        norm="l1",
        rng=np.random.default_rng(seed),
    )
    mech.calibrate()
    return mech


def test_query_engine_runs_basic_queries() -> None:
    # 验证 QueryEngine 对 count 与 sum 查询的分发逻辑及其与手工噪声路径的一致性
    engine = QueryEngine()
    # 通过同一参数与种子的机制构造预期结果以对比引擎输出

    # count -----------------------------------------------------------
    # 先基于 predicate 得到真实计数并用相同 Laplace 机制生成预期的带噪计数结果
    data = [1, 2, 3, 4, 5]
    predicate = lambda x: x % 2 == 0
    count_mech = _laplace(1, 0.5, 1.0)
    count_mech_expected = _laplace(1, 0.5, 1.0)
    expected_count = count_mech_expected.randomise(2.0)

    result = engine.execute(
        "count",
        data=data,
        epsilon=0.5,
        predicate=predicate,
        mechanism=count_mech,
    )
    assert result == pytest.approx(expected_count)

    # sum -----------------------------------------------------------
    # 先构造受 bounds 约束的裁剪和并用相同 Laplace 机制获得预期带噪结果
    bounds = (0.0, 4.0)
    clipped_sum = 8.0
    sum_mech = _laplace(2, 1.0, bounds[1] - bounds[0])
    sum_mech_expected = _laplace(2, 1.0, bounds[1] - bounds[0])
    expected_sum = sum_mech_expected.randomise(clipped_sum)

    result = engine.execute(
        "sum",
        data=[0.0, 5.0, 10.0],
        epsilon=1.0,
        bounds=bounds,
        mechanism=sum_mech,
    )
    assert result == pytest.approx(expected_sum)


def test_query_engine_mean_and_variance() -> None:
    # 验证 QueryEngine 在 mean 与 variance 分支上复用外部构造的查询对象并产生正确带噪结果
    engine = QueryEngine()
    data = [0.0, 5.0, 10.0]
    bounds = (0.0, 4.0)
    # 对原始数据按 bounds 做裁剪并预先计算真实总和与样本数
    clipped = np.clip(np.asarray(data), *bounds)
    true_sum = float(clipped.sum())
    true_count = float(len(clipped))

    # mean -----------------------------------------------------------
    # 构造可复用的求和与计数查询对象并在 engine 中组合为 DP 均值
    sum_mech = _laplace(3, 0.6, bounds[1] - bounds[0])
    sum_mech_expected = _laplace(3, 0.6, bounds[1] - bounds[0])
    count_mech = _laplace(4, 0.4, 1.0)
    count_mech_expected = _laplace(4, 0.4, 1.0)

    sum_query = PrivateSumQuery(epsilon=0.6, bounds=bounds, mechanism=sum_mech)
    count_query = PrivateCountQuery(epsilon=0.4, mechanism=count_mech)

    result = engine.execute(
        "mean",
        data=data,
        epsilon=1.0,
        bounds=bounds,
        sum_query=sum_query,
        count_query=count_query,
    )
    # 使用同配置的机制对真实统计量加噪得到期望的 DP 均值表达式
    dp_sum = sum_mech_expected.randomise(true_sum)
    dp_count = count_mech_expected.randomise(true_count)
    expected_mean = np.clip(dp_sum / max(dp_count, sum_query.epsilon * 0 + 1e-6), *bounds)
    assert result == pytest.approx(expected_mean)

    # variance -----------------------------------------------------------
    # 通过平方构造二阶矩以支持 Var(X) = E[X^2] - (E[X])^2 形式的方差估计
    squared = np.square(clipped)
    true_squares = float(squared.sum())

    var_sum_mech = _laplace(5, 0.4, bounds[1] - bounds[0])
    var_sum_mech_exp = _laplace(5, 0.4, bounds[1] - bounds[0])
    var_sq_mech = _laplace(6, 0.4, bounds[1] ** 2)
    var_sq_mech_exp = _laplace(6, 0.4, bounds[1] ** 2)
    var_count_mech = _laplace(7, 0.2, 1.0)
    var_count_mech_exp = _laplace(7, 0.2, 1.0)

    # 为一阶矩、二阶矩与计数分别注入独立 Laplace 噪声以匹配引擎内部实现
    result = engine.execute(
        "variance",
        data=data,
        epsilon=1.0,
        bounds=bounds,
        sum_query=PrivateSumQuery(epsilon=0.4, bounds=bounds, mechanism=var_sum_mech),
        squares_query=PrivateSumQuery(epsilon=0.4, bounds=(0.0, bounds[1] ** 2), mechanism=var_sq_mech),
        count_query=PrivateCountQuery(epsilon=0.2, mechanism=var_count_mech),
    )

    dp_sum = var_sum_mech_exp.randomise(true_sum)
    dp_squares = var_sq_mech_exp.randomise(true_squares)
    dp_count = var_count_mech_exp.randomise(true_count)
    # stable_count 和 denom 通过下界截断避免除零与极小分母带来的数值不稳定
    stable_count = max(dp_count, 1e-6)
    mean_estimate = dp_sum / stable_count
    second_moment = dp_squares / stable_count
    # 先按二阶矩减去均值平方得到原始方差并做非负裁剪
    raw_variance = max(second_moment - mean_estimate ** 2, 0.0)
    denom = max(stable_count - 1, 1e-6)
    # 再利用 Bhatia-Davis 上界将方差限制在给定 bounds 下的理论最大值范围内
    mean_for_bound = np.clip(mean_estimate, bounds[0], bounds[1])
    variance_bound = (bounds[1] - mean_for_bound) * (mean_for_bound - bounds[0])
    expected_variance = np.clip(raw_variance * (stable_count / denom), 0.0, variance_bound)
    assert result == pytest.approx(expected_variance)


def test_query_engine_histogram_and_range_metrics() -> None:
    # 验证 QueryEngine 在 histogram 与 range(sum/mean) 分支上的分发与数值结果是否与手工路径一致
    engine = QueryEngine()

    # histogram -----------------------------------------------------------
    # 通过两段等宽分箱验证向量机制生成的带噪直方图计数与手工路径一致
    data = [0.5, 1.5, 2.5, 4.0]
    bins = (0.0, 2.0, 4.0)
    mech_hist = _vector(8, 0.7, 1.0)
    mech_hist_exp = _vector(8, 0.7, 1.0)
    expected_counts = mech_hist_exp.randomise(np.asarray([2.0, 2.0]))

    noisy_counts, edges = engine.execute(
        "histogram",
        data=data,
        epsilon=0.7,
        bins=bins,
        mechanism=mech_hist,
    )
    assert edges == bins
    assert noisy_counts == pytest.approx(np.maximum(expected_counts, 0.0))

    # range_sum -----------------------------------------------------------
    # 使用前缀和一次性加噪的方式构造区间和的期望结果并与引擎输出对比
    range_data = [1.0, 2.0, 3.0]
    bounds = (0.0, 5.0)
    ranges = [(0, 2), (1, 3)]
    mech_range = _vector(9, 1.0, 1.0)
    mech_range_exp = _vector(9, 1.0, 1.0)
    prefix = [0.0, 1.0, 3.0, 6.0]
    mech_range_exp.calibrate(sensitivity=(bounds[1] - bounds[0]) * (len(prefix) - 1))
    noisy_prefix = np.asarray(mech_range_exp.randomise(prefix), dtype=float)
    expected = [
        noisy_prefix[2] - noisy_prefix[0],
        noisy_prefix[3] - noisy_prefix[1],
    ]

    result = engine.execute(
        "range",
        data=range_data,
        epsilon=1.0,
        bounds=bounds,
        ranges=ranges,
        mechanism=mech_range,
        metric="sum",
    )
    assert result == pytest.approx(expected)

    # range_mean -----------------------------------------------------------
    # 通过同一个向量机制对区间和与区间计数的前缀和分别加噪以重现区间均值估计算法
    mech_range_mean = _vector(10, 1.0, 1.0)
    mech_range_mean_exp = _vector(10, 1.0, 1.0)
    clipped = np.clip(np.asarray(range_data), *bounds)

    sum_prefix = [0.0, 1.0, 3.0, 6.0]
    width = len(sum_prefix) - 1
    span = bounds[1] - bounds[0]
    mech_range_mean_exp.calibrate(sensitivity=span * width)
    noisy_sum = np.asarray(mech_range_mean_exp.randomise(sum_prefix), dtype=float)

    count_prefix = [0.0, 1.0, 2.0, 3.0]
    mech_range_mean_exp.calibrate(sensitivity=width)
    noisy_count = np.asarray(mech_range_mean_exp.randomise(count_prefix), dtype=float)

    # 由带噪前缀和取差得到目标区间的带噪和与带噪计数并求均值后按 bounds 裁剪
    dp_sum = noisy_sum[3] - noisy_sum[0]
    dp_count = noisy_count[3] - noisy_count[0]
    expected_mean = float(np.clip(dp_sum / max(dp_count, 1e-6), bounds[0], bounds[1]))

    result_mean = engine.execute(
        "range",
        data=range_data,
        epsilon=1.0,
        bounds=bounds,
        ranges=[(0, 3)],
        mechanism=mech_range_mean,
        metric="mean",
    )
    assert result_mean == pytest.approx([expected_mean])
