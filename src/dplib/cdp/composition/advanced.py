"""
Advanced composition utilities for central differential privacy.
Provides composition rules, model conversions, and amplification helpers.

Responsibilities
  - Provide composition rules and helper functions for CDP events.
  - Support multiple privacy models and conversions to (epsilon, delta)-DP.
  - Offer heuristic amplification utilities for sampling and shuffling.

Usage Context
  - Use in privacy accounting or analysis pipelines.
  - Intended for central DP composition across multiple events.

Limitations
  - Amplification helpers use simplified heuristics.
  - Optimal composition is a fallback, not a full optimizer.
"""
# 说明：实现中心差分隐私场景下多种高级组合与隐私放大工具函数。
# 职责：
# - 提供 Dwork–Roth 异质纯 DP 事件高级组合与 DRV10 强组合封装
# - 支持 zCDP/RDP/GDP 等替代表征下的组合并转换回 (ε, δ)-DP
# - 实现子采样与混洗场景下的隐私放大近似公式与最优组合降级策略

from __future__ import annotations

import math
from typing import Callable, Iterable, Optional, Sequence

from dplib.core.privacy.composition import (
    CompositionResult,
    CompositionRule,
    PrivacyEventLike,
    normalize_privacy_events,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent
from dplib.core.privacy.privacy_model import (
    gdp_to_cdp,
    rdp_to_cdp,
    zcdp_to_cdp,
)
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type


def advanced_composition(
    events: Iterable[PrivacyEventLike],
    *,
    delta_prime: float = 1e-6,
) -> CompositionResult:
    # 针对一组异质纯 DP 事件应用 Dwork–Roth 高级组合定理并返回等效 (ε, δ)
    """
    Advanced composition for heterogeneous pure-DP events (δ_i = 0).

    ε = sqrt(2 log(1/δ') * Σ ε_i^2) + Σ ε_i (exp(ε_i) - 1)
    δ = δ' + Σ δ_i
    """
    ensure(delta_prime > 0, "delta_prime must be positive")
    normalized = normalize_privacy_events(events)
    epsilons = [event.epsilon for event in normalized]
    deltas = [event.delta for event in normalized]
    eps_sq_sum = sum(eps * eps for eps in epsilons)
    eps_term = math.sqrt(2.0 * math.log(1.0 / delta_prime) * eps_sq_sum) if eps_sq_sum > 0 else 0.0
    linear_term = sum(eps * (math.exp(eps) - 1.0) for eps in epsilons)
    epsilon = eps_term + linear_term
    delta = float(delta_prime) + sum(deltas)
    detail = {
        "rule": "advanced",
        "delta_prime": float(delta_prime),
        "count": len(normalized),
        "eps_l2_sq": eps_sq_sum,
    }
    return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)


class AdvancedCompositionRule(CompositionRule):
    # 将 advanced_composition 封装为 CompositionRule 以便在记账器中复用
    """
    Rule wrapper around `advanced_composition` with a default delta_prime.

    - Configuration
      - delta_prime: Default delta_prime used in advanced composition.
      - name: Optional rule name override.

    - Behavior
      - Applies advanced composition to provided events.
      - Records the rule name in the result detail.

    - Usage Notes
      - Override delta_prime per call via `apply` kwargs.
    """

    def __init__(self, delta_prime: float = 1e-6, *, name: Optional[str] = None):
        # 在规则实例上固定默认 δ' 并允许调用时覆盖
        ensure(delta_prime > 0, "delta_prime must be positive")
        super().__init__(name or "advanced")
        self.delta_prime = float(delta_prime)

    def apply(self, events: Sequence[PrivacyEvent], **kwargs) -> CompositionResult:
        # 将事件序列与当前规则的 δ' 传递给 advanced_composition 并在 detail 中记录规则名
        delta_prime = float(kwargs.get("delta_prime", self.delta_prime))
        result = advanced_composition(events, delta_prime=delta_prime)
        detail = dict(result.detail)
        detail["rule"] = self.name
        return CompositionResult(epsilon=result.epsilon, delta=result.delta, detail=detail)


