"""
Unit tests for sensitivity utilities.
"""
# 说明：针对连续域敏感度工具函数与平滑敏感度估计的单元测试。
# 覆盖：
# - 计数全局敏感度在最大贡献约束下的线性缩放与非法参数校验
# - 连续有界域上的 sum 与 mean 全局敏感度计算正确性
# - 方差、直方图与滑动区间 range 等高级查询的全局敏感度上界
# - 本地敏感度在 L1 与 L2 度量下的行为及空样本错误分支
# - 平滑均值敏感度估计的返回类型与正值约束以及非法输入处理

import pytest

from dplib.core.data import (
    ContinuousDomain,
    SmoothSensitivityEstimate,
    SensitivityError,
    count_global_sensitivity,
    histogram_global_sensitivity,
    local_sensitivity,
    mean_global_sensitivity,
    range_global_sensitivity,
    smooth_sensitivity_mean,
    sum_global_sensitivity,
    variance_global_sensitivity,
)


def test_count_global_sensitivity_respects_contribution_limit() -> None:
    # 验证计数查询的全局敏感度与 max_contribution 一致并对非正值抛出异常
    assert count_global_sensitivity(max_contribution=2) == 2.0
    with pytest.raises(SensitivityError):
        count_global_sensitivity(max_contribution=0)


def test_sum_and_mean_global_sensitivity() -> None:
    # 验证 sum 与 mean 在简单连续域上的闭式全局敏感度公式
    domain = ContinuousDomain(minimum=0.0, maximum=5.0)
    assert sum_global_sensitivity(domain, max_contribution=1) == 5.0
    assert mean_global_sensitivity(domain, sample_size=5) == 1.0


def test_variance_histogram_and_range_sensitivity() -> None:
    # 检查方差、直方图与固定窗口区间求和的全局敏感度实现是否满足理论上界
    domain = ContinuousDomain(minimum=0.0, maximum=4.0)
    assert variance_global_sensitivity(domain, sample_size=4, ddof=1) == pytest.approx(4.0)
    assert histogram_global_sensitivity(max_contribution=2) == 2.0
    assert range_global_sensitivity(domain, window=3) == pytest.approx(12.0)


def test_local_sensitivity_l1_and_l2() -> None:
    # 验证给定样本向量的 L1 / L2 局部敏感度计算并对空输入抛出异常
    values = [0.0, 0.5, 1.5, 2.0]
    assert local_sensitivity(values, metric="l1") == pytest.approx(1.0)
    assert local_sensitivity(values, metric="l2") == pytest.approx(1.0)
    with pytest.raises(SensitivityError):
        local_sensitivity([], metric="l1")


def test_smooth_sensitivity_mean_returns_positive_estimate() -> None:
    # 验证均值的平滑敏感度估计返回的类型且估计值为正，并对空输入抛出异常
    estimate = smooth_sensitivity_mean([1.0, 2.0, 3.0], beta=0.5)
    assert isinstance(estimate, SmoothSensitivityEstimate)
    assert estimate.estimate > 0
    with pytest.raises(SensitivityError):
        smooth_sensitivity_mean([], beta=0.5)
