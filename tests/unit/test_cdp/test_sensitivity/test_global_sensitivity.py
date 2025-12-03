"""
Tests for global sensitivity wrapper functions.
"""
# 说明：全局敏感度封装函数及其区间变体 range 的单元测试。
# 覆盖：
# - 基本统计量 count/sum/mean/variance/histogram 的全局敏感度包装是否返回预期解析值
# - 区间 range 在 sum/mean/count 三种 metric 下的敏感度计算是否一致且与参数设置相符

import pytest

from dplib.cdp.sensitivity import count, histogram, mean, range, sum, variance
from dplib.core.data import ContinuousDomain


def test_global_sensitivity_wrappers_cover_range_variants() -> None:
    # 验证各全局敏感度封装函数以及 range 在不同 metric 下的返回值是否符合理论敏感度
    domain = ContinuousDomain(minimum=0.0, maximum=5.0)
    assert count(max_contribution=2) == 2.0
    assert sum(domain, max_contribution=1) == pytest.approx(5.0)
    assert mean(domain, sample_size=5, max_contribution=1) == pytest.approx(1.0)
    assert variance(domain, sample_size=5, ddof=1, max_contribution=1) == pytest.approx(6.25)
    assert histogram(max_contribution=3) == pytest.approx(3.0)

    assert range(domain, window=3, max_contribution=1, metric="sum") == pytest.approx(15.0)
    assert range(domain, window=3, max_contribution=1, metric="mean") == pytest.approx(5.0)
    assert range(domain, window=3, max_contribution=3, metric="count") == pytest.approx(3.0)
