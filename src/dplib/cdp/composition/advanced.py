"""
Advanced composition utilities for CDP.

Responsibilities:
    * advanced (Dwork-Roth) composition
    * ρ-zCDP composition with conversion back to (epsilon, delta)
"""
# 说明：中心化差分隐私（CDP）高级组合工具。
# 职责：
# - Advanced composition（Dwork-Roth 上界）：异质 ε_i, δ_i 的组合界
# - ρ-zCDP 合成：ρ 累加后按目标 δ 转换回 (ε, δ)-DP

from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

from dplib.core.privacy.base_mechanism import ValidationError
from dplib.core.privacy.composition import (
    CompositionResult,
    CompositionRule,
    normalize_privacy_events,
)


def _validate_delta(name: str, value: float) -> float:
    # δ 类参数校验：要求在 (0, 1) 开区间内
    if not 0 < value < 1:
        raise ValidationError(f"{name} must be in (0, 1)")
    return float(value)


def advanced_composition(events: Iterable, *, delta_prime: float) -> CompositionResult:
    """
    Advanced composition for heterogeneous epsilons/deltas.

    Uses the bound:
        epsilon = sqrt(2 log(1/delta_prime) * sum_i epsilon_i^2)
                  + sum_i epsilon_i * (exp(epsilon_i) - 1)
        delta = delta_prime + sum_i delta_i
    """
    # Dwork-Roth 组合上界：
    # - 首项是 √(2 log(1/δ') * Σ ε_i^2)
    # - 次项是 Σ ε_i (e^{ε_i} - 1)
    # - δ 合成为 δ' + Σ δ_i
    normalized = normalize_privacy_events(events)
    if not normalized:
        return CompositionResult.zero(detail={"rule": "advanced", "count": 0})
    delta_prime = _validate_delta("delta_prime", delta_prime)
    sum_sq = sum(event.epsilon ** 2 for event in normalized)
    tail = sum(event.epsilon * (math.exp(event.epsilon) - 1.0) for event in normalized)
    epsilon = math.sqrt(2.0 * math.log(1.0 / delta_prime) * sum_sq) + tail
    delta = delta_prime + sum(event.delta for event in normalized)
    detail = {
        "rule": "advanced",
        "delta_prime": delta_prime,
        "count": len(normalized),
        "sum_sq": sum_sq,
    }
    return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)


def rho_zcdp_composition(rhos: Sequence[float], *, target_delta: float) -> CompositionResult:
    """
    Compose ρ-zCDP mechanisms and convert to (epsilon, delta).

    Args:
        rhos: Sequence of rho values.
        target_delta: Desired δ when converting back to (ε, δ)-DP.
    """
    # ρ-zCDP 合成：ρ 可加（Σρ_i）；再用目标 δ 将 ρ 转回 (ε, δ)：
    # ε = ρ_total + 2 √(ρ_total * log(1/δ_target))
    if any(rho < 0 for rho in rhos):
        raise ValidationError("rho values must be non-negative")
    target_delta = _validate_delta("target_delta", target_delta)
    rho_total = sum(rhos)
    if rho_total == 0:
        return CompositionResult.zero(detail={"rule": "rho-zcdp", "rho": 0.0, "delta": target_delta})
    epsilon = rho_total + 2.0 * math.sqrt(rho_total * math.log(1.0 / target_delta))
    detail = {"rule": "rho-zcdp", "rho": rho_total, "delta": target_delta}
    return CompositionResult(epsilon=epsilon, delta=target_delta, detail=detail)


class AdvancedCompositionRule(CompositionRule):
    """CompositionRule wrapper around `advanced_composition`."""
    # 封装成 CompositionRule，便于与统一合成框架对接

    def __init__(self, *, delta_prime: float, name: Optional[str] = None):
        super().__init__(name or "AdvancedCompositionRule")
        self.delta_prime = _validate_delta("delta_prime", delta_prime)

    def apply(self, events, **kwargs):
        # 允许在调用时覆盖 delta_prime；其余逻辑复用函数实现
        delta_prime = kwargs.get("delta_prime", self.delta_prime)
        delta_prime = _validate_delta("delta_prime", delta_prime)
        return advanced_composition(events, delta_prime=delta_prime)


class RhoZCDPCompositionRule(CompositionRule):
    """CompositionRule for ρ-zCDP accounting."""
    # ρ-zCDP 规则：从事件 metadata 中提取 rho，合成后转回 (ε, δ)

    def __init__(self, *, target_delta: float, name: Optional[str] = None):
        super().__init__(name or "RhoZCDPCompositionRule")
        self.target_delta = _validate_delta("target_delta", target_delta)

    def apply(self, events, **kwargs):
        # 允许覆盖 target_delta；事件需在 metadata 中提供 "rho" 字段
        target_delta = kwargs.get("target_delta", self.target_delta)
        target_delta = _validate_delta("target_delta", target_delta)
        normalized = normalize_privacy_events(events)
        extracted = []
        for event in normalized:
            if "rho" not in event.metadata:
                raise ValidationError("rho metadata missing from one or more events")
            rho_value = float(event.metadata["rho"])
            if rho_value < 0:
                raise ValidationError("rho values must be non-negative")
            extracted.append(rho_value)
        return rho_zcdp_composition(extracted, target_delta=target_delta)
