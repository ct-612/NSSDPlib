"""
Property-based tests for the core privacy accounting and composition primitives.
"""
# 说明：核心隐私记账（PrivacyAccountant）与组合原语（CompositionRule）的属性测试。
# 覆盖：
# - PrivacyBudget 的算术运算一致性与零预算不变性
# - PrivacyAccountant 在连续事件历史下的花费累加与预算强制约束
# - 顺序组合、并行组合以及高阶重复组合规则的数学正确性
# - 下溢保护与预算超限拦截逻辑

import pytest
from hypothesis import given, strategies as st
from dplib.core.privacy.privacy_accountant import (
    PrivacyBudget,
    PrivacyAccountant,
    PrivacyEvent,
    BudgetExceededError,
)
from dplib.core.privacy.composition import (
    SequentialCompositionRule,
    ParallelCompositionRule,
    HigherOrderCompositionRule,
    CompositionResult,
)


# ------------------------------------------------------------- PrivacyBudget Tests
@given(st.floats(min_value=0, max_value=100),
       st.floats(min_value=0, max_value=1))
def test_budget_identity(eps, delta):
    # 验证任何隐私预算对象的 epsilon 和 delta 分量加上零值预算后保持数值不变
    budget = PrivacyBudget(eps, delta)
    zero = PrivacyBudget(0, 0)
    assert (budget + zero).epsilon == budget.epsilon
    assert (budget + zero).delta == budget.delta


@given(st.floats(min_value=0, max_value=50),
       st.floats(min_value=0, max_value=0.5),
       st.floats(min_value=0, max_value=50),
       st.floats(min_value=0, max_value=0.5))
def test_budget_commutativity(e1, d1, e2, d2):
    # 验证隐私预算对象的加法运算逻辑满足交换律，屏蔽不同加法顺序对结果的影响
    b1 = PrivacyBudget(e1, d1)
    b2 = PrivacyBudget(e2, d2)
    sum1 = b1 + b2
    sum2 = b2 + b1
    # 利用 approx 处理极小数值在浮点数累加时产生的微弱精度差异
    assert sum1.epsilon == pytest.approx(sum2.epsilon)
    assert sum1.delta == pytest.approx(sum2.delta)


@given(st.floats(min_value=0, max_value=100),
       st.floats(min_value=0, max_value=100))
def test_budget_subtraction_floor(v1, v2):
    # 验证隐私预算减法具备下溢截断特性，即差值最小被限制为零而不出现负数分量
    b1 = PrivacyBudget(v1, 0)
    b2 = PrivacyBudget(v2, 0)
    res = b1 - b2
    assert res.epsilon >= 0
    # 当消耗预算超过剩余量时结果应直接归零
    if v1 < v2:
        assert res.epsilon == 0


# --------------------------------------------------------- PrivacyAccountant Tests
@given(
    st.lists(st.tuples(st.floats(min_value=0, max_value=1),
                       st.floats(min_value=0, max_value=0.01)),
             min_size=1,
             max_size=10))
def test_accountant_accumulation(events_data):
    # 验证隐私记账器能根据注入的历史隐私事件列表正确累加总的花费预算 (ε, δ)
    accountant = PrivacyAccountant()
    total_eps = 0.0
    total_delta = 0.0
    for eps, delta in events_data:
        accountant.add_event(eps, delta)
        total_eps += eps
        total_delta += delta

    assert accountant.spent.epsilon == pytest.approx(total_eps)
    assert accountant.spent.delta == pytest.approx(total_delta)
    assert len(accountant.events) == len(events_data)


def test_accountant_budget_enforcement():
    # 验证隐私记账器在配置合规性边界后能有效拦截并拒绝超出额度的隐私分配请求
    accountant = PrivacyAccountant(total_epsilon=1.0, total_delta=0.1)
    accountant.add_event(0.5, 0.05)

    # 在可用预算范围内的分配应当成功
    assert accountant.can_allocate(0.5, 0.05)
    accountant.add_event(0.5, 0.05)

    # 当记账器累计花费触及阈值后，新的分配尝试应抛出 BudgetExceededError
    assert not accountant.can_allocate(0.1, 0.0)
    with pytest.raises(BudgetExceededError):
        accountant.add_event(0.1, 0.0)


# --------------------------------------------------------- Composition Rules Tests
@given(
    st.lists(st.tuples(st.floats(min_value=0, max_value=1),
                       st.floats(min_value=0, max_value=0.01)),
             min_size=1,
             max_size=10))
def test_sequential_composition_property(events_data):
    # 验证顺序组合规则的行为符合基础差分隐私定义的线性加和特性
    rule = SequentialCompositionRule()
    result = rule.compose(events_data)

    expected_eps = sum(e[0] for e in events_data)
    expected_delta = sum(e[1] for e in events_data)

    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(expected_delta)


@given(
    st.lists(st.tuples(st.floats(min_value=0, max_value=1),
                       st.floats(min_value=0, max_value=0.01)),
             min_size=1,
             max_size=10))
def test_parallel_composition_property(events_data):
    # 验证并行组合规则在处理不相交数据分组时遵循子预算最大值的数学边界
    rule = ParallelCompositionRule()
    # 默认策略下每个事件归属于不同的并行组
    result = rule.compose(events_data)

    expected_eps = max(e[0] for e in events_data)
    expected_delta = max(e[1] for e in events_data)

    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(expected_delta)


# ---------------------------------------------------------------- HigherOrder Composition
@given(st.integers(min_value=1, max_value=10),
       st.floats(min_value=0.1, max_value=1.0))
def test_higher_order_composition_scaling(order, epsilon):
    # 验证高阶组合规则对于重复执行同一隐私事件后的等效隐私代价缩放逻辑
    # 基础规则默认为 Sequential，对于单事件的组合结果即为 epsilon * order
    rule = HigherOrderCompositionRule(order=order)
    event = PrivacyEvent(epsilon, 0.0)

    result = rule.compose([event])

    assert result.epsilon == pytest.approx(epsilon * order)
