"""
Privacy accountant utilities for tracking cumulative (epsilon, delta) spending.

Responsibilities:
    * validate budgets and individual privacy events
    * accumulate spending and guard against budget overruns
    * provide lightweight serialization for audit or checkpointing
"""
# 说明：用于累计与管理 (epsilon, delta) 隐私预算的记账器工具。
# 职责：
# - 验证隐私预算与单次事件
# - 累加花费并在超额时阻止
# - 提供轻量序列化，便于审计或中断恢复

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .base_mechanism import MechanismError, ValidationError


class BudgetExceededError(MechanismError):
    """Raised when an allocation would exceed the configured privacy budget."""
    # 当一次分配将导致总花费超过预算上限时抛出


def _validate_budget_value(value: float, label: str) -> float:
    """Ensure epsilon/delta components are finite and non-negative."""
    # 将输入转为 float，并确保非负；用于 epsilon/delta 的基础校验
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValidationError(f"{label} must be convertible to float") from exc
    if label == "epsilon" and numeric < 0:
        raise ValidationError("epsilon must be non-negative")
    if label == "delta" and numeric < 0:
        raise ValidationError("delta must be non-negative")
    return numeric


@dataclass(frozen=True)
class PrivacyBudget:
    """Simple container for epsilon/delta pairs."""
    # 不可变的预算容器；支持加减与字典导出

    epsilon: float = 0.0
    delta: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "epsilon", _validate_budget_value(self.epsilon, "epsilon"))
        object.__setattr__(self, "delta", _validate_budget_value(self.delta, "delta"))

    def __add__(self, other: "PrivacyBudget") -> "PrivacyBudget":
        return PrivacyBudget(self.epsilon + other.epsilon, self.delta + other.delta)

    def __sub__(self, other: "PrivacyBudget") -> "PrivacyBudget":
        # 减法结果下限为 0，避免出现负预算
        return PrivacyBudget(
            max(self.epsilon - other.epsilon, 0.0),
            max(self.delta - other.delta, 0.0),
        )

    def to_dict(self) -> Dict[str, float]:
        return {"epsilon": float(self.epsilon), "delta": float(self.delta)}


@dataclass(frozen=True)
class PrivacyEvent:
    """Record for a single privacy allocation."""
    # 单次隐私花费事件记录：包含 ε/δ、可选描述与元数据

    epsilon: float
    delta: float = 0.0
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "epsilon": float(self.epsilon),
            "delta": float(self.delta),
            "description": self.description,
            "metadata": dict(self.metadata),
        }
        return payload


