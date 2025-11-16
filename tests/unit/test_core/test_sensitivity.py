"""
Unit tests for sensitivity utilities.
"""
# 说明：敏感度（全局 / 局部 / 平滑）相关工具函数的单元测试。
# 覆盖：
# - 计数查询 count_global_sensitivity 的贡献上限约束与非法参数错误
# - 有界连续域上 sum_global_sensitivity / mean_global_sensitivity 的解析全局敏感度
# - local_sensitivity 对样本向量的 L1 / L2 局部敏感度计算
# - smooth_sensitivity_mean 返回 SmoothSensitivityEstimate 及估计值为正
# - 空输入、非正 max_contribution 等情况下抛出 SensitivityError

import pytest

from dplib.core.data import (
    ContinuousDomain,
    SmoothSensitivityEstimate,
    SensitivityError,
    count_global_sensitivity,
    local_sensitivity,
    mean_global_sensitivity,
    smooth_sensitivity_mean,
    sum_global_sensitivity,
)


def test_count_global_sensitivity_respects_contribution_limit() -> None:
    # 计数查询的全局敏感度应等于 max_contribution，非正参数应触发异常。
    assert count_global_sensitivity(max_contribution=2) == 2.0
    with pytest.raises(SensitivityError):
        count_global_sensitivity(max_contribution=0)


def test_sum_and_mean_global_sensitivity() -> None:
    # 验证有界连续域上 sum / mean 的全局敏感度解析公式是否正确。
    domain = ContinuousDomain(minimum=0.0, maximum=5.0)
    assert sum_global_sensitivity(domain, max_contribution=1) == 5.0
    assert mean_global_sensitivity(domain, sample_size=5) == 1.0


def test_local_sensitivity_l1_and_l2() -> None:
    # 检查给定样本向量的 L1 / L2 局部敏感度，并对空输入抛出错误。
    values = [0.0, 0.5, 1.5, 2.0]
    assert local_sensitivity(values, metric="l1") == pytest.approx(1.0)
    assert local_sensitivity(values, metric="l2") == pytest.approx(1.0)
    with pytest.raises(SensitivityError):
        local_sensitivity([], metric="l1")


def test_smooth_sensitivity_mean_returns_positive_estimate() -> None:
    # 验证均值的平滑敏感度估计返回 SmoothSensitivityEstimate 且值为正，空输入时报错。
    estimate = smooth_sensitivity_mean([1.0, 2.0, 3.0], beta=0.5)
    assert isinstance(estimate, SmoothSensitivityEstimate)
    assert estimate.estimate > 0
    with pytest.raises(SensitivityError):
        smooth_sensitivity_mean([], beta=0.5)
