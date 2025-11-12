"""
Unit tests for advanced CDP composition utilities.

Covers:
    * advanced_composition: Dwork–Roth bound for heterogeneous (ε_i, δ_i)
    * AdvancedCompositionRule: rule wrapper honoring default `delta_prime`
    * rho_zcdp_composition: sums ρ and converts back to (ε, δ) at target δ
    * RhoZCDPCompositionRule: extracts `rho` from event metadata and composes
"""
# 说明：高级 CDP 组合工具单元测试。
# 覆盖：
# - 异质 (ε_i, δ_i) 的 Dwork–Roth 组合上界校验
# - 确认规则封装能使用并生效默认的 delta_prime
# - 证明 ρ-zCDP 在 ρ 上可加，并能以目标 δ 转回 (ε, δ)-DP
# - 校验从事件 metadata 读取 rho 并完成合成
import math

import pytest

from dplib.cdp.composition.advanced import (
    AdvancedCompositionRule,
    RhoZCDPCompositionRule,
    advanced_composition,
    rho_zcdp_composition,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent


def test_advanced_composition_matches_formula() -> None:
    # Advanced 组合与公式一致性：按 Dwork-Roth 上界计算期望值并比对
    # 公式：[expected = √(2 log(1/δ') * Σ ε_i^2) + Σ ε_i (e^{ε_i} - 1)]，[δ = δ' + Σ δ_i]
    events = [PrivacyEvent(0.2, 1e-6), PrivacyEvent(0.3, 2e-6)]
    result = advanced_composition(events, delta_prime=1e-5)
    expected = math.sqrt(2 * math.log(1e5) * (0.2**2 + 0.3**2)) + sum(
        eps * (math.exp(eps) - 1) for eps in (0.2, 0.3)
    )
    assert result.epsilon == pytest.approx(expected)
    assert result.delta == pytest.approx(1e-5 + 3e-6)


def test_advanced_composition_rule_uses_default_delta_prime() -> None:
    # 规则封装：使用构造时提供的默认 delta_prime，且输出 δ>0
    rule = AdvancedCompositionRule(delta_prime=1e-5)
    events = [PrivacyEvent(0.1, 0.0)] * 5
    result = rule.compose(events)
    assert result.detail["rule"] == "advanced"
    assert result.delta > 0


def test_rho_zcdp_composition_converts_rho_sum() -> None:
    # ρ-zCDP：ρ 可加后按目标 δ 转回 (ε, δ)，验证 ε 公式
    result = rho_zcdp_composition([0.5, 0.3], target_delta=1e-6)
    rho_total = 0.8
    expected = rho_total + 2 * math.sqrt(rho_total * math.log(1e6))
    assert result.epsilon == pytest.approx(expected)
    assert result.delta == pytest.approx(1e-6)


def test_rho_zcdp_rule_reads_metadata() -> None:
    # 规则从事件 metadata 中读取 "rho" 并累计，验证明细字段
    rule = RhoZCDPCompositionRule(target_delta=1e-6)
    events = [
        PrivacyEvent(0.0, 0.0, metadata={"rho": 0.2}),
        PrivacyEvent(0.0, 0.0, metadata={"rho": 0.3}),
    ]
    result = rule.compose(events)
    assert result.detail["rho"] == pytest.approx(0.5)
