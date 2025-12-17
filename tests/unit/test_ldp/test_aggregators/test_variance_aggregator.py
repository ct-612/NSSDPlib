"""
Unit tests for the VarianceAggregator over numeric LDP reports.
"""
# 说明：针对 VarianceAggregator 在存在或缺省噪声方差设置下的方差估计行为进行单元测试。
# 覆盖：
# - 在提供 noise_variance 时按观测方差减去噪声方差并输出去噪结果
# - 空报告列表触发异常的错误分支
# - 报告元数据中包含 noise_variance 但未在构造函数传入时不执行去噪只记录观测结果

import numpy as np
import pytest

from dplib.ldp.aggregators.variance import VarianceAggregator
from dplib.ldp.types import LDPReport


def test_variance_aggregator_noise_subtraction():
    # 验证在指定 noise_variance 时方差估计会从观测方差中减去噪声贡献并记录去噪标记
    reports = [
        LDPReport(user_id=1, mechanism_id="laplace", encoded=0.0, epsilon=1.0, metadata={}),
        LDPReport(user_id=2, mechanism_id="laplace", encoded=2.0, epsilon=1.0, metadata={}),
    ]
    agg = VarianceAggregator(noise_variance=0.5)
    est = agg.aggregate(reports)
    assert est.metric == "variance"
    observed_variance = 2.0  # 数值 [0,2] 在 ddof=1 时的方差
    assert est.metadata["observed_variance"] == pytest.approx(observed_variance)
    assert est.point == pytest.approx(max(observed_variance - 0.5, 0.0))
    assert est.metadata["noise_adjusted"] is True


def test_variance_aggregator_no_reports_raises():
    # 验证在空报告列表输入时会抛出异常避免返回无意义的估计结果
    agg = VarianceAggregator()
    with pytest.raises(Exception):
        agg.aggregate([])


def test_variance_metadata_noise_from_report():
    # 验证噪声方差仅由构造参数控制，元数据中的 noise_variance 不参与去噪逻辑
    reports = [
        LDPReport(user_id=1, mechanism_id="laplace", encoded=1.0, epsilon=1.0, metadata={"noise_variance": 0.3}),
        LDPReport(user_id=2, mechanism_id="laplace", encoded=2.0, epsilon=1.0, metadata={"noise_variance": 0.3}),
    ]
    agg = VarianceAggregator()
    est = agg.aggregate(reports)
    assert est.metadata["noise_variance"] is None  # 是否去噪由构造参数决定
