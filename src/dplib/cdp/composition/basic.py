"""
Basic composition utilities for central differential privacy.

Responsibilities:
    * linear (additive) composition
    * sequential composition wrappers
    * simple parallel composition over disjoint groups
    * helper for repeating the same mechanism multiple times
"""
# 说明：面向中心化差分隐私（CDP）的基础组合工具。
# 职责：
# - 线性（加法）组合：直接对 (ε, δ) 求和
# - 顺序组合封装：复用统一的顺序组合规则
# - 并行组合：针对不相交分组的并行机制，按分组键聚合
# - 重复机制：同一机制重复调用的合成便捷函数

from __future__ import annotations

from typing import Callable, Iterable, Optional, Sequence

from dplib.core.privacy.composition import (
    CompositionResult,
    SequentialCompositionRule,
    ParallelCompositionRule,  
    normalize_privacy_events,
)


_SEQUENTIAL_RULE = SequentialCompositionRule(name="CDPBasicSequential")
# 共享的顺序组合规则实例：对一组事件的 ε、δ 线性累加
_PARALLEL_RULE = ParallelCompositionRule(name="CDPBasicParallel")
# 共享的并行组合规则实例：对分组后的事件按分量取最大或自定义归约


def linear_addition(epsilons: Sequence[float], deltas: Optional[Sequence[float]] = None) -> CompositionResult:
    """
    Compose independent mechanisms by summing epsilons (and optional deltas).

    Args:
        epsilons: Sequence of epsilon values.
        deltas: Optional sequence of delta values; defaults to zeros.
    """
    # 线性相加便捷函数：长度一致性检查；未提供 δ 时按 0 处理
    deltas = deltas or [0.0] * len(epsilons)
    if len(deltas) != len(epsilons):
        raise ValueError("deltas must match epsilons length")
    events = [(eps, delt) for eps, delt in zip(epsilons, deltas)]
    return _SEQUENTIAL_RULE.compose(events)


def sequential_composition(events: Iterable) -> CompositionResult:
    """Sequential composition wrapper using the shared sequential rule."""
    # 顺序组合封装：对输入事件直接应用共享的顺序规则
    return _SEQUENTIAL_RULE.compose(events)


def parallel_composition(events: Iterable, *, group_key: Optional[Callable] = None) -> CompositionResult:
    """
    Parallel composition assuming disjoint groups identified by `group_key`.

    Args:
        events: Iterable of privacy events.
        group_key: Optional callable returning a hashable key for each event.
    """
    # 并行组合封装：需要提供分组键以指示不相交分组；默认按索引分组
    normalized = normalize_privacy_events(events)
    if group_key is None:
        return _PARALLEL_RULE.apply(normalized)
    return _PARALLEL_RULE.apply(normalized, group_key=group_key)


def repeated_mechanism(epsilon: float, delta: float = 0.0, *, repetitions: int = 1) -> CompositionResult:
    """
    Compose the same mechanism multiple times via linear addition.

    Args:
        epsilon: Single-mechanism epsilon.
        delta: Single-mechanism delta.
        repetitions: Number of invocations of the mechanism.
    """
    # 重复机制合成：将 (ε, δ) 重复 N 次后做顺序组合
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    events = [(epsilon, delta)] * repetitions
    return _SEQUENTIAL_RULE.compose(events)
