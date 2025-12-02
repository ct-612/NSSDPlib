"""
Budget scheduler for allocating CDP budgets across tasks or time windows.

Designed to sit on top of the core PrivacyAccountant primitives and
provide light-weight strategies for dividing a total (ε, δ) into
sub-allocations (tasks, batches, windows).
"""
# 说明：在总 (ε, δ) 预算之上为任务或时间窗口进行差分隐私预算切分的调度器。
# 职责：
# - 基于 PrivacyBudget 对象管理全局中心差分隐私总预算
# - 提供按任务键统一划分与按权重成比例划分的预算分配策略
# - 提供按时间窗口带几何衰减的预算安排以及已分配预算后的剩余额度计算

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Tuple

from dplib.core.privacy.privacy_accountant import PrivacyBudget
from dplib.core.utils.param_validation import ParamValidationError, ensure


@dataclass(frozen=True)
class Allocation:
    """Immutable allocation container."""

    epsilon: float
    delta: float

    def to_budget(self) -> PrivacyBudget:
        # 将当前分配转换为 PrivacyBudget 实例以便与记账器接口对接
        return PrivacyBudget(self.epsilon, self.delta)


class BudgetScheduler:
    """
    Schedule ε/δ budgets over tasks or time windows.

    Strategies:
        * uniform: equal split
        * proportional: split by user-provided weights
        * geometric_decay: for ordered windows (earlier windows get more)
    """

    def __init__(self, total_epsilon: float, total_delta: float = 0.0):
        # 使用给定总 ε 与 δ 构造全局预算对象作为后续切分的来源
        self.total = PrivacyBudget(total_epsilon, total_delta)

    # ------------------------------ task-based allocation
    def allocate_uniform(self, items: Mapping[str, float]) -> Dict[str, Allocation]:
        # 对给定键集合进行均匀切分，忽略值部分仅使用键作为单元标识
        """Equal split across items (values ignored, keys used as identifiers)."""
        if not items:
            raise ParamValidationError("items cannot be empty")
        share_eps = self.total.epsilon / len(items)
        share_delta = self.total.delta / len(items)
        return {key: Allocation(share_eps, share_delta) for key in items}

    def allocate_proportional(self, weights: Mapping[str, float]) -> Dict[str, Allocation]:
        # 按调用方提供的非负权重比例切分全局 ε 和 δ 预算
        """Split proportionally to provided weights."""
        if not weights:
            raise ParamValidationError("weights cannot be empty")
        total_weight = sum(weights.values())
        ensure(total_weight > 0, "weights must sum to a positive value")
        allocations: Dict[str, Allocation] = {}
        for key, weight in weights.items():
            ensure(weight >= 0, "weights must be non-negative")
            ratio = weight / total_weight if total_weight else 0.0
            allocations[key] = Allocation(
                epsilon=self.total.epsilon * ratio,
                delta=self.total.delta * ratio,
            )
        return allocations

    # ------------------------------ time-window allocation
    def allocate_windows(
        self,
        window_count: int,
        *,
        decay: float = 1.0,
    ) -> Tuple[Allocation, ...]:
        """
        Allocate across ordered windows with optional geometric decay.
        decay=1.0 -> uniform; decay<1 distributes more to early windows.
        """
        # 面向有序时间窗口的预算切分接口，可通过几何衰减控制前后窗口分配比例
        if window_count <= 0:
            raise ParamValidationError("window_count must be positive")
        ensure(decay > 0, "decay must be positive")
        if decay == 1.0:
            return tuple(self.allocate_uniform({str(i): 1 for i in range(window_count)}).values())

        # geometric series weights: 1, decay, decay^2, ...
        weights = [decay**i for i in range(window_count)]
        total_weight = sum(weights)
        allocations = []
        for w in weights:
            ratio = w / total_weight
            allocations.append(
                Allocation(
                    epsilon=self.total.epsilon * ratio,
                    delta=self.total.delta * ratio,
                )
            )
        return tuple(allocations)

    # ------------------------------ convenience
    def remaining_after_allocation(self, allocations: Mapping[str, Allocation]) -> PrivacyBudget:
        # 计算给定一组分配后剩余的隐私预算并截断为非负值
        """Compute residual budget after a set of allocations."""
        eps_spent = sum(a.epsilon for a in allocations.values())
        delta_spent = sum(a.delta for a in allocations.values())
        remaining_eps = max(self.total.epsilon - eps_spent, 0.0)
        remaining_delta = max(self.total.delta - delta_spent, 0.0)
        return PrivacyBudget(remaining_eps, remaining_delta)
