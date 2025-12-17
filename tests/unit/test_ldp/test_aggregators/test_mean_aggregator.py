"""
Unit tests for the MeanAggregator over numeric LDP reports.
"""
# 说明：针对 MeanAggregator 的数值型 LDP 报告聚合行为进行单元测试。
# 覆盖：
# - 带噪声方差参数时对均值与去噪方差的估计逻辑
# - 空报告列表时的异常抛出行为
# - 从报告元数据中提供噪声信息但未在构造器中指定时的兼容性与元数据记录

import numpy as np
import pytest

from dplib.ldp.aggregators.mean import MeanAggregator
from dplib.ldp.types import LDPReport


def test_mean_aggregator_basic_and_noise_subtraction():
    # 验证在提供 noise_variance 时计算样本均值并对观测方差进行噪声方差扣除
    reports = [
        LDPReport(user_id=1, mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="laplace", encoded=3.0, epsilon=1.0, metadata={}),
    ]
    agg = MeanAggregator(noise_variance=1.0)
    est = agg.aggregate(reports)
    assert est.metric == "mean"
    assert est.point == pytest.approx(2.0)
    # [1,3] 的观测方差（ddof=1）为 2.0；去除噪声方差 1.0 后为 1.0
    assert est.variance == pytest.approx(1.0)
    assert est.metadata["observed_variance"] == pytest.approx(2.0)
    assert est.metadata["noise_variance"] == 1.0


def test_mean_aggregator_no_reports_raises():
    # 验证在输入空报告列表时聚合器会抛出异常而不是返回非法结果
    agg = MeanAggregator()
    with pytest.raises(Exception):
        agg.aggregate([])


def test_mean_aggregator_metadata_noise_from_report():
    # 验证噪声方差仅由构造参数控制，元数据中的 noise_variance 不参与去噪逻辑
    reports = [
        LDPReport(user_id=1, mechanism_id="laplace", encoded=0.0, epsilon=1.0, metadata={"noise_variance": 0.2}),
        LDPReport(user_id=2, mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={"noise_variance": 0.2}),
    ]
    # 构造器未传 noise_variance，元数据中的噪声信息不应影响聚合流程
    agg = MeanAggregator()
    est = agg.aggregate(reports)
    assert est.metadata["noise_variance"] is None  # 是否去噪由构造参数决定
