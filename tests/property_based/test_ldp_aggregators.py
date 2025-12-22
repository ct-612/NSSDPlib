"""
Property-based tests for the LDP Aggregators.
"""
# 说明：本地化差分隐私（LDP）聚合器（Mean, Frequency, Quantile, Variance）的属性测试。
# 覆盖：
# - MeanAggregator 在零噪声场景下的均值与方差聚合准确性
# - FrequencyAggregator 的输出分布归一化特性与非负性截断
# - QuantileAggregator 的输出维度一致性与元数据解析逻辑
# - VarianceAggregator 对去噪逻辑的实现及其在无噪声配置下的观测一致性

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.aggregators.quantile import QuantileAggregator
from dplib.ldp.aggregators.variance import VarianceAggregator
from dplib.ldp.types import LDPReport


# ---------------------------------------------------------------- Mean Aggregator
@given(
    st.lists(st.floats(min_value=-100, max_value=100), min_size=1,
             max_size=20))
def test_mean_aggregator_deterministic(values):
    # 验证在无噪声注入的情况下，均值聚合器能够还原出输入的算术平均值与样本方差
    aggregator = MeanAggregator(noise_variance=0.0)
    reports = [
        LDPReport(encoded=v, mechanism_id="test", user_id="u", epsilon=1.0)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)

    assert estimate.point == pytest.approx(np.mean(values))
    if len(values) > 1:
        # np.var ddof=0 by default, but aggregator uses ddof=1
        expected_var = np.var(values, ddof=1)
        assert estimate.variance == pytest.approx(expected_var)


@given(
    st.lists(st.floats(min_value=-1e30,
                       max_value=1e30,
                       allow_nan=False,
                       allow_infinity=False),
             min_size=1,
             max_size=20))
def test_mean_aggregator_metadata(values):
    # 验证聚合生成的结果对象中记录的报告总数是否与输入报告列表长度相匹配
    aggregator = MeanAggregator()
    reports = [
        LDPReport(encoded=v, mechanism_id="test", user_id="u", epsilon=1.0)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)

    assert estimate.metadata["n_reports"] == len(values)


@given(st.floats(min_value=0.1, max_value=10.0),
       st.floats(min_value=0.0, max_value=10.0))
def test_mean_aggregator_denoising_non_negative(obs_var, noise_var):
    # 验证均值聚合器的去噪逻辑能否正确处理观测方差小于噪声方差的极端情况并截断为零
    aggregator = MeanAggregator(noise_variance=noise_var)

    # 构造两个值，使其样本方差严格等于 obs_var
    # x = sqrt(2 * obs_var)
    x = np.sqrt(2 * obs_var)
    reports = [
        LDPReport(encoded=0.0, mechanism_id="m", user_id="u1", epsilon=1.0),
        LDPReport(encoded=x, mechanism_id="m", user_id="u2", epsilon=1.0)
    ]

    estimate = aggregator.aggregate(reports)

    if obs_var < noise_var:
        assert estimate.variance == 0.0
    else:
        assert estimate.variance == pytest.approx(obs_var - noise_var)


# ---------------------------------------------------------------- Frequency Aggregator
@given(st.lists(st.integers(min_value=0, max_value=9), min_size=1,
                max_size=20))
def test_frequency_aggregator_normalization(values):
    # 验证频率聚合器的估计结果在所有类别上的概率总和应严格（或近似）等于 1.0
    k = 10
    epsilon = 1.0
    aggregator = FrequencyAggregator(num_categories=k)

    # 构造携带隐私参数的报告集用于频率去偏推断
    reports = [
        LDPReport(encoded=v, mechanism_id="grr", user_id="u", epsilon=epsilon)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)

    # 验证非负性与归一化
    assert np.all(estimate.point >= 0)
    assert np.sum(estimate.point) == pytest.approx(1.0)
    assert estimate.metadata["num_categories"] == k


@given(st.lists(st.integers(min_value=0, max_value=4), min_size=1,
                max_size=20))
def test_frequency_aggregator_non_negativity(values):
    # 验证在强噪声环境下去偏可能导致的负频数会被聚合处理逻辑强制截断为非负
    k = 5
    aggregator = FrequencyAggregator(num_categories=k)
    reports = [
        LDPReport(encoded=v, mechanism_id="grr", user_id="u", epsilon=0.1)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)
    assert np.all(estimate.point >= 0.0)


# ---------------------------------------------------------------- Quantile Aggregator
@given(
    st.lists(st.floats(min_value=0.0, max_value=1.0), min_size=1, max_size=5),
    st.integers(min_value=1, max_value=20))
def test_quantile_output_dimension(quantiles, n_values):
    # 验证分位数聚合器返回的估计点集大小是否与请求的分位点数量完全对齐
    aggregator = QuantileAggregator(quantiles=quantiles)
    # 构造基础观测值报告
    reports = [
        LDPReport(encoded=float(i),
                  mechanism_id="lap",
                  user_id="u",
                  epsilon=1.0) for i in range(n_values)
    ]

    estimate = aggregator.aggregate(reports)

    # 验证输出类型与形状
    res = np.asarray(estimate.point)
    assert res.shape == (len(quantiles), )
    assert isinstance(estimate.point, (np.ndarray, list, tuple))


@given(st.floats(min_value=0.1, max_value=10.0))
def test_quantile_noise_resolution(noise_std):
    # 验证分位数聚合器在未显式传递配置时，能从报告的元数据中自动动态提取噪声参数
    aggregator = QuantileAggregator(quantiles=[0.5], method="linear")

    # 将噪声标准差与类型注入报告元数据
    reports = [
        LDPReport(encoded=1.0,
                  mechanism_id="lap",
                  user_id="u",
                  epsilon=1.0,
                  metadata={
                      "noise_std": noise_std,
                      "noise_type": "laplace"
                  })
    ]

    estimate = aggregator.aggregate(reports)

    assert estimate.metadata["noise_std"] == pytest.approx(noise_std)
    assert estimate.metadata["noise_type"] == "laplace"


# ---------------------------------------------------------------- Variance Aggregator
@given(
    st.lists(st.floats(min_value=-10.0, max_value=10.0),
             min_size=2,
             max_size=20), st.floats(min_value=0.0, max_value=1.0))
def test_variance_aggregator_non_negativity(values, noise_var):
    # 验证方差聚合器在执行去噪减法后，其最终返回的方差估计值始终保持非负
    aggregator = VarianceAggregator(noise_variance=noise_var)
    reports = [
        LDPReport(encoded=v, mechanism_id="lap", user_id="u", epsilon=1.0)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)
    assert estimate.point >= 0.0


@given(
    st.lists(st.floats(min_value=-10.0, max_value=10.0),
             min_size=2,
             max_size=20))
def test_variance_aggregator_observed(values):
    # 验证当未指定噪声方差时，聚合器返回的结果应当退化为当前样本集的普通观测方差
    aggregator = VarianceAggregator(noise_variance=None)
    reports = [
        LDPReport(encoded=v, mechanism_id="lap", user_id="u", epsilon=1.0)
        for v in values
    ]

    estimate = aggregator.aggregate(reports)

    expected_var = np.var(values, ddof=1)
    # 验证浮点数结果的一致性
    assert estimate.point == pytest.approx(float(expected_var))
