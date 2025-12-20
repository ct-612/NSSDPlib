"""
Unit tests for the LDP composition helpers.
"""
# 说明：LDP 组合规则与 per-user 统计工具的单元测试。
# 覆盖：
# - epsilon 求和与负值校验
# - per-user 聚合与匿名用户 key
# - 顺序与并行入口的返回值语义

from __future__ import annotations

import pytest

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.composition.compose import (
    ANONYMOUS_USER_KEY,
    basic_composition,
    compose_epsilon_sum,
    compose_usages_sum,
    parallel_composition,
    parallel_compose_by_user,
    per_user_epsilon,
    sequential_composition,
    sequential_compose_by_user,
    summarize_budget,
)
from dplib.ldp.types import LocalPrivacyUsage


def test_compose_epsilon_sum_sums_values() -> None:
    # 验证 compose_epsilon_sum 能线性求和
    result = compose_epsilon_sum([0.2, 0.3])
    assert result == pytest.approx(0.5)


def test_compose_epsilon_sum_rejects_negative() -> None:
    # 验证 compose_epsilon_sum 对负值抛出 ParamValidationError
    with pytest.raises(ParamValidationError):
        compose_epsilon_sum([0.1, -0.2])


def test_compose_usages_sum_reuses_epsilon_sum() -> None:
    # 验证 compose_usages_sum 对 usage 序列求和
    usages = [LocalPrivacyUsage("u1", 0.1), LocalPrivacyUsage("u2", 0.2)]
    assert compose_usages_sum(usages) == pytest.approx(0.3)


def test_per_user_epsilon_groups_anonymous() -> None:
    # 验证 per_user_epsilon 按 user_id 聚合并处理匿名用户
    usages = [
        LocalPrivacyUsage("u1", 0.2),
        LocalPrivacyUsage("u1", 0.1),
        LocalPrivacyUsage(None, 0.3),
    ]
    result = per_user_epsilon(usages)
    assert result["u1"] == pytest.approx(0.3)
    assert result[ANONYMOUS_USER_KEY] == pytest.approx(0.3)


def test_summarize_budget_empty_input() -> None:
    # 验证 summarize_budget 在空输入时返回零值摘要
    summary = summarize_budget([])
    assert summary.total_epsilon == 0.0
    assert summary.max_user_epsilon == 0.0
    assert summary.n_events == 0
    assert summary.per_user_epsilon == {}


def test_basic_and_parallel_composition_summary() -> None:
    # 验证 basic_composition 与 parallel_composition 返回一致摘要结构
    usages = [LocalPrivacyUsage("u1", 0.2), LocalPrivacyUsage("u2", 0.5)]
    basic_summary = basic_composition(usages)
    parallel_summary = parallel_composition(usages)
    assert basic_summary.total_epsilon == pytest.approx(0.7)
    assert basic_summary.per_user_epsilon["u1"] == pytest.approx(0.2)
    assert parallel_summary.max_user_epsilon == pytest.approx(0.5)


def test_sequential_and_parallel_views_by_user() -> None:
    # 验证顺序与并行的 per-user 视角输出一致
    usages = [LocalPrivacyUsage("u1", 0.4), LocalPrivacyUsage("u2", 0.2)]
    sequential_view = sequential_compose_by_user(usages)
    parallel_view = parallel_compose_by_user(usages)
    assert sequential_view == parallel_view
    assert sequential_composition(usages) == pytest.approx(0.6)
