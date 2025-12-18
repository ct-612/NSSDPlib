"""
Unit tests for the FrequencyAggregator over categorical LDP reports.
"""
# 说明：针对 LDP 频率估计聚合器 FrequencyAggregator 的单元测试。
# 覆盖：
# - GRR 场景下对整数索引报告进行去偏估计并验证频率归一性与排序关系
# - 带显式 p/q 的 bit 向量报告在 OUE 机制下的去偏行为与元数据记录
# - 缺省 p/q 元数据时基于 OUE 默认参数的近似估计路径
# - 从 LDPReport 元数据中推断 num_categories 与 p/q 参数的能力

import numpy as np
import pytest

from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.types import LDPReport


def test_frequency_grr_debias():
    # 验证 GRR 去偏估计能够在容差范围内恢复真实类别频率顺序并保持总和为 1
    # 验证在采样噪声存在时估计值仍能近似反映 0.5/0.3/0.2 的真值关系
    epsilon = 1.0
    reports = [
        LDPReport(user_id=i, mechanism_id="grr", encoded=0, epsilon=epsilon, metadata={})
        for i in range(5)
    ] + [
        LDPReport(user_id=i, mechanism_id="grr", encoded=1, epsilon=epsilon, metadata={})
        for i in range(5, 8)
    ] + [
        LDPReport(user_id=i, mechanism_id="grr", encoded=2, epsilon=epsilon, metadata={})
        for i in range(8, 10)
    ]
    agg = FrequencyAggregator(num_categories=3, mechanism="grr")
    est = agg.aggregate(reports)
    assert est.metric == "frequency"
    np.testing.assert_allclose(est.point.sum(), 1.0, atol=1e-6)
    # 真实频率约为 0.5、0.3、0.2
    assert est.point[0] > est.point[1] > est.point[2]


def test_frequency_bitvector_debias_with_pq():
    # 验证在显式提供 p/q 参数时对 bit 向量报告进行去偏后能得到预期频率分布
    p = 0.5
    q = 0.25
    reports = [
        LDPReport(
            user_id=1,
            mechanism_id="oue",
            encoded=np.array([1, 0, 0]),
            epsilon=1.0,
            metadata={"p": p, "q": q},
        ),
        LDPReport(
            user_id=2,
            mechanism_id="oue",
            encoded=np.array([0, 1, 0]),
            epsilon=1.0,
            metadata={"p": p, "q": q},
        ),
    ]
    agg = FrequencyAggregator(num_categories=3, mechanism="oue")
    est = agg.aggregate(reports)
    np.testing.assert_allclose(est.point, np.array([0.5, 0.5, 0.0]), atol=1e-6)
    assert est.metadata["approximation"] is None
    assert est.metadata["p"] == p and est.metadata["q"] == q


def test_frequency_bitvector_fallback_approximation():
    # 验证缺省 p/q 元数据时基于 OUE 默认参数仍能得到合理的频率估计与近似标记
    reports = [
        LDPReport(user_id=1, mechanism_id="oue", encoded=np.array([1, 0]), epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="oue", encoded=np.array([0, 1]), epsilon=1.0, metadata={}),
    ]
    agg = FrequencyAggregator(num_categories=2, mechanism="oue")
    est = agg.aggregate(reports)
    np.testing.assert_allclose(est.point, np.array([0.5, 0.5]), atol=1e-6)
    # 使用 OUE 默认值时可推断 p/q，因此 approximation 应为 None
    assert est.metadata["approximation"] is None


def test_frequency_infer_num_categories_from_metadata():
    # 验证在构造聚合器未显式给出 num_categories 时可从元数据中推断类别数与 p/q
    reports = [
        LDPReport(
            user_id=1,
            mechanism_id="grr",
            encoded=1,
            epsilon=1.0,
            metadata={"num_categories": 4, "prob_true": 0.7, "prob_false": 0.1},
        )
    ]
    agg = FrequencyAggregator(num_categories=None, mechanism="grr")
    est = agg.aggregate(reports)
    assert est.metadata["num_categories"] == 4
    assert est.metadata["p"] == 0.7
    assert est.metadata["q"] == 0.1
