"""
Tests for sensitivity bounds helpers.
"""
# 说明：敏感度区间辅助函数和 tighten 调整工具的单元测试。
# 覆盖：
# - 常见统计查询的敏感度区间工厂函数是否返回 SensitivityBounds
# - 区间下界固定为 0 且上界非负等基本不变量
# - tighten 在给定观测值时是否能按观测值收紧上界

from dplib.cdp.sensitivity.sensitivity_bounds import (
    SensitivityBounds,
    count_bounds,
    histogram_bounds,
    mean_bounds,
    range_bounds,
    sum_bounds,
    tighten,
    variance_bounds,
)
from dplib.core.data import ContinuousDomain


def test_bounds_and_tighten_cover_all_queries() -> None:
    # 检查所有定义的敏感度区间工厂函数都能生成合法区间并验证 tighten 的收紧行为
    domain = ContinuousDomain(minimum=0.0, maximum=2.0)
    cb = count_bounds(max_contribution=2)
    sb = sum_bounds(domain, max_contribution=1)
    mb = mean_bounds(domain, sample_size=4, max_contribution=1)
    vb = variance_bounds(domain, sample_size=4, ddof=1, max_contribution=1)
    hb = histogram_bounds(max_contribution=1)
    rb_sum = range_bounds(domain, window=2, max_contribution=1, metric="sum")
    rb_mean = range_bounds(domain, window=2, max_contribution=1, metric="mean")
    rb_count = range_bounds(domain, window=2, max_contribution=3, metric="count")

    for bounds in (cb, sb, mb, vb, hb, rb_sum, rb_mean, rb_count):
        assert isinstance(bounds, SensitivityBounds)
        assert bounds.lower == 0.0
        assert bounds.upper >= 0.0

    tightened = tighten(sb, observed=0.5)
    assert tightened.upper == 0.5
