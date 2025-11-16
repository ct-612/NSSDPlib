"""
Unit tests for basic statistical utilities.
"""
# 说明：基础统计工具与在线统计 RunningStats 的单元测试。
# 覆盖：
# - count / summation：样本数量与总和计算行为
# - mean / variance：均值与方差结果是否符合预期（含 ddof 自由度参数）
# - histogram：给定分箱边界时的每箱计数与边界数组返回
# - RunningStats：在线更新得到的均值 / 方差与批量 variance 结果是否一致

import pytest

from dplib.core.data import (
    RunningStats,
    count,
    histogram,
    mean,
    summation,
    variance,
)


def test_count_and_summation() -> None:
    # 验证简单整数序列的计数与求和结果。
    values = [1, 2, 3]
    assert count(values) == 3
    assert summation(values) == 6.0


def test_mean_and_variance_match_expected() -> None:
    # 检查 mean / variance 是否与预期标量结果一致（含 ddof=1 的无偏估计）。
    values = [1.0, 2.0, 3.0, 4.0]
    assert pytest.approx(mean(values)) == 2.5
    assert pytest.approx(variance(values, ddof=1)) == pytest.approx(1.6666666667)


def test_histogram_counts_per_bin() -> None:
    # 验证 histogram 在指定分箱边界下的计数，以及返回的 bins 边界是否正确。
    counts, bins = histogram([1.0, 1.5, 2.4, 4.9], bins=[1.0, 2.0, 3.0, 5.0])
    assert counts == [2, 1, 1]
    assert bins[-1] == 5.0


def test_running_stats_matches_batch_variance() -> None:
    # 使用 RunningStats 在线更新样本，检查其均值 / 方差与批量 variance 结果是否一致。
    stats = RunningStats()
    values = [1.0, 2.0, 3.0, 4.0]
    for value in values:
        stats.update(value)
    assert pytest.approx(stats.mean) == pytest.approx(mean(values))
    assert pytest.approx(stats.variance) == pytest.approx(variance(values, ddof=1))
