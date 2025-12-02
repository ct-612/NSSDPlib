"""
Unit tests for the CDP privacy accountant strategies.
"""
# 说明：针对 CDPPrivacyAccountant 及其多种组合策略调度行为的单元测试。
# 覆盖：
# - 验证 BASIC 策略走顺序组合路径并正确累加 ε 与 δ
# - 验证 ADVANCED 策略支持覆盖 delta_prime 并在结果 detail 中标记规则名称
# - 验证 STRONG 策略对均匀 (ε, δ) 事件与非均匀事件的处理与异常行为
# - 验证 ZCDP/RDP/GDP 策略从事件元数据读取 rho/rdp_epsilon/mu 并组合
# - 验证 OPTIMAL 策略在同质与异质事件间切换 strong 与 advanced 路径
# - 验证 add_composed_event 会将组合结果写入底层记账器并更新 spent 视图

import math

import pytest

from dplib.cdp.composition.advanced import strong_composition
from dplib.cdp.composition.privacy_accountant import AccountingMethod, CDPPrivacyAccountant
from dplib.core.utils.param_validation import ParamValidationError


def test_basic_composition_uses_sequential_sum() -> None:
    # 验证 BASIC 策略默认使用顺序组合对 ε 和 δ 进行线性求和
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.BASIC)
    events = [{"epsilon": 0.2, "delta": 1e-6}, {"epsilon": 0.3, "delta": 2e-6}]
    result = acct.compose(events)
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(3e-6)


def test_advanced_composition_with_delta_prime_override() -> None:
    # 验证 ADVANCED 策略在传入 delta_prime 时会覆盖默认值并正确反映在结果中
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.ADVANCED)
    events = [{"epsilon": 0.1, "delta": 0.0}] * 2
    result = acct.compose(events, delta_prime=1e-5)
    assert result.delta == pytest.approx(1e-5)
    assert result.detail["rule"] == "advanced"


def test_strong_composition_requires_uniform_events() -> None:
    # 验证 STRONG 策略对均匀事件使用 strong_composition 且对非均匀事件抛出异常
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.STRONG)
    uniform = [{"epsilon": 0.2, "delta": 1e-6}] * 3
    result = acct.compose(uniform, delta_hat=1e-5)
    expected = strong_composition(0.2, 1e-6, k=3, delta_hat=1e-5)
    assert result.epsilon == pytest.approx(expected.epsilon)
    assert result.delta == pytest.approx(expected.delta)
    mixed = [{"epsilon": 0.2, "delta": 1e-6}, {"epsilon": 0.3, "delta": 1e-6}]
    with pytest.raises(ParamValidationError):
        acct.compose(mixed, delta_hat=1e-5)


def test_zcdp_composition_reads_metadata_rho() -> None:
    # 验证 ZCDP 策略从 metadata 中读取 rho 并基于 rho 总和进行组合
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.ZCDP)
    events = [
        {"epsilon": 0.0, "delta": 0.0, "metadata": {"rho": 0.2}},
        {"epsilon": 0.0, "delta": 0.0, "metadata": {"rho": 0.3}},
    ]
    result = acct.compose(events, target_delta=1e-6)
    rho_total = 0.5
    expected_eps = rho_total + 2 * math.sqrt(rho_total * math.log(1e6))
    assert result.epsilon == pytest.approx(expected_eps)
    with pytest.raises(ParamValidationError):
        acct.compose([{"epsilon": 0.0, "delta": 0.0, "metadata": {}}], target_delta=1e-6)


def test_rdp_composition_and_gdp_composition() -> None:
    # 验证 RDP 与 GDP 策略分别读取 rdp_epsilon 与 mu 元数据并触发对应规则
    acct_rdp = CDPPrivacyAccountant(default_method=AccountingMethod.RDP)
    events = [
        {"epsilon": 0.0, "delta": 0.0, "metadata": {"rdp_epsilon": 0.1}},
        {"epsilon": 0.0, "delta": 0.0, "metadata": {"rdp_epsilon": 0.2}},
    ]
    result = acct_rdp.compose(events, order=4.0, target_delta=1e-6)
    assert result.detail["rule"] == "rdp"

    acct_gdp = CDPPrivacyAccountant(default_method=AccountingMethod.GDP)
    gdp_events = [{"epsilon": 0.0, "delta": 0.0, "metadata": {"mu": 0.5}} for _ in range(2)]
    result_gdp = acct_gdp.compose(gdp_events, target_delta=1e-5)
    assert result_gdp.detail["rule"] == "gdp"


def test_optimal_fallback_delegates_to_advanced_or_strong() -> None:
    # 验证 OPTIMAL 策略对异质事件走 advanced 路径对同质事件走 strong 路径
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.OPTIMAL)
    heterogeneous = [{"epsilon": 0.1, "delta": 0.0}, {"epsilon": 0.2, "delta": 0.0}]
    result_adv = acct.compose(heterogeneous, delta_hat=1e-5)
    assert (
        result_adv.detail["rule"] == "optimal_fallback"
        and result_adv.detail["strategy"] == "advanced"
        )
    uniform = [{"epsilon": 0.2, "delta": 1e-6}] * 2
    result_strong = acct.compose(uniform, delta_hat=1e-5)
    assert (
        result_strong.detail["rule"] == "optimal_fallback"
        and result_strong.detail["strategy"] == "strong"
        )   


def test_add_composed_event_updates_spent() -> None:
    # 验证 add_composed_event 在组合后会更新底层记账器的 spent 预算
    acct = CDPPrivacyAccountant(default_method=AccountingMethod.BASIC, total_epsilon=1.0, total_delta=1e-3)
    acct.add_composed_event([{"epsilon": 0.3, "delta": 1e-4}], description="test")
    spent_eps, spent_delta = acct.spent
    assert spent_eps == pytest.approx(0.3)
    assert spent_delta == pytest.approx(1e-4)
