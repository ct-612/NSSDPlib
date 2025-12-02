"""
Unit tests for the RDP-based moment accountant.
"""
# 说明：针对基于 RDP 的 MomentAccountant 进行多步组合与最优 ε 选择行为的单元测试。
# 覆盖：
# - 验证在多个阶数上累积 RDP 并通过最小化 ε 获得最优 (ε, δ)-DP 界
# - 验证 add_rdp 对未跟踪阶数与负 ε 输入的异常处理
# - 验证 reset 能清空内部累计状态以及非法 δ 时的参数校验

import math

import pytest

from dplib.cdp.composition.moment_accountant import MomentAccountant
from dplib.core.privacy.privacy_model import rdp_to_cdp
from dplib.core.utils.param_validation import ParamValidationError


def test_accumulates_rdp_and_minimises_epsilon() -> None:
    # 验证在多个阶数上累积 RDP 后 get_epsilon 能选择给出最小 ε 的阶数
    orders = (2.0, 4.0)
    acc = MomentAccountant(orders=orders)
    # step 1
    acc.add_step({2.0: 0.5, 4.0: 0.2})
    # step 2
    acc.add_step({2.0: 0.3, 4.0: 0.4})
    # cumulative RDP: {2:0.8, 4:0.6}
    delta = 1e-5
    eps_candidates = [
        rdp_to_cdp(2.0, 0.8, delta),
        rdp_to_cdp(4.0, 0.6, delta),
    ]
    expected = min(eps_candidates)
    epsilon = acc.get_epsilon(delta)
    assert epsilon == pytest.approx(expected)
    spent_eps, spent_delta = acc.spent(delta)
    assert spent_eps == pytest.approx(expected)
    assert spent_delta == pytest.approx(delta)


def test_add_rdp_requires_tracked_order_and_non_negative() -> None:
    # 验证 add_rdp 对未跟踪阶数与负 ε 输入抛出 ParamValidationError
    acc = MomentAccountant(orders=(2.0,))
    with pytest.raises(ParamValidationError):
        acc.add_rdp(3.0, 0.1)
    with pytest.raises(ParamValidationError):
        acc.add_rdp(2.0, -0.1)


def test_reset_clears_state() -> None:
    # 验证 reset 调用后所有阶数上的累计 RDP 被清零
    acc = MomentAccountant(orders=(2.0,))
    acc.add_step({2.0: 0.3})
    assert acc.get_rdp()[2.0] == pytest.approx(0.3)
    acc.reset()
    assert acc.get_rdp()[2.0] == pytest.approx(0.0)


def test_invalid_delta_raises() -> None:
    # 验证 get_epsilon 对不在 (0,1) 区间的 δ 触发参数校验异常
    acc = MomentAccountant()
    acc.add_step({2.0: 0.1})
    with pytest.raises(ParamValidationError):
        acc.get_epsilon(0.0)
    with pytest.raises(ParamValidationError):
        acc.get_epsilon(1.5)
