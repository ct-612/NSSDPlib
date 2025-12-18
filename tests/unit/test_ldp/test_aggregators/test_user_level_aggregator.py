"""
Unit tests for the UserLevelAggregator over numeric LDP reports.
"""
# 说明：针对 UserLevelAggregator 在不同分组与加权策略下的用户级聚合行为进行单元测试。
# 覆盖：
# - 按 user_id 分组后结合内部 MeanAggregator 的基本均值聚合逻辑
# - 等权重与按报告数加权两种 weight_mode 的差异
# - 匿名用户丢弃策略 anonymous_strategy="drop" 对有效用户数与结果的影响
# - 自定义 reducer 函数替代默认均值聚合的行为

import numpy as np
import pytest

from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.aggregators.user_level import UserLevelAggregator
from dplib.ldp.types import LDPReport


def test_user_level_grouping_and_equal_weights():
    # 验证在等权重模式下不同用户的均值先按 user_id 聚合再做简单平均
    inner_aggregator = MeanAggregator()
    agg = UserLevelAggregator(inner_aggregator=inner_aggregator, weight_mode="equal")
    reports = [
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=3.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u2", mechanism_id="laplace", encoded=10.0, epsilon=1.0, metadata={}),
    ]
    est = agg.aggregate(reports)
    # u1 mean =2, u2 mean=10, equal weight -> (2+10)/2=6
    assert est.point == pytest.approx(6.0)
    assert est.metadata["num_users"] == 2


def test_user_level_report_count_weighting():
    # 验证当 weight_mode 为 report_count 时会按每个用户的报告数量做加权平均
    inner_aggregator = MeanAggregator()
    agg = UserLevelAggregator(inner_aggregator=inner_aggregator, weight_mode="report_count")
    reports = [
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=3.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u2", mechanism_id="laplace", encoded=10.0, epsilon=1.0, metadata={}),
    ]
    est = agg.aggregate(reports)
    # weights: u1 has 2 reports, u2 has 1. Weighted mean = (2*2 + 1*10)/3 = 14/3
    assert est.point == pytest.approx(14 / 3)
    assert est.metadata["weight_mode"] == "report_count"


def test_user_level_anonymous_strategy_drop():
    # 验证 anonymous_strategy="drop" 时会丢弃 user_id 为空的报告，只对有标识用户聚合
    inner_aggregator = MeanAggregator()
    agg = UserLevelAggregator(inner_aggregator=inner_aggregator, anonymous_strategy="drop")
    reports = [
        LDPReport(user_id=None, mechanism_id="laplace", encoded=5.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=2.0, epsilon=1.0, metadata={}),
    ]
    est = agg.aggregate(reports)
    assert est.metadata["num_users"] == 1
    assert est.point == pytest.approx(1.5)


def test_user_level_custom_reducer():
    # 验证通过自定义 reducer（如取最大值）可以覆盖默认的均值合并策略
    inner_aggregator = MeanAggregator()
    # 自定义 reducer：取用户级 point 的最大值
    agg = UserLevelAggregator(inner_aggregator=inner_aggregator, reducer=lambda pts: max(pts))
    reports = [
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u1", mechanism_id="laplace", encoded=3.0, epsilon=1.0, metadata={}),
        LDPReport(user_id="u2", mechanism_id="laplace", encoded=10.0, epsilon=1.0, metadata={}),
    ]
    est = agg.aggregate(reports)
    assert est.metadata["num_users"] == 2
    assert est.point == pytest.approx(10.0)
