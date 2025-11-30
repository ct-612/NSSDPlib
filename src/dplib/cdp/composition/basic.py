"""
Basic composition helpers for central differential privacy.

This module wraps the generic core composition rules with CDP-friendly
shortcuts and adds a few engineering conveniences such as repeated
mechanism scaling, post-processing invariance, and group privacy lifting.
"""
# 说明：围绕中心差分隐私的基础组合定理提供便捷封装和工程化辅助工具。
# 职责：
# - 基于通用组合规则提供顺序与并行组合的简化入口接口
# - 支持重复机制的线性放大、后处理不变性标注与 group privacy 提升变换
# - 在组合结果中携带规则名称与参数细节元数据以便审计与调试

from __future__ import annotations

import math
from typing import Iterable, Optional

from dplib.core.privacy.composition import (
    CompositionResult,
    GroupKey,
    ParallelCompositionRule,
    PrivacyEventLike,
    SequentialCompositionRule,
    normalize_privacy_events,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent
from dplib.core.utils.param_validation import ensure, ensure_type


def linear_addition(epsilons: Iterable[float], deltas: Iterable[float]) -> CompositionResult:
    # 使用线性累加方式将一组 ε 和 δ 聚合为单个组合结果
    """Linearly add ε and δ components."""
    eps_total = sum(float(eps) for eps in epsilons)
    delta_total = sum(float(delta) for delta in deltas)
    return CompositionResult(epsilon=eps_total, delta=delta_total, detail={"rule": "linear"})


def sequential_composition(
    events: Iterable[PrivacyEventLike],
    *,
    rule: Optional[SequentialCompositionRule] = None,
) -> CompositionResult:
    # 对一系列异质隐私事件应用顺序组合规则并按加法方式累加 ε 和 δ
    """
    Sequential composition for heterogeneous events.

    Uses the core SequentialCompositionRule to normalise events and sum
    ε/δ additively.
    """
    seq_rule = rule or SequentialCompositionRule(name="sequential")
    return seq_rule.compose(events)


def parallel_composition(
    events: Iterable[PrivacyEventLike],
    *,
    group_key: Optional[GroupKey] = None,
    inner_rule: Optional[SequentialCompositionRule] = None,
    reducer=None,
    rule: Optional[ParallelCompositionRule] = None,
) -> CompositionResult:
    # 在按 group_key 划分的不相交子集上并行组合隐私事件并通过 reducer 聚合各组结果
    """
    Parallel composition across disjoint subsets.

    Groups events by `group_key`, composes within each group using
    `inner_rule`, then reduces (default: per-coordinate max).
    """
    par_rule = rule or ParallelCompositionRule(
        group_key=group_key,
        inner_rule=inner_rule,
        reducer=reducer,
        name="parallel",
    )
    compose_kwargs = {}
    if group_key is not None:
        compose_kwargs["group_key"] = group_key
    if inner_rule is not None:
        compose_kwargs["inner_rule"] = inner_rule
    if reducer is not None:
        compose_kwargs["reducer"] = reducer
    return par_rule.compose(events, **compose_kwargs)


def repeated_mechanism(epsilon: float, delta: float = 0.0, *, repetitions: int = 1) -> CompositionResult:
    # 表示同一机制独立重复应用多次并按线性比例放大 ε 与 δ
    """Repeat the same mechanism `repetitions` times using linear scaling."""
    ensure_type(repetitions, (int,), label="repetitions")
    ensure(repetitions > 0, "repetitions must be positive")
    epsilons = (float(epsilon) for _ in range(repetitions))
    deltas = (float(delta) for _ in range(repetitions))
    return linear_addition(epsilons, deltas)


def post_processing_invariance(event: PrivacyEventLike) -> PrivacyEvent:
    # 显式体现后处理不增加隐私损失的性质并在元数据中标记 post_processing 标志
    """
    Return the same privacy event to emphasise post-processing closure.

    The function normalises the input and re-emits it unchanged while
    annotating the rule name in metadata.
    """
    normalized = normalize_privacy_events([event])[0]
    meta = dict(normalized.metadata)
    meta.setdefault("composition", {})["post_processing"] = True
    return PrivacyEvent(
        epsilon=normalized.epsilon,
        delta=normalized.delta,
        description=normalized.description,
        metadata=meta,
        model=normalized.model,
        mechanism=normalized.mechanism,
        parameters=normalized.parameters,
        cdp_equivalent=normalized.cdp_equivalent,
        reports=normalized.reports,
    )


def group_privacy(event: PrivacyEventLike, *, group_size: int = 1) -> CompositionResult:
    # 将单个个体的 (ε, δ)-DP 保证提升为 group_size 个体的 k-组隐私保证
    """
    Lift an (ε, δ)-DP guarantee to k-group privacy.

    For group size k, ε is scaled linearly; δ is amplified using the
    standard sum_{i=0}^{k-1} exp(i * ε) factor (pure DP keeps δ at 0).
    """
    ensure_type(group_size, (int,), label="group_size")
    ensure(group_size > 0, "group_size must be positive")
    normalized = normalize_privacy_events([event])[0]
    epsilon = float(normalized.epsilon) * group_size
    if normalized.delta == 0.0:
        delta = 0.0
    else:
        # 非零 δ 情况下使用 sum_{i=0}^{k-1} exp(i * ε) 系数放大尾部概率
        delta = float(normalized.delta) * sum(math.exp(normalized.epsilon * i) for i in range(group_size))
    detail = {"rule": "group_privacy", "group_size": group_size}
    return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)
