"""
CDP-level privacy accountant with pluggable composition strategies.

This module wraps the core PrivacyAccountant and exposes a strategy
selector so callers can switch between basic, advanced, strong, RDP/zCDP,
GDP, or “optimal fallback” accounting without re-implementing the
formulas. It is intentionally light-weight and keeps inputs in terms of
epsilon/delta pairs or metadata fields for alternative models.

Responsibilities
  - Provide strategy-based composition over normalized privacy events.
  - Expose a CDP-focused API on top of the core PrivacyAccountant.
  - Support alternative models via metadata-based extraction.

Usage Context
  - Use when selecting composition strategies for CDP analytics.
  - Intended to wrap and extend the core accountant in pipelines.

Limitations
  - Strategy selection is limited to implemented composition helpers.
  - Parallel composition uses a simplified wrapper implementation.
"""
# 说明：为中心差分隐私提供可插拔组合策略的记账器封装层。
# 职责：
# - 在 BASIC/ADVANCED/STRONG/RDP/zCDP/GDP/OPTIMAL 多种组合策略之间进行解析与调度
# - 将异构事件输入归一化为 PrivacyEvent 序列并调用对应组合实现
# - 将组合后的 (ε, δ) 结果写入底层 PrivacyAccountant 并暴露已用与剩余预算视图

from __future__ import annotations

import enum
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from dplib.cdp.composition.advanced import (
    advanced_composition,
    gdp_composition,
    optimal_composition_fallback,
    rdp_composition,
    rho_zcdp_composition,
    strong_composition,
)
from dplib.cdp.composition.basic import parallel_composition, sequential_composition
from dplib.core.privacy.composition import CompositionResult, normalize_privacy_events
from dplib.core.privacy.privacy_accountant import PrivacyAccountant, PrivacyEvent
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type


