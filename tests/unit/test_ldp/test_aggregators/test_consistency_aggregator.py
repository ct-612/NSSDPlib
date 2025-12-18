"""
Unit tests for consistency post-processing helpers and wrapper aggregator.
"""
# 说明：LDP 频率一致性后处理工具函数及 ConsistencyPostProcessor 包装器的单元测试。
# 覆盖：
# - 非负裁剪与归一化工具函数在典型输入上的数值行为
# - simplex 投影在单向量与按轴批量输入场景下的形状与和为 1 约束
# - 单调性约束函数在递增与递减两种模式下的累计 max/min 行为
# - ConsistencyPostProcessor 包裹 FrequencyAggregator 后的非负归一与 postprocessed 元数据标记
# - ConsistencyPostProcessor 开启单调递增约束时结果在误差容忍范围内保持非递减
# - apply_to_metrics 为空时的异常路径以及 strict_metrics 打开/关闭时的过滤与报错行为

import numpy as np
import pytest

from dplib.ldp.aggregators.consistency import (
    ConsistencyPostProcessor,
    enforce_monotonic,
    enforce_non_negative,
    normalize_probabilities,
    project_simplex,
)
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.types import LDPReport


def test_enforce_non_negative_and_normalize():
    # 验证向量经非负裁剪后所有元素 >= 0 且归一化后总和接近 1
    vec = np.array([-0.1, 0.2, 0.3])
    clipped = enforce_non_negative(vec)
    assert (clipped >= 0).all()
    normalized = normalize_probabilities(clipped)
    np.testing.assert_allclose(normalized.sum(), 1.0, atol=1e-9)


def test_project_simplex_basic_and_axis():
    # 验证单个向量及按轴批量输入在 simplex 投影后均为非负且每个向量的和为 1
    vec = np.array([0.2, -0.1, 0.9])
    projected = project_simplex(vec)
    np.testing.assert_allclose(projected.sum(), 1.0, atol=1e-9)
    assert (projected >= 0).all()

    batch = np.vstack([vec, vec])
    projected_batch = project_simplex(batch, axis=1)
    assert projected_batch.shape == batch.shape
    np.testing.assert_allclose(projected_batch.sum(axis=1), np.ones(2), atol=1e-9)


def test_enforce_monotonic_increasing_and_decreasing():
    # 验证单调性约束函数对递增和递减两种模式下的累计 max/min 行为
    vec = np.array([0.5, 0.4, 0.6, 0.3])
    inc = enforce_monotonic(vec, increasing=True)
    dec = enforce_monotonic(vec, increasing=False)
    assert np.all(np.diff(inc) >= 0)
    assert np.all(np.diff(dec) <= 0)


def test_consistency_postprocessor_pipeline():
    # 验证 ConsistencyPostProcessor 包裹频率聚合器后输出非负归一且打上 postprocessed 标记
    reports = [
        LDPReport(user_id=1, mechanism_id="grr", encoded=0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="grr", encoded=1, epsilon=1.0, metadata={}),
    ]
    freq = FrequencyAggregator(num_categories=2, mechanism="grr")
    wrapper = ConsistencyPostProcessor(
        inner_aggregator=freq,
        apply_to_metrics=("frequency",),
        non_negative=True,
        normalize=True,
        use_simplex=True,
        monotonic=False,
    )
    est = wrapper.aggregate(reports)
    assert est.metadata.get("postprocessed") is True
    np.testing.assert_allclose(est.point.sum(), 1.0, atol=1e-9)
    assert (np.asarray(est.point) >= 0).all()


def test_consistency_postprocessor_monotonic():
    # 验证启用单调递增约束后聚合结果在误差容忍范围内保持非递减
    reports = [
        LDPReport(user_id=1, mechanism_id="grr", encoded=0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="grr", encoded=1, epsilon=1.0, metadata={}),
    ]
    freq = FrequencyAggregator(num_categories=2, mechanism="grr")
    wrapper = ConsistencyPostProcessor(
        inner_aggregator=freq,
        apply_to_metrics=("frequency",),
        non_negative=True,
        normalize=True,
        use_simplex=False,
        monotonic=True,
        monotonic_increasing=True,
    )
    est = wrapper.aggregate(reports)
    assert np.all(np.diff(np.asarray(est.point)) >= -1e-9)


def test_consistency_postprocessor_apply_to_metrics_filter():
    # 验证 apply_to_metrics 为空时构造阶段抛出异常，以及 strict_metrics 不同配置的行为
    reports = [
        LDPReport(user_id=1, mechanism_id="grr", encoded=0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="grr", encoded=1, epsilon=1.0, metadata={}),
    ]
    freq = FrequencyAggregator(num_categories=2, mechanism="grr")
    with pytest.raises(Exception):
        ConsistencyPostProcessor(inner_aggregator=freq, apply_to_metrics=())

    wrapper = ConsistencyPostProcessor(
        inner_aggregator=freq,
        apply_to_metrics=("mean",),
        strict_metrics=False,
    )
    est = wrapper.aggregate(reports)
    assert est.metadata.get("apply_to_metrics") == ["mean"]

    wrapper_strict = ConsistencyPostProcessor(
        inner_aggregator=freq,
        apply_to_metrics=("mean",),
        strict_metrics=True,
    )
    with pytest.raises(Exception):
        wrapper_strict.aggregate(reports)
