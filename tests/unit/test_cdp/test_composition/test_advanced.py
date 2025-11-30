"""
Unit tests for advanced CDP composition helpers.
"""
# 说明：中心差分隐私高级组合与隐私放大工具函数的单元测试。
# 覆盖：
# - 验证 advanced_composition 与 AdvancedCompositionRule 在 δ' 默认值与覆盖参数下的行为
# - 验证 strong_composition 与 zCDP/RDP/GDP 组合转换到 (ε, δ)-DP 的正确性
# - 验证子采样 subsampling_amplification 与混洗 shuffle_amplification 的隐私放大效果
# - 验证 optimal_composition_fallback 在空输入、同质事件与异质事件路径选择上的逻辑
# - 验证 RhoZCDPCompositionRule 对元数据中 rho 的读取及缺失时抛出 ParamValidationError 的行为

import math

import pytest

from dplib.cdp.composition.advanced import (
    AdvancedCompositionRule,
    RhoZCDPCompositionRule,
    advanced_composition,
    gdp_composition,
    optimal_composition_fallback,
    rdp_composition,
    rho_zcdp_composition,
    shuffle_amplification,
    strong_composition,
    subsampling_amplification,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent
from dplib.core.privacy.privacy_model import gdp_to_cdp, rdp_to_cdp, zcdp_to_cdp
from dplib.core.utils.param_validation import ParamValidationError


def test_advanced_composition_matches_formula() -> None:
    # 验证 advanced_composition 的实现与参考公式计算结果保持一致
    events = [PrivacyEvent(0.2, 0.0), PrivacyEvent(0.3, 0.0)]
    result = advanced_composition(events, delta_prime=1e-5)
    expected_eps = math.sqrt(2 * math.log(1e5) * (0.2**2 + 0.3**2)) + sum(
        eps * (math.exp(eps) - 1) for eps in (0.2, 0.3)
    )
    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(1e-5)
    assert result.detail["eps_l2_sq"] == pytest.approx(0.13)


def test_advanced_composition_rule_uses_default_and_override() -> None:
    # 验证 AdvancedCompositionRule 使用默认 delta_prime 与调用时覆盖 delta_prime 的差异
    rule = AdvancedCompositionRule(delta_prime=1e-4)
    events = [PrivacyEvent(0.1, 0.0)] * 3
    default_result = rule.compose(events)
    override_result = rule.compose(events, delta_prime=1e-6)
    assert default_result.delta == pytest.approx(1e-4)
    assert override_result.delta == pytest.approx(1e-6)
    assert default_result.detail["rule"] == "advanced"


def test_strong_composition_formulation() -> None:
    # 验证 strong_composition 对 k 次相同 (ε, δ)-DP 机制的公式实现
    result = strong_composition(0.5, 1e-6, k=4, delta_hat=1e-5)
    expected_eps = math.sqrt(2 * 4 * math.log(1e5)) * 0.5 + 4 * 0.5 * (math.exp(0.5) - 1.0)
    expected_delta = 4 * 1e-6 + 1e-5
    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(expected_delta)
    assert result.detail["k"] == 4


def test_rho_zcdp_composition_converts_to_cdp() -> None:
    # 验证 rho_zcdp_composition 汇总 rho 并通过 zcdp_to_cdp 转换为 (ε, δ)-DP
    result = rho_zcdp_composition([0.5, 0.3], target_delta=1e-6)
    expected_eps = zcdp_to_cdp(0.8, 1e-6)
    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(1e-6)
    assert result.detail["rho"] == pytest.approx(0.8)


def test_rho_zcdp_rule_reads_metadata_and_errors_on_missing_rho() -> None:
    # 验证 RhoZCDPCompositionRule 从事件元数据读取 rho 并在缺失时抛出 ParamValidationError
    rule = RhoZCDPCompositionRule(target_delta=1e-6, rho_key="rho")
    events = [
        PrivacyEvent(0.0, 0.0, metadata={"rho": 0.2}),
        PrivacyEvent(0.0, 0.0, metadata={"rho": 0.3}),
    ]
    result = rule.compose(events)
    assert result.epsilon == pytest.approx(zcdp_to_cdp(0.5, 1e-6))
    assert result.detail["rule"] == "rho_zcdp"

    with pytest.raises(ParamValidationError):
        rule.compose(
            [PrivacyEvent(0.0, 0.0, metadata={})],
            rho_getter=lambda event: event.metadata.get("missing"),
        )


def test_rdp_composition_converts_at_order() -> None:
    # 验证 rdp_composition 在指定阶数与 target_delta 下求和并转换为 (ε, δ)-DP
    result = rdp_composition([0.1, 0.2], order=4.0, target_delta=1e-6)
    expected_eps = rdp_to_cdp(4.0, 0.30000000000000004, 1e-6)
    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(1e-6)
    assert result.detail["order"] == pytest.approx(4.0)


def test_gdp_composition_sums_in_l2() -> None:
    # 验证 gdp_composition 按 L2 范数组合 μ 并通过 gdp_to_cdp 转换为等效 (ε, δ)-DP
    result = gdp_composition([0.5, 0.5, 0.5], target_delta=1e-5)
    mu_total = math.sqrt(0.5**2 + 0.5**2 + 0.5**2)
    expected_eps = gdp_to_cdp(mu_total, 1e-5)
    assert result.epsilon == pytest.approx(expected_eps)
    assert result.delta == pytest.approx(1e-5)
    assert result.detail["mu"] == pytest.approx(mu_total)


def test_subsampling_amplification_scales_privacy() -> None:
    # 验证 subsampling_amplification 按采样率缩放 δ 并使用放大公式更新 ε
    event = {"epsilon": 1.0, "delta": 1e-3}
    amplified = subsampling_amplification(event, sampling_rate=0.2)
    expected_eps = math.log(1 + 0.2 * (math.exp(1.0) - 1))
    expected_delta = 0.2 * 1e-3
    assert amplified.epsilon == pytest.approx(expected_eps)
    assert amplified.delta == pytest.approx(expected_delta)


def test_shuffle_amplification_scales_by_sqrt_n() -> None:
    # 验证 shuffle_amplification 使用 1/√n 因子对 ε 与 δ 进行缩放
    event = {"epsilon": 0.8, "delta": 2e-4}
    amplified = shuffle_amplification(event, population=25)
    scale = 1 / math.sqrt(25)
    assert amplified.epsilon == pytest.approx(0.8 * scale)
    assert amplified.delta == pytest.approx(2e-4 * scale)


def test_optimal_composition_fallback_empty_and_strong_path() -> None:
    # 验证 optimal_composition_fallback 在空事件与同质事件时分别返回零或使用强组合路径
    empty = optimal_composition_fallback([], delta_hat=1e-6)
    assert empty.epsilon == 0.0 and empty.delta == 0.0
    assert empty.detail["note"] == "no events"

    uniform_events = [PrivacyEvent(0.2, 1e-6) for _ in range(3)]
    result = optimal_composition_fallback(uniform_events, delta_hat=1e-5)
    expected = strong_composition(0.2, 1e-6, k=3, delta_hat=1e-5)
    assert result.epsilon == pytest.approx(expected.epsilon)
    assert result.delta == pytest.approx(expected.delta)
    assert result.detail["strategy"] == "strong"
    assert result.detail["rule"] == "optimal_fallback"


def test_optimal_composition_fallback_heterogeneous_uses_advanced() -> None:
    # 验证 optimal_composition_fallback 在异质事件时降级为 advanced_composition 路径
    events = [PrivacyEvent(0.1, 0.0), PrivacyEvent(0.2, 0.0)]
    result = optimal_composition_fallback(events, delta_hat=1e-5)
    assert result.detail["strategy"] == "advanced"
    assert result.detail["rule"] == "optimal_fallback"