class PrivacyAccountant:
    """Track cumulative privacy usage and guard against exceeding allocations."""
    # 记账器：维护总预算、累计花费、事件列表，并提供权限检查与序列化

    def __init__(
        self,
        total_epsilon: Optional[float] = None,
        total_delta: Optional[float] = None,
        *,
        name: Optional[str] = None,
        slack: float = 1e-12,
    ):
        """
        Args:
            total_epsilon: Optional global epsilon budget (None -> unbounded).
            total_delta: Optional global delta budget (defaults to 0 if None and epsilon provided).
            name: Optional identifier used in logs or serialization.
            slack: Numerical tolerance when checking residual budget.
        """
        # 只有提供了 ε 总预算时才允许设置 δ 总预算
        if total_epsilon is None and total_delta is not None:
            raise ValidationError("delta budget requires an epsilon budget as well")
        self.name = name or "PrivacyAccountant"
        # total_budget 为 None 表示不设上限；否则为有界预算
        self.total_budget: Optional[PrivacyBudget] = (
            PrivacyBudget(total_epsilon, total_delta or 0.0) if total_epsilon is not None else None
        )
        self.slack = float(slack)  # 容差，用于比较时避免浮点误差导致的误判
        if self.slack < 0:
            raise ValidationError("slack must be non-negative")
        self._events: List[PrivacyEvent] = []  # 历史事件
        self._spent = PrivacyBudget(0.0, 0.0)  # 已花费累计

    # --------------------------------------------------------------------- helpers
    def _ensure_within_budget(self, epsilon: float, delta: float) -> None:
        # 若为无界预算，直接通过；否则检验 future 花费是否越界（含 slack）
        if self.total_budget is None:
            return
        future = PrivacyBudget(self._spent.epsilon + epsilon, self._spent.delta + delta)
        limit = PrivacyBudget(
            self.total_budget.epsilon + self.slack,
            self.total_budget.delta + self.slack,
        )
        if future.epsilon > limit.epsilon or future.delta > limit.delta:
            remaining = self.remaining
            raise BudgetExceededError(
                "privacy budget exceeded: "
                f"requested (eps={epsilon}, delta={delta}) while remaining "
                f"(eps={remaining.epsilon if remaining else '∞'}, "
                f"delta={remaining.delta if remaining else '∞'})"
            )

    # --------------------------------------------------------------------- queries
    @property
    def spent(self) -> PrivacyBudget:
        """Return the cumulative spending so far."""
        # 返回当前累计花费（不可变对象）
        return self._spent

    @property
    def remaining(self) -> Optional[PrivacyBudget]:
        """Return remaining budget when bounded, otherwise None."""
        # 有界预算时返回剩余额度；无界返回 None
        if self.total_budget is None:
            return None
        return self.total_budget - self._spent

    @property
    def events(self) -> Tuple[PrivacyEvent, ...]:
        """Expose immutable history of recorded events."""
        # 以元组形式暴露事件历史，防止外部修改
        return tuple(self._events)

    def can_allocate(self, epsilon: float, delta: float = 0.0) -> bool:
        """Check availability without mutating internal state."""
        # 只做可用性检查，不改变内部状态；包含参数合法性校验
        try:
            epsilon = _validate_budget_value(epsilon, "epsilon")
            delta = _validate_budget_value(delta, "delta")
        except ValidationError:
            return False
        if self.total_budget is None:
            return True
        return (
            self._spent.epsilon + epsilon <= self.total_budget.epsilon + self.slack
            and self._spent.delta + delta <= self.total_budget.delta + self.slack
        )

    # ----------------------------------------------------------------- mutations
    def add_event(
        self,
        epsilon: float,
        delta: float = 0.0,
        *,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PrivacyEvent:
        """Record a privacy-spending event and update cumulative totals."""
        # 校验参数 → 预算检查 → 记录事件 → 累加已花费
        epsilon = _validate_budget_value(epsilon, "epsilon")
        delta = _validate_budget_value(delta, "delta")
        self._ensure_within_budget(epsilon, delta)
        event = PrivacyEvent(
            epsilon=epsilon,
            delta=delta,
            description=description,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        self._spent = PrivacyBudget(self._spent.epsilon + epsilon, self._spent.delta + delta)
        return event

    def extend(self, events: Iterable[Tuple[float, float]]) -> None:
        """Bulk-register a sequence of (epsilon, delta) pairs."""
        # 批量添加事件，逐个经过相同的校验与累计
        for eps, delta in events:
            self.add_event(eps, delta)

    def reset(self) -> None:
        """Clear recorded events and reset the spending counters."""
        # 清空事件与累计花费，恢复到初始状态
        self._events.clear()
        self._spent = PrivacyBudget(0.0, 0.0)

    # -------------------------------------------------------------- serialization
    def serialize(self) -> Dict[str, Any]:
        """Return a JSON-friendly snapshot of the accountant state."""
        # 导出可 JSON 化快照：名称、总预算、已花费、事件列表与容差
        return {
            "name": self.name,
            "total_budget": None if self.total_budget is None else self.total_budget.to_dict(),
            "spent": self._spent.to_dict(),
            "events": [event.to_dict() for event in self._events],
            "slack": self.slack,
        }

    @classmethod
    def deserialize(cls, payload: Dict[str, Any]) -> "PrivacyAccountant":
        """Recreate an accountant from serialized metadata."""
        # 从序列化数据重建记账器，包括总预算、已花费与事件历史
        total = payload.get("total_budget")
        accountant = cls(
            total_epsilon=None if total is None else total.get("epsilon"),
            total_delta=None if total is None else total.get("delta"),
            name=payload.get("name"),
            slack=payload.get("slack", 1e-12),
        )
        spent = payload.get("spent", {})
        accountant._spent = PrivacyBudget(
            spent.get("epsilon", 0.0),
            spent.get("delta", 0.0),
        )
        events = payload.get("events", [])
        accountant._events = [
            PrivacyEvent(
                epsilon=item.get("epsilon", 0.0),
                delta=item.get("delta", 0.0),
                description=item.get("description"),
                metadata=dict(item.get("metadata") or {}),
            )
            for item in events
        ]
        return accountant

    # ------------------------------------------------------------------ debugging
    def __repr__(self) -> str:
        # 便于调试的简洁字符串表示：展示名称、总预算、已花费与事件数量
        budget = self.total_budget.to_dict() if self.total_budget else None
        return (
            f"<PrivacyAccountant name={self.name!r} "
            f"total={budget} spent={self._spent.to_dict()} events={len(self._events)}>"
        )