def strong_composition(
    epsilon: float,
    delta: float,
    *,
    k: int,
    delta_hat: float,
) -> CompositionResult:
    # 针对 k 次相同 (ε, δ)-DP 机制应用 DRV10 强组合界给出整体 (ε', δ')
    """
    DRV10 strong composition for k identical (ε, δ)-DP mechanisms.

    ε' = sqrt(2k log(1/δ̂ )) * ε + k * ε * (exp(ε) - 1)
    δ' = k * δ + δ̂
    """
    ensure_type(k, (int,), label="k")
    ensure(k > 0, "k must be positive")
    ensure(delta_hat > 0, "delta_hat must be positive")
    eps_prime = math.sqrt(2.0 * k * math.log(1.0 / delta_hat)) * float(epsilon)
    eps_prime += k * float(epsilon) * (math.exp(float(epsilon)) - 1.0)
    delta_prime = k * float(delta) + float(delta_hat)
    detail = {"rule": "strong", "k": k, "delta_hat": float(delta_hat)}
    return CompositionResult(epsilon=eps_prime, delta=delta_prime, detail=detail)


def rho_zcdp_composition(rhos: Iterable[float], *, target_delta: float) -> CompositionResult:
    # 对一组 ρ-zCDP 保证进行求和并在给定 target_delta 下转换回 (ε, δ)-DP
    """Sum ρ-zCDP guarantees and convert back to (ε, δ)-DP at `target_delta`."""
    ensure(target_delta > 0 and target_delta < 1, "target_delta must be in (0,1)")
    rho_total = sum(float(rho) for rho in rhos)
    ensure(rho_total >= 0, "rho must be non-negative")
    epsilon = zcdp_to_cdp(rho_total, target_delta)
    detail = {"rule": "rho_zcdp", "rho": rho_total, "target_delta": float(target_delta)}
    return CompositionResult(epsilon=epsilon, delta=target_delta, detail=detail)


class RhoZCDPCompositionRule(CompositionRule):
    # 从事件元数据中提取 rho 并在 zCDP 模型下组合然后还原为 (ε, δ)-DP
    """
    Extract rho from event metadata and compose under zCDP.

    - Configuration
      - target_delta: Delta used when converting zCDP to (epsilon, delta)-DP.
      - rho_key: Metadata key used to fetch rho values.
      - name: Optional rule name override.

    - Behavior
      - Collects rho values from events and composes in zCDP space.
      - Converts the result back to (epsilon, delta)-DP.

    - Usage Notes
      - Provide a custom rho_getter via `apply` kwargs when needed.
    """

    def __init__(
        self,
        *,
        target_delta: float = 1e-6,
        rho_key: str = "rho",
        name: Optional[str] = None,
    ):
        # 固定 zCDP 组合的 target_delta 与元数据中 rho 对应的键名
        ensure(target_delta > 0 and target_delta < 1, "target_delta must be in (0,1)")
        super().__init__(name or "rho_zcdp")
        self.target_delta = float(target_delta)
        self.rho_key = rho_key

    def apply(self, events: Sequence[PrivacyEvent], **kwargs) -> CompositionResult:
        # 通过可配置的 getter 从事件中抽取 rho 并进行数值校验与组合
        getter: Callable[[PrivacyEvent], float] = kwargs.get(
            "rho_getter", lambda event: event.metadata.get(self.rho_key, 0.0)
        )
        rhos = []
        for event in events:
            rho = getter(event)
            if rho is None:
                raise ParamValidationError("missing rho in event metadata")
            try:
                rho_value = float(rho)
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ParamValidationError("rho must be numeric") from exc
            ensure(rho_value >= 0, "rho must be non-negative")
            rhos.append(rho_value)
        result = rho_zcdp_composition(rhos, target_delta=self.target_delta)
        detail = dict(result.detail)
        detail["rule"] = self.name
        return CompositionResult(epsilon=result.epsilon, delta=result.delta, detail=detail)


def rdp_composition(
    rdp_epsilons: Iterable[float],
    *,
    order: float,
    target_delta: float,
) -> CompositionResult:
    # 在固定 Rényi 阶 α 下对一组 RDP ε 进行求和并转换为等效 (ε, δ)
    """
    Compose (α, ε_i)-RDP guarantees at fixed order α and convert to (ε, δ).
    """
    ensure(order > 1, "rdp order must be > 1")
    ensure(target_delta > 0 and target_delta < 1, "target_delta must be in (0,1)")
    epsilon_rdp = sum(float(eps) for eps in rdp_epsilons)
    ensure(epsilon_rdp >= 0, "rdp epsilon must be non-negative")
    epsilon = rdp_to_cdp(order, epsilon_rdp, target_delta)
    detail = {"rule": "rdp", "order": float(order), "target_delta": float(target_delta), "rdp_epsilon": epsilon_rdp}
    return CompositionResult(epsilon=epsilon, delta=target_delta, detail=detail)


