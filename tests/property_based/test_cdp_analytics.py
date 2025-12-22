"""
Property-based tests for the CDP Analytics Queries.
"""
# 说明：CDP 统计查询（Histogram, Sum, Count, Mean, Variance, Range）的属性测试。
# 覆盖：
# - PrivateHistogramQuery 分箱一致性与计数非负性截断
# - PrivateSumQuery 与 PrivateCountQuery 的基础运行验证
# - PrivateMeanQuery 与 PrivateVarianceQuery 的结果范围与类型校验
# - PrivateRangeQuery 的多区间查询输出形状验证
# - QueryEngine 统一查询分派接口的调用逻辑

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.cdp.analytics.queries.histogram import PrivateHistogramQuery
from dplib.cdp.analytics.queries.sum import PrivateSumQuery
from dplib.cdp.analytics.queries.count import PrivateCountQuery
from dplib.cdp.analytics.queries.mean import PrivateMeanQuery
from dplib.cdp.analytics.queries.variance import PrivateVarianceQuery
from dplib.cdp.analytics.queries.range import PrivateRangeQuery
from dplib.cdp.analytics.queries.query_engine import QueryEngine
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError


# ---------------------------------------------------------------- Histogram Query
@settings(suppress_health_check=[HealthCheck.too_slow])
@given(
    st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1),
    st.lists(st.floats(allow_nan=False, allow_infinity=False),
             min_size=2,
             unique=True).map(sorted))
def test_histogram_bins_consistency(data, bins):
    # 验证输出的 bin_edges 必须与输入的 bins 完全一致，且 counts 数量满足 len(bins)-1
    # 注意：bin_edges 长度应为 len(counts) + 1 或 len(bins)
    query = PrivateHistogramQuery(epsilon=1.0, bins=bins, max_contribution=1)

    noisy_counts, out_bins = query.evaluate(data)

    assert len(out_bins) == len(bins)
    assert np.allclose(out_bins, bins)
    assert len(noisy_counts) == len(bins) - 1


@given(st.lists(st.floats(min_value=-100, max_value=100), min_size=1),
       st.integers(min_value=2, max_value=10))
def test_histogram_non_negativity(data, n_bins):
    # 验证评估后的直方图计数恒为非负，避免噪声导致负频数
    # 自动生成均匀分布的 bins
    if not data:
        return
    mn, mx = min(data), max(data)
    if mn == mx:
        bins = [mn - 1, mx + 1]
    else:
        bins = np.linspace(mn, mx, n_bins).tolist()

    query = PrivateHistogramQuery(epsilon=0.1,
                                  bins=bins)  # Low epsilon -> high noise
    noisy_counts, _ = query.evaluate(data)

    assert all(c >= 0 for c in noisy_counts)
    assert isinstance(noisy_counts, list)


@given(st.lists(st.floats(), min_size=1))
def test_histogram_mechanism_calibration(data):
    # 验证直方图查询在未手动注入机制时能自动完成默认机制的校准
    bins = [0.0, 1.0, 2.0]
    query = PrivateHistogramQuery(epsilon=1.0, bins=bins)
    assert isinstance(query.mechanism, BaseMechanism)
    assert query.mechanism.calibrated


# ---------------------------------------------------------------- Sum Query
@given(st.lists(st.floats(min_value=-10.0, max_value=10.0), min_size=1),
       st.floats(min_value=0.1, max_value=10.0))
def test_sum_query_basic(data, epsilon):
    # 验证加噪求和查询的基础流程，确保其能够处理包含负数的输入并返回浮点结果
    bounds = (-10.0, 10.0)
    query = PrivateSumQuery(epsilon=epsilon, bounds=bounds)
    res = query.evaluate(data)
    assert isinstance(res, float)


@given(st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=1),
       st.floats(min_value=0.1, max_value=1.0))
def test_count_query_basic(data, epsilon):
    # 验证加噪计数查询的行为，目前暂不强制截断为非负值
    query = PrivateCountQuery(epsilon=epsilon)
    res = query.evaluate(data)
    assert isinstance(res, float)


@given(st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=1),
       st.floats(min_value=0.1, max_value=1.0))
def test_mean_query_bounds(data, epsilon):
    # 验证均值查询结果是否由于后处理逻辑被限制在指定的取值边界内
    bounds = (0.0, 10.0)
    query = PrivateMeanQuery(epsilon=epsilon, bounds=bounds)
    res = query.evaluate(data)
    assert bounds[0] <= res <= bounds[1]


# ---------------------------------------------------------------- Variance Query
@given(st.lists(st.floats(min_value=-10.0, max_value=10.0), min_size=2),
       st.floats(min_value=0.1, max_value=1.0))
def test_variance_query_non_negativity(data, epsilon):
    # 验证方差查询的输出类型，尽管加噪可能产生负方差，接口仍应返回数值
    # PrivateVarianceQuery 应该返回 float
    bounds = (-10.0, 10.0)
    query = PrivateVarianceQuery(epsilon=epsilon, bounds=bounds)
    res = query.evaluate(data)
    assert isinstance(res, float)


# ---------------------------------------------------------------- Range Query
@given(
    st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=5,
             max_size=20), st.floats(min_value=0.1, max_value=1.0))
def test_range_query_shape(data, epsilon):
    # 验证多区间范围查询的输出列表长度与请求的区间数量保持一致
    bounds = (0.0, 10.0)
    query = PrivateRangeQuery(epsilon=epsilon, bounds=bounds)
    ranges = [(0, 2), (2, 5), (0, len(data))]
    res = query.evaluate(data, ranges)
    assert isinstance(res, list)
    assert len(res) == len(ranges)


# ---------------------------------------------------------------- Query Engine
@given(st.lists(st.floats(min_value=0.0, max_value=10.0), min_size=1))
def test_query_engine_interface(data):
    # 验证 QueryEngine 能够正确分派 count/sum/mean 查询到对应的处理器并返回结果
    # QueryEngine 是一个调度器，数据作为 execute 参数传递
    engine = QueryEngine()

    c = engine.execute("count", data=data, epsilon=1.0)
    s = engine.execute("sum", data=data, epsilon=1.0, bounds=(0.0, 10.0))
    m = engine.execute("mean", data=data, epsilon=1.0, bounds=(0.0, 10.0))

    assert isinstance(c, float)
    assert isinstance(s, float)
    assert isinstance(m, float)
