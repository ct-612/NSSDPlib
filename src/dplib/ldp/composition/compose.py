"""
LDP composition helpers for per-user accounting.

Responsibilities:
    * add up epsilon values with non-negative checks
    * aggregate per-user usage and return budget summaries
    * offer sequential and parallel views over LocalPrivacyUsage

Notes:
    The entry points share linear aggregation, but different names signal
    intent and expected return shapes for sequential/parallel views.
"""
# 说明：LDP 组合规则的统一入口，提供基础、顺序与并行视角的工具函数。
# 职责：
# - 对 epsilon 做线性求和并校验非负输入
# - 按 user_id 聚合并输出 per-user 与系统级摘要
# - 提供顺序组合与并行组合的便捷入口供会计器复用

from __future__ import annotations

from typing import Dict, Sequence

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import LDPBudgetSummary, LocalPrivacyUsage


ANONYMOUS_USER_KEY = "<anonymous>"


def compose_epsilon_sum(epsilons: Sequence[float]) -> float:
    # 对 epsilon 序列做线性求和并拒绝负值输入
    total = 0.0
    for epsilon in epsilons:
        value = float(epsilon)
        if value < 0:
            raise ParamValidationError("epsilon must be non-negative")
        total += value
    return total


def compose_usages_sum(usages: Sequence[LocalPrivacyUsage]) -> float:
    # 提取每条 usage 的 epsilon 并复用基础求和规则
    return compose_epsilon_sum([usage.epsilon for usage in usages])


def per_user_epsilon(usages: Sequence[LocalPrivacyUsage]) -> Dict[str, float]:
    # 按 user_id 聚合每条 usage 的 epsilon 并输出累计结果
    per_user: Dict[str, float] = {}
    for usage in usages:
        value = float(usage.epsilon)
        if value < 0:
            raise ParamValidationError("epsilon must be non-negative")
        user_key = ANONYMOUS_USER_KEY if usage.user_id is None else str(usage.user_id)
        per_user[user_key] = per_user.get(user_key, 0.0) + value
    return per_user


def summarize_budget(usages: Sequence[LocalPrivacyUsage]) -> LDPBudgetSummary:
    # 汇总总 epsilon、每用户 epsilon、最大用户 epsilon 与事件数量
    per_user = per_user_epsilon(usages)
    total = compose_usages_sum(usages)
    max_user = max(per_user.values()) if per_user else 0.0
    return LDPBudgetSummary(
        total_epsilon=total,
        per_user_epsilon=per_user,
        max_user_epsilon=max_user,
        n_events=len(usages),
    )


def basic_composition(usages: Sequence[LocalPrivacyUsage]) -> LDPBudgetSummary:
    # 作为 LDP 基础组合入口返回总览摘要
    return summarize_budget(usages)


def sequential_composition(usages: Sequence[LocalPrivacyUsage]) -> float:
    # 将同一用户的多轮 usage 视为顺序组合并累加 epsilon
    return compose_usages_sum(usages)


def sequential_compose_by_user(usages: Sequence[LocalPrivacyUsage]) -> Dict[str, float]:
    # 按 user_id 聚合每个用户在多轮交互中的累计 epsilon
    return per_user_epsilon(usages)


def parallel_compose_by_user(usages: Sequence[LocalPrivacyUsage]) -> Dict[str, float]:
    # 直接返回每个用户的累计 epsilon 作为并行组合视角
    return per_user_epsilon(usages)


def parallel_composition(usages: Sequence[LocalPrivacyUsage]) -> LDPBudgetSummary:
    # 输出包含 max_user_epsilon 的系统级并行组合摘要
    return summarize_budget(usages)