def gdp_composition(mus: Iterable[float], *, target_delta: float) -> CompositionResult:
    # 对一组 μ-GDP 保证以 L2 范数组合并转换为等效 (ε, δ)-DP
    """Compose μ-GDP guarantees (L2 addition) and convert to (ε, δ)-DP."""
    ensure(target_delta > 0 and target_delta < 1, "target_delta must be in (0,1)")
    mu_sq = sum(float(mu) ** 2 for mu in mus)
    ensure(mu_sq >= 0, "mu must be non-negative")
    mu_total = math.sqrt(mu_sq)
    epsilon = gdp_to_cdp(mu_total, target_delta)
    detail = {"rule": "gdp", "mu": mu_total, "target_delta": float(target_delta)}
    return CompositionResult(epsilon=epsilon, delta=target_delta, detail=detail)


def subsampling_amplification(event: PrivacyEventLike, *, sampling_rate: float) -> PrivacyEvent:
    # 使用泊松子采样启发式对单个事件应用隐私放大并更新 (ε, δ)
    """
    Apply privacy amplification by subsampling (Poisson sampling heuristic).

    ε' = log(1 + q * (exp(ε) - 1))
    δ' = q * δ
    """
    ensure(0 < sampling_rate <= 1, "sampling_rate must be in (0,1]")
    normalized = normalize_privacy_events([event])[0]
    eps_new = math.log(1.0 + sampling_rate * (math.exp(normalized.epsilon) - 1.0))
    delta_new = sampling_rate * normalized.delta
    return PrivacyEvent(
        epsilon=eps_new,
        delta=delta_new,
        description=normalized.description,
        metadata=dict(normalized.metadata),
        model=normalized.model,
        mechanism=normalized.mechanism,
        parameters=normalized.parameters,
        cdp_equivalent=normalized.cdp_equivalent,
        reports=normalized.reports,
    )


def shuffle_amplification(event: PrivacyEventLike, *, population: int) -> PrivacyEvent:
    # 通过对局部报告进行打乱以近似集中化带来的隐私放大效果
    """
    Simplified amplification by shuffling for local reports.

    Uses a loose √n scaling on ε to reflect centralisation effects.
    """
    ensure_type(population, (int,), label="population")
    ensure(population > 0, "population must be positive")
    normalized = normalize_privacy_events([event])[0]
    scale = 1.0 / math.sqrt(population)
    eps_new = normalized.epsilon * scale
    delta_new = normalized.delta * scale
    return PrivacyEvent(
        epsilon=eps_new,
        delta=delta_new,
        description=normalized.description,
        metadata=dict(normalized.metadata),
        model=normalized.model,
        mechanism=normalized.mechanism,
        parameters=normalized.parameters,
        cdp_equivalent=normalized.cdp_equivalent,
        reports=normalized.reports,
    )


def optimal_composition_fallback(
    events: Iterable[PrivacyEventLike],
    *,
    delta_hat: float,
) -> CompositionResult:
    # 作为最优组合占位实现根据事件是否同质在强组合与高级组合之间做策略降级
    """
    Placeholder for optimal composition; currently falls back to strong bound.
    """
    normalized = normalize_privacy_events(events)
    if not normalized:
        return CompositionResult.zero(detail={"rule": "optimal", "note": "no events"})
    unique_eps = {event.epsilon for event in normalized}
    unique_delta = {event.delta for event in normalized}
    if len(unique_eps) == 1 and len(unique_delta) == 1:
        # 同质 (ε, δ) 事件时使用 DRV10 强组合界作为近似最优解
        epsilon = next(iter(unique_eps))
        delta = next(iter(unique_delta))
        base = strong_composition(epsilon, delta, k=len(normalized), delta_hat=delta_hat)
        detail = dict(base.detail)
        detail.update({"rule": "optimal_fallback", "strategy": "strong"})
        return CompositionResult(epsilon=base.epsilon, delta=base.delta, detail=detail)
    # 异质事件组合时退化为 Dwork–Roth 高级组合界
    base = advanced_composition(normalized, delta_prime=delta_hat)
    detail = dict(base.detail)
    detail.update({"rule": "optimal_fallback", "strategy": "advanced"})
    return CompositionResult(epsilon=base.epsilon, delta=base.delta, detail=detail)
