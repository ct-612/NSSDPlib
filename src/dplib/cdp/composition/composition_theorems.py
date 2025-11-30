"""
Reference implementations of DP composition theorems for verification.

This module is intentionally math-only (no PrivacyEvent wrappers) to
serve property-based and numerical testing. It collects “authoritative”
formulas so higher-level helpers can be validated against them.
"""
# 说明：差分隐私组合定理的参考数学实现，用于测试验证。
# 职责：
# - 提供与文献一致的顺序组合、高级组合与替代表征转换的闭式公式
# - 为 property-based 测试与数值回归测试提供权威基线
# - 支持对比不同组合路径并检查隐私开销的单调性与合理性

from __future__ import annotations

import math
from typing import Dict, Iterable, Tuple

from dplib.core.privacy.privacy_model import gdp_to_cdp, rdp_to_cdp, zcdp_to_cdp
from dplib.core.utils.param_validation import ensure, ensure_type

FloatPair = Tuple[float, float]


def _to_float_list(values: Iterable[float], *, label: str) -> Tuple[float, ...]:
    # 将任意可迭代输入安全转换为 float 元组并在类型错误时抛出带标签的友好异常信息
    items = []
    for value in values:
        try:
            items.append(float(value))
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ValueError(f"{label} must contain numeric values") from exc
    return tuple(items)


# ------------------------------ Exact formulas
def sequential_sum(epsilons: Iterable[float], deltas: Iterable[float]) -> FloatPair:
    # 顺序组合的精确形式实现，对 ε 与 δ 分量分别做求和
    """Basic sequential composition: sum epsilon and delta."""
    eps = sum(_to_float_list(epsilons, label="epsilons"))
    delta = sum(_to_float_list(deltas, label="deltas"))
    return float(eps), float(delta)


def parallel_max(groups: Iterable[FloatPair]) -> FloatPair:
    # 并行组合的精确形式实现，对不相交组的 ε 与 δ 取坐标最大值
    """Parallel composition over disjoint groups: take coordinate-wise max."""
    pairs = tuple((float(eps), float(delta)) for eps, delta in groups)
    if not pairs:
        return 0.0, 0.0
    eps = max(e for e, _ in pairs)
    delta = max(d for _, d in pairs)
    return eps, delta


def advanced_pure_dp_bound(epsilons: Iterable[float], *, delta_prime: float) -> FloatPair:
    # 实现 Dwork–Roth 对纯 DP 事件的高级组合界用于精确对照库中封装实现
    """
    Dwork–Roth advanced composition for pure DP events (delta_i = 0).

    epsilon = sqrt(2 log(1/delta') * sum eps_i^2) + sum eps_i (exp(eps_i) - 1)
    delta = delta'
    """
    ensure(delta_prime > 0, "delta_prime must be positive")
    eps_list = _to_float_list(epsilons, label="epsilons")
    eps_sq_sum = sum(e * e for e in eps_list)
    eps_term = math.sqrt(2.0 * math.log(1.0 / delta_prime) * eps_sq_sum) if eps_sq_sum > 0 else 0.0
    linear_term = sum(e * (math.exp(e) - 1.0) for e in eps_list)
    epsilon = eps_term + linear_term
    return float(epsilon), float(delta_prime)


def drv10_strong_bound(epsilon: float, delta: float, *, k: int, delta_hat: float) -> FloatPair:
    # 实现 DRV10 强组合定理作为 k 次相同 (ε, δ)-DP 机制的精确上界
    """
    DRV10 strong composition for k identical (epsilon, delta)-DP mechanisms.
    """
    ensure_type(k, (int,), label="k")
    ensure(k > 0, "k must be positive")
    ensure(delta_hat > 0, "delta_hat must be positive")
    eps_prime = math.sqrt(2.0 * k * math.log(1.0 / delta_hat)) * float(epsilon)
    eps_prime += k * float(epsilon) * (math.exp(float(epsilon)) - 1.0)
    delta_prime = k * float(delta) + float(delta_hat)
    return eps_prime, delta_prime


def zcdp_to_cdp_bound(rhos: Iterable[float], *, target_delta: float) -> FloatPair:
    # 对一组 ρ-zCDP 保证进行求和并转换为等效的 (ε, δ)-DP
    """Sum rho-zCDP guarantees then convert to (epsilon, delta)-DP."""
    ensure(0 < target_delta < 1, "target_delta must be in (0,1)")
    rho_total = sum(_to_float_list(rhos, label="rhos"))
    ensure(rho_total >= 0, "rho must be non-negative")
    epsilon = zcdp_to_cdp(rho_total, target_delta)
    return epsilon, float(target_delta)


def rdp_to_cdp_bound(rdp_epsilons: Iterable[float], *, order: float, target_delta: float) -> FloatPair:
    # 在固定 Rényi 阶数下组合 RDP ε 并转换为 (ε, δ)-DP
    """Compose (alpha, epsilon_i)-RDP at fixed order and convert to CDP."""
    ensure(order > 1, "order must be > 1")
    ensure(0 < target_delta < 1, "target_delta must be in (0,1)")
    eps_rdp = sum(_to_float_list(rdp_epsilons, label="rdp_epsilons"))
    ensure(eps_rdp >= 0, "rdp epsilon must be non-negative")
    epsilon = rdp_to_cdp(order, eps_rdp, target_delta)
    return epsilon, float(target_delta)


def gdp_to_cdp_bound(mus: Iterable[float], *, target_delta: float) -> FloatPair:
    # 以 L2 范数组合一组 μ-GDP 值并通过 gdp_to_cdp 转换为 (ε, δ)-DP
    """Compose mu-GDP in L2 and convert via zCDP bridge to CDP."""
    ensure(0 < target_delta < 1, "target_delta must be in (0,1)")
    mu_sq = sum(float(mu) ** 2 for mu in _to_float_list(mus, label="mus"))
    ensure(mu_sq >= 0, "mu must be non-negative")
    mu_total = math.sqrt(mu_sq)
    epsilon = gdp_to_cdp(mu_total, target_delta)
    return epsilon, float(target_delta)


# ------------------------------ Verification helpers
def compare_composition_paths(
    epsilons: Iterable[float],
    deltas: Iterable[float],
    *,
    delta_hat: float,
) -> Dict[str, FloatPair]:
    # 统一事件列表下对比 strong 与 advanced 两种组合路径的隐私开销
    """
    Compare strong vs advanced bounds for the same event list.

    Returns a dict keyed by strategy name to facilitate property checks.
    """
    eps_list = _to_float_list(epsilons, label="epsilons")
    delta_list = _to_float_list(deltas, label="deltas")
    ensure(len(eps_list) == len(delta_list), "epsilons and deltas must align")
    strong_eps, strong_delta = drv10_strong_bound(
        eps_list[0] if eps_list else 0.0,
        delta_list[0] if delta_list else 0.0,
        k=len(eps_list),
        delta_hat=delta_hat,
    )
    adv_eps, adv_delta = advanced_pure_dp_bound(eps_list, delta_prime=delta_hat)
    return {
        "strong": (strong_eps, strong_delta),
        "advanced": (adv_eps, adv_delta),
    }


def assert_non_decreasing_spending(baseline: FloatPair, candidate: FloatPair) -> None:
    # 断言候选组合隐私开销不低于基线组合以保证单调性属性
    """Assertion helper: candidate spending should not be less than baseline."""
    if candidate[0] < baseline[0] or candidate[1] < baseline[1]:
        raise AssertionError("privacy spending decreased unexpectedly")