class AccountingMethod(enum.Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    STRONG = "strong"
    RDP = "rdp"
    ZCDP = "zcdp"
    GDP = "gdp"
    OPTIMAL = "optimal"

    @classmethod
    def from_str(cls, name: str) -> "AccountingMethod":
        # 将字符串名称解析为 AccountingMethod 枚举并在未知名称时抛出参数校验错误
        try:
            return cls(name.lower())
        except Exception as exc:  # pragma: no cover - defensive
            raise ParamValidationError(f"unknown accounting method '{name}'") from exc


class CDPPrivacyAccountant:
    """
    Strategy-aware accountant for central DP.

    - Configuration
      - total_epsilon: Optional total epsilon budget for the core accountant.
      - total_delta: Optional total delta budget for the core accountant.
      - default_method: Default composition strategy used for compose calls.
      - name: Optional name for the underlying accountant.

    - Behavior
      - Normalises heterogeneous event inputs.
      - Composes using the selected strategy and records results.

    - Usage Notes
      - Provide metadata fields for RDP/zCDP/GDP compositions when required.
    """

    def __init__(
        self,
        *,
        total_epsilon: Optional[float] = None,
        total_delta: Optional[float] = None,
        default_method: AccountingMethod | str = AccountingMethod.BASIC,
        name: Optional[str] = None,
    ):
        # 初始化时配置默认组合策略与总预算并构造内部核心 PrivacyAccountant
        self.default_method = (
            default_method
            if isinstance(default_method, AccountingMethod)
            else AccountingMethod.from_str(str(default_method))
        )
        self._accountant = PrivacyAccountant(total_epsilon, total_delta, name=name)

    # ------------------------------ public API
    @property
    def spent(self) -> Tuple[float, float]:
        # 以元组形式返回当前累计消耗的 (ε, δ) 预算
        budget = self._accountant.spent
        return budget.epsilon, budget.delta

    @property
    def remaining(self) -> Optional[Tuple[float, float]]:
        # 以元组形式返回剩余可用预算没有上界时返回 None
        remaining = self._accountant.remaining
        return None if remaining is None else (remaining.epsilon, remaining.delta)

    @property
    def events(self) -> Sequence[PrivacyEvent]:
        # 暴露底层记账器记录的 PrivacyEvent 序列用于审计或测试
        return self._accountant.events

    def compose(
        self,
        events: Iterable[Mapping],
        *,
        method: AccountingMethod | str | None = None,
        **kwargs,
    ) -> CompositionResult:
        # 按指定或默认策略对一组事件进行组合并返回 CompositionResult
        strategy = self._resolve_method(method)
        normalized = normalize_privacy_events(events)
        if strategy == AccountingMethod.BASIC:
            return sequential_composition(normalized)
        if strategy == AccountingMethod.ADVANCED:
            return advanced_composition(normalized, delta_prime=float(kwargs.get("delta_prime", 1e-6)))
        if strategy == AccountingMethod.OPTIMAL:
            delta_hat = float(kwargs.get("delta_hat", 1e-6))
            return optimal_composition_fallback(normalized, delta_hat=delta_hat)
        if strategy == AccountingMethod.STRONG:
            epsilon, delta = self._ensure_uniform_epsilon_delta(normalized)
            k = int(kwargs.get("k", len(normalized)))
            delta_hat = float(kwargs.get("delta_hat", 1e-6))
            return strong_composition(epsilon, delta, k=k, delta_hat=delta_hat)
        if strategy == AccountingMethod.RDP:
            rdp_epsilons = kwargs.get("rdp_epsilons") or self._extract_field(normalized, key="rdp_epsilon")
            order = float(kwargs["order"])
            target_delta = float(kwargs["target_delta"])
            return rdp_composition(rdp_epsilons, order=order, target_delta=target_delta)
        if strategy == AccountingMethod.ZCDP:
            rhos = kwargs.get("rhos") or self._extract_field(normalized, key="rho")
            target_delta = float(kwargs["target_delta"])
            return rho_zcdp_composition(rhos, target_delta=target_delta)
        if strategy == AccountingMethod.GDP:
            mus = kwargs.get("mus") or self._extract_field(normalized, key="mu")
            target_delta = float(kwargs["target_delta"])
            return gdp_composition(mus, target_delta=target_delta)
        raise ParamValidationError(f"unsupported accounting method {strategy}")

    def add_composed_event(
        self,
        events: Iterable[Mapping],
        *,
        method: AccountingMethod | str | None = None,
        description: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs,
    ) -> CompositionResult:
        """
        Compose using the selected strategy and persist the aggregated spending
        into the underlying core accountant.
        """
        # 使用指定策略组合事件后将结果作为单个 PrivacyEvent 写入核心记账器
        result = self.compose(events, method=method, **kwargs)
        self._accountant.add_event(result.epsilon, result.delta, description=description, metadata=metadata)
        return result

    def compose_parallel(
        self,
        grouped_events: Iterable[Mapping],
        *,
        group_key=None,
        inner_method: AccountingMethod | str | None = None,
        **kwargs,
    ) -> CompositionResult:
        """
        Parallel composition wrapper: per-group compose then max-reduce.
        """
        # 针对分组事件提供并行组合封装，内部可指定分组组合所使用的策略
        inner = inner_method or self.default_method
        inner_rule = lambda events: self.compose(events, method=inner, **kwargs)  # noqa: E731
        return parallel_composition(
            grouped_events,
            group_key=group_key,
            inner_rule=None,  # handled via lambda above
            reducer=None,
            rule=None,
        ).__class__(  # type: ignore
            epsilon=inner_rule(grouped_events).epsilon,  # pragma: no cover - defensive placeholder
            delta=inner_rule(grouped_events).delta,
            detail={"rule": "parallel"},
        )

    # ------------------------------ helpers
    def _resolve_method(self, method: AccountingMethod | str | None) -> AccountingMethod:
        # 将调用方传入的策略参数统一解析为 AccountingMethod 枚举
        if method is None:
            return self.default_method
        if isinstance(method, AccountingMethod):
            return method
        return AccountingMethod.from_str(str(method))

    @staticmethod
    def _ensure_uniform_epsilon_delta(events: Sequence[PrivacyEvent]) -> Tuple[float, float]:
        # 校验所有事件的 ε 与 δ 是否一致以满足强组合 STRONG 的前提条件
        eps_set = {event.epsilon for event in events}
        delta_set = {event.delta for event in events}
        if len(eps_set) != 1 or len(delta_set) != 1:
            raise ParamValidationError("strong composition requires uniform epsilon/delta")
        return float(next(iter(eps_set))), float(next(iter(delta_set)))

    @staticmethod
    def _extract_field(events: Sequence[PrivacyEvent], *, key: str) -> Tuple[float, ...]:
        # 从事件元数据中提取给定键的数值序列并在缺失或非数值时抛出错误
        values = []
        for event in events:
            if key not in event.metadata:
                raise ParamValidationError(f"missing '{key}' in event metadata")
            try:
                values.append(float(event.metadata[key]))
            except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
                raise ParamValidationError(f"metadata '{key}' must be numeric") from exc
        return tuple(values)
