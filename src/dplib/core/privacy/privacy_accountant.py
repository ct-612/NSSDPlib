"""
Privacy budget tracking and accounting helpers.

Provides an accountant that records DP spending events, enforces global
(ε, δ) budgets, and exposes serialisable audit metadata for audit/reporting.
"""
# 说明：隐私预算记账与管理工具，负责在库内统一跟踪与约束 (ε, δ) 花费。
# 职责：
# - PrivacyBudget：封装不可变的 (epsilon, delta) 预算，并支持加减与字典导出
# - PrivacyEvent：记录单次隐私花费事件及其审计元数据（模型、机制、等价 CDP 参数等）
# - PrivacyAccountant：维护总预算、累计花费与事件列表，提供超额检测、批量登记与序列化/反序列化
# - _normalize_allocation：统一处理显式 (ε, δ) 与 ModelSpec/PrivacyGuarantee，折算为 CDP 预算并生成审计报告

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .base_mechanism import MechanismError, ValidationError
from .privacy_model import ModelSpec
from .privacy_guarantee import PrivacyGuarantee


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
        # 构造后对 epsilon/delta 进行一次统一校验与标准化
        object.__setattr__(self, "epsilon", _validate_budget_value(self.epsilon, "epsilon"))
        object.__setattr__(self, "delta", _validate_budget_value(self.delta, "delta"))

    def __add__(self, other: "PrivacyBudget") -> "PrivacyBudget":
        # 逐分量相加，得到新的隐私预算对象
        return PrivacyBudget(self.epsilon + other.epsilon, self.delta + other.delta)

    def __sub__(self, other: "PrivacyBudget") -> "PrivacyBudget":
        # 减法结果下限为 0，避免出现负预算
        return PrivacyBudget(
            max(self.epsilon - other.epsilon, 0.0),
            max(self.delta - other.delta, 0.0),
        )

    def to_dict(self) -> Dict[str, float]:
        # 导出为易于序列化的字典结构
        return {"epsilon": float(self.epsilon), "delta": float(self.delta)}


