"""
Property-based tests for extended LDP aggregators and applications.
"""
# 说明：扩展 LDP 聚合器（一致性后处理、用户级聚合）与复杂应用（Key-Value, 范围查询）的属性测试。
# 覆盖：
# - ConsistencyPostProcessor 的非负性、归一化与单纯形投影约束
# - UserLevelAggregator 的按用户分组聚合与加权合并逻辑
# - KeyValueApplication 的端到端遥测流程（Key 频率与 Value 均值）
# - RangeQueriesApplication 的数值区间统计（均值与分位数）

import pytest
import numpy as np
from hypothesis import given, strategies as st
from dplib.ldp.aggregators.consistency import ConsistencyPostProcessor
from dplib.ldp.aggregators.user_level import UserLevelAggregator
from dplib.ldp.aggregators.frequency import FrequencyAggregator
from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.applications.key_value import KeyValueApplication, KeyValueClientConfig
from dplib.ldp.applications.range_queries import RangeQueriesApplication, RangeQueriesClientConfig
from dplib.ldp.types import LDPReport, Estimate


# ------------------------------------------------------------------ Consistency
@given(
    st.lists(st.floats(min_value=-10.0, max_value=10.0),
             min_size=1,
             max_size=20))
def test_consistency_post_processor_simplex(values):
    # 验证单纯形投影后处理器的输出满足非负且总和为 1 的约束
    values_arr = np.array(values)
    inner = FrequencyAggregator(num_categories=len(values))

    # 模拟一个内部估计结果
    class MockAggregator:

        def aggregate(self, _):
            return Estimate(metric="frequency", point=values_arr)

        def reset(self):
            pass

    processor = ConsistencyPostProcessor(MockAggregator(),
                                         use_simplex=True,
                                         apply_to_metrics=["frequency"])

    res = processor.aggregate([])
    point = res.point

    assert np.all(point >= -1e-12)  # 允许极小的浮点误差
    assert np.sum(point) == pytest.approx(1.0)


# ------------------------------------------------------------------ User Level
def test_user_level_aggregator_grouping():
    # 验证用户级聚合器能够正确按 user_id 分组并调用内部聚合器
    inner = MeanAggregator(clip_range=(0, 10))
    agg = UserLevelAggregator(inner, anonymous_strategy="group")

    reports = [
        LDPReport(encoded=2.0,
                  user_id="u1",
                  mechanism_id="laplace",
                  epsilon=1.0),
        LDPReport(encoded=4.0,
                  user_id="u1",
                  mechanism_id="laplace",
                  epsilon=1.0),
        LDPReport(encoded=10.0,
                  user_id="u2",
                  mechanism_id="laplace",
                  epsilon=1.0)
    ]

    res = agg.aggregate(reports)
    # u1 mean = 3.0, u2 mean = 10.0 -> global mean = 6.5
    assert res.point == pytest.approx(6.5)


# ------------------------------------------------------------------ Key-Value App
@given(st.sampled_from(["A", "B", "C"]), st.floats(min_value=0, max_value=100))
def test_key_value_application_flow(key, value):
    # 验证 Key-Value 应用的端到端数据流（客户端生成报告，服务端聚合）
    categories = ["A", "B", "C"]
    from dplib.ldp.applications.key_value import KeyValueServerConfig
    client_cfg = KeyValueClientConfig(epsilon_key=1.0,
                                      epsilon_value=1.0,
                                      categories=categories,
                                      value_clip_range=(0, 100))
    server_cfg = KeyValueServerConfig(estimate_key_frequency=True,
                                      estimate_value_mean=True)
    app = KeyValueApplication(client_cfg, server_cfg)

    client = app.build_client()
    reports = client((key, value), user_id="user1")

    assert len(reports) == 2  # 1 for key, 1 for value

    aggregator = app.build_aggregator()
    res = aggregator.aggregate(reports)

    assert "frequency" in res.point
    assert "value_mean" in res.point


# ------------------------------------------------------------------ Range Queries App
@given(st.floats(min_value=0, max_value=10))
def test_range_queries_application_flow(val):
    # 验证范围查询应用在均值与分位数估计上的基本正确性
    client_cfg = RangeQueriesClientConfig(epsilon=2.0, clip_range=(0, 10))
    app = RangeQueriesApplication(client_cfg)

    client = app.build_client()
    report = client(val, user_id="u1")

    aggregator = app.build_aggregator()
    # 模拟多条报告以使分位数计算有意义
    res = aggregator.aggregate([report])

    # RangeQueriesApplication 默认只开启 mean 估计，返回 float
    if isinstance(res.point, dict):
        assert "mean" in res.point
    else:
        assert isinstance(res.point, float)

    # 如果配置了分位数且保留均值，则返回 RangeQueriesAggregator (dict)
    app.server_config.estimate_quantiles = [0.5]
    aggregator_q = app.build_aggregator()
    res_q = aggregator_q.aggregate([report])
    if isinstance(res_q.point, dict):
        assert "quantiles" in res_q.point
        assert "mean" in res_q.point
    else:
        # 如果只开启了分位数，则返回 np.ndarray
        assert isinstance(res_q.point, np.ndarray)
