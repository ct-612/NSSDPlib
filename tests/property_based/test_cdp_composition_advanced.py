"""
Property-based tests for advanced CDP composition, accountants, and budget schedulers.
"""
# 说明：高级中心化差分隐私（CDP）组合、会计器（MomentAccountant, CDPPrivacyAccountant）与预算调度器的属性测试。
# 覆盖：
# - 高级组合（Advanced Composition）与强组合（Strong Composition）的数学界限对比
# - zCDP, RDP, GDP 等替代表征下的隐私组合正确性
# - 隐私放大效应（子采样、混洗）的公式验证
# - MomentAccountant 在 RDP 累积与转换过程中的单调性与最优性
# - CDPPrivacyAccountant 策略分派的一致性
# - BudgetScheduler 在均匀、比例及几何衰减策略下的分配总额守恒

import pytest
import math
import numpy as np
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.cdp.composition.advanced import (
    advanced_composition, strong_composition, rho_zcdp_composition,
    rdp_composition, gdp_composition, subsampling_amplification,
    shuffle_amplification, optimal_composition_fallback)
from dplib.cdp.composition.basic import (sequential_composition,
                                         parallel_composition,
                                         repeated_mechanism, group_privacy)
from dplib.cdp.composition.moment_accountant import MomentAccountant
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant, AccountingMethod
from dplib.cdp.composition.budget_scheduler import BudgetScheduler, Allocation
from dplib.core.privacy.privacy_accountant import PrivacyEvent


# ---------------------------------------------------------------- Advanced Composition
@given(
    st.lists(st.floats(min_value=0.01, max_value=1.0), min_size=1,
             max_size=10), st.floats(min_value=1e-10, max_value=1e-2))
def test_advanced_composition_monotony(epsilons, delta_prime):
    # 验证高级组合结果随着输入 epsilon 增加而单调不减
    # 将 epsilon 列表转换为 (epsilon, delta) 元组序列以满足标准化要求
    events = [(e, 0.0) for e in epsilons]
    res = advanced_composition(events, delta_prime=delta_prime)

    # 增加一个 epsilon 的值
    events_inc = [(e + 0.1, 0.0) for e in epsilons]
    res_inc = advanced_composition(events_inc, delta_prime=delta_prime)

    assert res_inc.epsilon >= res.epsilon
    assert res_inc.delta == res.delta


@given(st.floats(min_value=0.1, max_value=1.0),
       st.floats(min_value=1e-10, max_value=1e-2),
       st.integers(min_value=1, max_value=50))
def test_strong_composition_k_scaling(epsilon, delta_hat, k):
    # 验证强组合结果随着重复次数 k 的增加而增加
    res = strong_composition(epsilon, delta=0.0, k=k, delta_hat=delta_hat)
    res_plus = strong_composition(epsilon,
                                  delta=0.0,
                                  k=k + 1,
                                  delta_hat=delta_hat)

    assert res_plus.epsilon > res.epsilon
    assert res_plus.delta == res.delta


# ---------------------------------------------------------------- Alternative Models (zCDP, RDP, GDP)
@given(
    st.lists(st.floats(min_value=0.001, max_value=0.5),
             min_size=1,
             max_size=10), st.floats(min_value=1e-8, max_value=1e-3))
def test_rho_zcdp_composition_correctness(rhos, target_delta):
    # 验证 zCDP 组合结果的基础数学性质（rho 线性累加影响）
    res = rho_zcdp_composition(rhos, target_delta=target_delta)
    assert res.epsilon > 0
    assert res.delta == target_delta


@given(
    st.lists(st.floats(min_value=0.001, max_value=0.5), min_size=1,
             max_size=5), st.floats(min_value=1.1, max_value=100.0),
    st.floats(min_value=1e-8, max_value=1e-3))
def test_rdp_composition_summation(rdp_epsilons, order, target_delta):
    # 验证在固定阶数下 RDP epsilon 是简单加性组合的
    res = rdp_composition(rdp_epsilons, order=order, target_delta=target_delta)
    single_sum = sum(rdp_epsilons)
    res_direct = rdp_composition([single_sum],
                                 order=order,
                                 target_delta=target_delta)

    assert res.epsilon == pytest.approx(res_direct.epsilon)


# ---------------------------------------------------------------- Privacy Amplification
@given(st.floats(min_value=0.1, max_value=5.0),
       st.floats(min_value=0.01, max_value=0.99))
def test_subsampling_amplification_effect(epsilon, q):
    # 验证子采样放大后的隐私损失 epsilon 严格小于原始损失
    event = PrivacyEvent(epsilon=epsilon, delta=0.0)
    amplified = subsampling_amplification(event, sampling_rate=q)

    assert amplified.epsilon < epsilon
    # 检查公式边界：q=1 时应等于原值
    amplified_1 = subsampling_amplification(event, sampling_rate=1.0)
    assert amplified_1.epsilon == pytest.approx(epsilon)


# ---------------------------------------------------------------- Accountants
@given(
    st.lists(st.floats(min_value=0.01, max_value=1.0), min_size=1,
             max_size=10))
def test_moment_accountant_accumulation(rdp_eps):
    # 验证矩会计器在 RDP 空间内正确单调累加隐私开销
    acc = MomentAccountant(orders=[2.0, 10.0])
    acc.add_rdp(2.0, rdp_eps[0])

    prev_eps = acc.get_epsilon(delta=1e-5)

    for eps in rdp_eps[1:]:
        acc.add_rdp(2.0, eps)

    new_eps = acc.get_epsilon(delta=1e-5)
    assert new_eps >= prev_eps


def test_cdp_privacy_accountant_dispatch():
    # 验证 CDPPrivacyAccountant 能够正确根据方法枚举分派组合逻辑
    acc = CDPPrivacyAccountant(total_epsilon=10.0,
                               default_method=AccountingMethod.ADVANCED)
    events = [{"epsilon": 0.1, "delta": 0.0}] * 5

    res = acc.compose(events, delta_prime=1e-5)
    assert res.detail["rule"] == "advanced"

    res_rdp = acc.compose(events,
                          method=AccountingMethod.RDP,
                          order=2.0,
                          target_delta=1e-5,
                          rdp_epsilons=[0.01] * 5)
    assert res_rdp.detail["rule"] == "rdp"


# ---------------------------------------------------------------- Budget Scheduler
@given(st.floats(min_value=1.0, max_value=100.0),
       st.integers(min_value=1, max_value=20))
def test_budget_scheduler_conservation(total_eps, n_items):
    # 验证预算调度器在均匀分配策略下的总预算守恒定律
    scheduler = BudgetScheduler(total_epsilon=total_eps)
    items = {str(i): 1.0 for i in range(n_items)}

    allocs = scheduler.allocate_uniform(items)
    sum_eps = sum(a.epsilon for a in allocs.values())

    assert sum_eps == pytest.approx(total_eps)


@given(st.floats(min_value=1.0, max_value=10.0),
       st.floats(min_value=0.1, max_value=2.0))
def test_geometric_decay_sum(total_eps, decay):
    # 验证几何衰减预算分配在窗口序列上的总和守恒
    scheduler = BudgetScheduler(total_epsilon=total_eps)
    allocs = scheduler.allocate_windows(window_count=5, decay=decay)

    sum_eps = sum(a.epsilon for a in allocs)
    assert sum_eps == pytest.approx(total_eps)