@dataclass(frozen=True)
class PrivacyEvent:
    """Record for a single privacy allocation."""
    # 单次隐私花费事件记录：包含 ε/δ、可选描述、元数据、隐私模型标识、机制、参数、等价 CDP 参数与审计报告列表

    epsilon: float
    delta: float = 0.0
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: Optional[str] = None
    mechanism: Optional[str] = None
    parameters: Dict[str, float] = field(default_factory=dict)
    cdp_equivalent: Optional[Dict[str, float]] = None
    reports: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        # 序列化事件为 JSON 友好的字典（嵌套字典也做浅拷贝，避免外部修改原始对象）
        payload = {
            "epsilon": float(self.epsilon),
            "delta": float(self.delta),
            "description": self.description,
            "metadata": dict(self.metadata),
            "model": self.model,
            "mechanism": self.mechanism,
            "parameters": dict(self.parameters),
            "cdp_equivalent": None if self.cdp_equivalent is None else dict(self.cdp_equivalent),
            "reports": [dict(item) for item in self.reports],
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
        model_spec: Optional[ModelSpec] = None,
        guarantee: Optional[PrivacyGuarantee] = None,
        model_specs: Optional[Sequence[ModelSpec]] = None,
        guarantees: Optional[Sequence[PrivacyGuarantee]] = None,
        target_delta: Optional[float] = None,
        rdp_order: Optional[float] = None,
    ) -> PrivacyEvent:
        """
        Record a privacy-spending event and update cumulative totals.

        Responsibilities:
            * normalize various model/guarantee specifications into a concrete (ε, δ)
            * enforce that the new spend does not exceed the configured budget
            * create a structured PrivacyEvent for logging/auditing
            * update internal cumulative spending counters
        """
        # 隐私开销事件记录，流程：规范化输入 → 检查预算 → 记录事件 → 累加花费

        # 统一所有输入形式（显式 ε/δ、ModelSpec、PrivacyGuarantee等），得到最终用于预算计算的 (ε, δ) 以及审计用的 payload 列表
        epsilon, delta, audit_payloads = self._normalize_allocation(
            epsilon,
            delta,
            model_spec=model_spec,
            guarantee=guarantee,
            model_specs=model_specs,
            guarantees=guarantees,
            target_delta=target_delta,
            rdp_order=rdp_order,
        )
        # 真正记录事件前，对新花费进行预算校验（如果超出，则抛出异常，保持内部状态不变）
        self._ensure_within_budget(epsilon, delta)
        # 合并调用方传入的 metadata 与内部审计信息
        merged_metadata = dict(metadata or {})
        if audit_payloads:
            merged_metadata.setdefault(
                "privacy",
                audit_payloads if len(audit_payloads) != 1 else audit_payloads[0],
            )
        # primary 作为“主视图”：通常是第一个 payload，用来提取模型名、机制名、参数等核心元数据
        primary = audit_payloads[0] if audit_payloads else None
        # 构造不可变的 PrivacyEvent 实例
        event = PrivacyEvent(
            epsilon=epsilon,
            delta=delta,
            description=description,
            metadata=merged_metadata,
            model=primary.get("model") if primary else None,
            mechanism=primary.get("mechanism") if primary else None,
            parameters=primary.get("parameters") if primary else {},
            cdp_equivalent=primary.get("cdp_equivalent") if primary else None,
            reports=tuple(audit_payloads),
        )
        # 将事件追加到内部事件序列中，并累加总花费
        self._events.append(event)
        self._spent = PrivacyBudget(
            self._spent.epsilon + epsilon,
            self._spent.delta + delta,
        )
        return event

    def extend(self, events: Iterable[Tuple[float, float]]) -> None:
        # 批量添加事件：逐个遍历传入的 (ε, δ) 对，并复用 add_event 的完整逻辑
        for eps, delta in events:
            self.add_event(eps, delta)

    def reset(self) -> None:
        # 清空所有历史事件记录，同时将累计花费重置为 0
        # - 该操作会丢弃审计历史，只适合在明确的“新会话”边界或测试场景中使用
        # - 对于需要长期审计的生产环境，应避免频繁调用 reset
        self._events.clear()
        self._spent = PrivacyBudget(0.0, 0.0)


    # -------------------------------------------------------------- conversions
    def _normalize_allocation(
        self,
        epsilon: float,
        delta: float,
        *,
        model_spec: Optional[ModelSpec],
        guarantee: Optional[PrivacyGuarantee],
        model_specs: Optional[Sequence[ModelSpec]] = None,
        guarantees: Optional[Sequence[PrivacyGuarantee]] = None,
        target_delta: Optional[float],
        rdp_order: Optional[float],
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """Normalise all provided privacy specifications to a single CDP allocation."""
        # 标准化隐私预算分配：将所有提供的隐私规格归一化为单一的 CDP 分配
        # - 接受显式 (ε, δ) 与一个或多个 ModelSpec / PrivacyGuarantee
        # - 对非 CDP 的规格统一调用 as_cdp(...) 折算到 (ε, δ)-DP
        # - 用所有折算出的 ε/δ 的最大值作为本次分配的“保守上界”，并生成审计报告 payload
        items: List[Tuple[ModelSpec, Optional[PrivacyGuarantee]]] = []
        if model_spec is not None:
            items.append((model_spec, None))
        if guarantee is not None:
            items.append((guarantee.to_model_spec(), guarantee))
        for spec in model_specs or ():
            items.append((spec, None))
        for guar in guarantees or ():
            items.append((guar.to_model_spec(), guar))

        # 如果未提供任何模型规格/隐私保证，则直接使用显式传入的 (ε, δ)
        if not items:
            eps = _validate_budget_value(epsilon, "epsilon")
            dlt = _validate_budget_value(delta, "delta")
            return eps, dlt, []

        reports: List[Dict[str, Any]] = []
        eps_candidates: List[float] = []
        delta_candidates: List[float] = []

        for spec, guar in items:
            # 先校验单个模型规格，再折算为 CDP 视图以统一计入预算
            spec.validate()
            cdp_spec = spec.as_cdp(delta=target_delta, rdp_order=rdp_order)
            eps = _validate_budget_value(cdp_spec.epsilon, "epsilon")
            dlt = _validate_budget_value(cdp_spec.delta or 0.0, "delta")
            eps_candidates.append(eps)
            delta_candidates.append(dlt)
            # 为每一项构建审计报告条目，包含原模型、机制以及等价的 CDP 参数
            report: Dict[str, Any] = {
                "model": spec.model.value,
                "mechanism": guar.mechanism.value if guar and guar.mechanism else None,
                "parameters": spec.to_parameters(),
                "cdp_equivalent": {"epsilon": eps, "delta": dlt},
            }
            if guar:
                report["description"] = guar.description
                report["proof"] = guar.proof
            reports.append(report)

        # 采用“最大 ε / 最大 δ”作为本次合成分配的保守上界
        eps_total = max(eps_candidates) if eps_candidates else _validate_budget_value(epsilon, "epsilon")
        dlt_total = max(delta_candidates) if delta_candidates else _validate_budget_value(delta, "delta")
        return eps_total, dlt_total, reports

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
                model=item.get("model"),
                mechanism=item.get("mechanism"),
                parameters=dict(item.get("parameters") or {}),
                cdp_equivalent=(None if item.get("cdp_equivalent") is None else dict(item.get("cdp_equivalent"))),
                reports=tuple(dict(r) for r in item.get("reports", ())),
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
