"""
Property-based tests for LDPPrivacyAccountant and Local-to-Central privacy bridge.
"""
# 说明：面向用户的 LDP 隐私会计器（LDPPrivacyAccountant）与本地到中心化隐私桥接逻辑的属性测试。
# 覆盖：
# - 每个用户的 Epsilon 预算上限强制执行逻辑
# - 全局 Epsilon 预算上限在多用户并发下的拦截校验
# - LDP 到 CDP 的隐私参数映射（Epsilon/Delta/Metadata）的一致性透传
# - 预算超限异常（BudgetExceededError）的准确抛出

import pytest
from hypothesis import given, strategies as st
from dplib.ldp.composition.privacy_accountant import LDPPrivacyAccountant, BudgetExceededError
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.ldp.types import LocalPrivacyUsage


# ----------------------------------------------------------------- Budget Enforcement
@given(
    st.floats(min_value=0.1, max_value=5.0),  # Limit
    st.lists(st.floats(min_value=0.01, max_value=1.5), min_size=2,
             max_size=10)  # Usages
)
def test_per_user_budget_enforcement(limit, usages):
    # 验证针对单个用户的 Epsilon 累计消耗是否受到严格的上限拦截
    accountant = LDPPrivacyAccountant(per_user_epsilon_limit=limit)
    user_id = "user_test"

    cumulative = 0.0
    over_limit_hit = False

    for eps in usages:
        usage = LocalPrivacyUsage(epsilon=eps, user_id=user_id)
        if cumulative + eps > limit:
            # 预期在超过阈值时抛出 BudgetExceededError
            with pytest.raises(BudgetExceededError):
                accountant.add_usage(usage)
            over_limit_hit = True
            break
        else:
            accountant.add_usage(usage)
            cumulative += eps
            assert accountant.get_user_spent(user_id) == pytest.approx(
                cumulative)

    if not over_limit_hit:
        # 如果随机生成的列表未触及上限，手动增加一条必然超限的记录进行最终确认
        with pytest.raises(BudgetExceededError):
            accountant.add_usage(
                LocalPrivacyUsage(epsilon=limit + 0.1, user_id=user_id))


@given(
    st.floats(min_value=1.0, max_value=10.0),  # Global limit
    st.lists(st.tuples(st.sampled_from(["u1", "u2", "u3"]),
                       st.floats(min_value=0.1, max_value=2.0)),
             min_size=5,
             max_size=20))
def test_global_budget_enforcement(global_limit, user_usage_pairs):
    # 验证全局预算上限逻辑：无论用户 ID 如何，所有用户的 Epsilon 贡献之和不得超过限制
    accountant = LDPPrivacyAccountant(global_epsilon_limit=global_limit)

    total_spent = 0.0
    for user_id, eps in user_usage_pairs:
        usage = LocalPrivacyUsage(epsilon=eps, user_id=user_id)
        if total_spent + eps > global_limit:
            with pytest.raises(BudgetExceededError):
                accountant.add_usage(usage)
            return  # 成功拦截并验证
        else:
            accountant.add_usage(usage)
            total_spent += eps
            assert accountant.get_total_spent() == pytest.approx(total_spent)


# ----------------------------------------------------------------- CDP Bridge
def test_ldp_to_cdp_bridge_consistency():
    # 验证本地隐私使用量（Usage）通过桥接逻辑透传到 CDP 会计器时，参数的一致性与完整性
    cdp_acc = CDPPrivacyAccountant()  # 内部持有一个 core accountant
    accountant = LDPPrivacyAccountant(cdp_accountant=cdp_acc)

    test_eps = 1.23
    test_meta = {"task": "survey", "round": 1}
    usage = LocalPrivacyUsage(epsilon=test_eps,
                              user_id="u1",
                              metadata=test_meta)

    accountant.add_usage(usage)

    # 检查关联的 CDP 会计器是否记录了对应的事件
    # 注意：CDPPrivacyAccountant 将事件保存在其内部 _accountant 的 events 列表中
    events = cdp_acc._accountant.events
    assert len(events) == 1
    event = events[0]

    # 验证核心参数透传
    assert event.epsilon == pytest.approx(test_eps)
    # LDP 到 CDP 映射默认 delta 为 0
    assert event.delta == 0.0
    # 验证元数据中自动注入了 LDP 上下文
    assert "ldp_context" in event.metadata
    assert event.metadata["ldp_context"]["user_id"] == "u1"
    # 验证原始业务元数据也被完整保留
    assert event.metadata["task"] == "survey"


def test_accountant_reset_behavior():
    # 验证重置（Reset）操作清空了累计消耗，但保留了注入的下游组件引用
    cdp_acc = CDPPrivacyAccountant()
    accountant = LDPPrivacyAccountant(per_user_epsilon_limit=1.0,
                                      cdp_accountant=cdp_acc)

    accountant.add_usage(LocalPrivacyUsage(epsilon=0.5, user_id="u1"))
    assert accountant.get_total_spent() == 0.5

    accountant.reset()
    assert accountant.get_total_spent() == 0.0
    assert accountant.get_user_spent("u1") == 0.0
    # 核心测试点：重置后注入的 cdp_accountant 引用依然有效
    assert accountant._cdp_accountant is cdp_acc
