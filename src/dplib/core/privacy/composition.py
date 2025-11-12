"""
Generic composition abstractions for differential privacy theorems.

Responsibilities:
    * normalise privacy events regardless of their original representation
    * provide reusable sequential, parallel, and higher-order composition rules
    * return structured CompositionResult objects for downstream accountants
"""
# 说明：差分隐私定理的通用组合抽象。
# 职责：
# - 将多种输入形式的隐私事件标准化为统一结构
# - 提供顺序组合、并行组合与高阶组合等可复用规则
# - 输出结构化 CompositionResult，便于与记账器等下游组件对接

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Hashable,
    Iterable,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from .base_mechanism import MechanismError, ValidationError
from .privacy_accountant import PrivacyEvent


PrivacyEventLike = Union[PrivacyEvent, Tuple[float, float], Dict[str, Any]]
# 事件输入别名：支持 PrivacyEvent、本征二元组 (epsilon, delta)、或字典
GroupKey = Callable[[PrivacyEvent, int], Hashable]
# 分组键函数：接收事件与其索引，返回可哈希分组键
Reducer = Callable[[Sequence["CompositionResult"]], "CompositionResult"]
# 归约器：将一组 CompositionResult 归并为单个结果


class CompositionError(MechanismError):
    """Raised when a composition rule cannot be evaluated."""
    # 组合规则无法评估时抛出


def _coerce_non_negative(value: Any, label: str) -> float:
    # 将值转换为浮点并确保非负；用于 epsilon/delta 基础校验
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValidationError(f"{label} must be convertible to float") from exc
    if numeric < 0:
        raise ValidationError(f"{label} must be non-negative")
    return numeric


def normalize_privacy_event(event: PrivacyEventLike) -> PrivacyEvent:
    """Convert supported shorthand inputs into a PrivacyEvent instance."""
    # 单个事件标准化：接受对象/字典/二元组(或含描述的三元组)，输出 PrivacyEvent
    if isinstance(event, PrivacyEvent):
        return event
    if isinstance(event, dict):
        epsilon = _coerce_non_negative(event.get("epsilon", 0.0), "epsilon")
        delta = _coerce_non_negative(event.get("delta", 0.0), "delta")
        description = event.get("description")
        metadata = dict(event.get("metadata", {}))
        return PrivacyEvent(epsilon=epsilon, delta=delta, description=description, metadata=metadata)
    if isinstance(event, (tuple, list)):
        if len(event) not in (2, 3):
            raise ValidationError("tuple/list privacy events must have 2 or 3 elements")
        epsilon = _coerce_non_negative(event[0], "epsilon")
        delta = _coerce_non_negative(event[1], "delta")
        description = event[2] if len(event) == 3 else None
        return PrivacyEvent(epsilon=epsilon, delta=delta, description=description)
    raise ValidationError(f"unsupported privacy event type: {type(event)!r}")


def normalize_privacy_events(events: Iterable[PrivacyEventLike]) -> Tuple[PrivacyEvent, ...]:
    """Normalise an iterable of privacy events."""
    # 批量标准化：返回不可变元组，便于后续规则安全处理
    return tuple(normalize_privacy_event(event) for event in events)


@dataclass(frozen=True)
class CompositionResult:
    """Container for the outcome of a composition rule."""
    # 组合结果：保存聚合后的 ε、δ 与可选细节字典；支持结果相加与 dict 序列化

    epsilon: float = 0.0
    delta: float = 0.0
    detail: Dict[str, Any] = field(default_factory=dict)

    def __add__(self, other: "CompositionResult") -> "CompositionResult":
        # 结果可加：数值相加，detail 右侧覆盖左侧同名键
        return CompositionResult(
            epsilon=self.epsilon + other.epsilon,
            delta=self.delta + other.delta,
            detail={**self.detail, **other.detail},
        )

    @classmethod
    def zero(cls, *, detail: Optional[Dict[str, Any]] = None) -> "CompositionResult":
        # 零元素构造器：便于空输入或初始化
        return cls(0.0, 0.0, detail=detail or {})

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly representation."""
        # JSON 友好导出
        return {"epsilon": float(self.epsilon), "delta": float(self.delta), "detail": dict(self.detail)}


class CompositionRule:
    """Base class for all composition rules."""
    # 组合规则基类：提供统一 compose 入口并委托 apply 实现

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    def compose(self, events: Iterable[PrivacyEventLike], **kwargs: Any) -> CompositionResult:
        # 对外入口：先标准化输入，再调用具体规则 apply
        normalized = normalize_privacy_events(events)
        return self.apply(normalized, **kwargs)

    def apply(self, events: Sequence[PrivacyEvent], **kwargs: Any) -> CompositionResult:
        # 子类需实现的核心逻辑
        raise NotImplementedError


class SequentialCompositionRule(CompositionRule):
    """Sequential composition that aggregates privacy loss additively."""
    # 顺序组合规则：ε、δ 逐事件线性累加

    def __init__(
        self,
        *,
        aggregator: Optional[Callable[[Sequence[PrivacyEvent]], Tuple[float, float]]] = None,
        name: Optional[str] = None,
    ):
        super().__init__(name)
        self._aggregator = aggregator or self._default_aggregator

    @staticmethod
    def _default_aggregator(events: Sequence[PrivacyEvent]) -> Tuple[float, float]:
        # 默认聚合器：简单求和
        epsilon = sum(event.epsilon for event in events)
        delta = sum(event.delta for event in events)
        return epsilon, delta

    def apply(self, events: Sequence[PrivacyEvent], **kwargs: Any) -> CompositionResult:
        epsilon, delta = self._aggregator(events)
        detail = {"rule": self.name, "count": len(events)}
        return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)


class ParallelCompositionRule(CompositionRule):
    """Parallel composition over disjoint sub-populations."""
    # 并行组合：对不相交子群体分别合成，再用归约器聚合（默认取分量最大）

    def __init__(
        self,
        *,
        group_key: Optional[GroupKey] = None,
        inner_rule: Optional[CompositionRule] = None,
        reducer: Optional[Reducer] = None,
        name: Optional[str] = None,
    ):
        super().__init__(name)
        self._group_key = group_key or (lambda _event, idx: idx)
        # 默认对每个分组使用顺序组合规则；规则名包含父规则名前缀便于追踪
        default_rule = inner_rule or SequentialCompositionRule(name=f"{self.name}GroupSequential")
        self._inner_rule = default_rule
        # 默认归约器：取各组结果在 ε、δ 上的最大值
        default_reducer = self._max_reducer
        self._reducer = reducer or default_reducer

    def apply(self, events: Sequence[PrivacyEvent], **kwargs: Any) -> CompositionResult:
        if not events:
            return CompositionResult.zero(detail={"rule": self.name, "groups": 0})
        key: GroupKey = kwargs.get("group_key", self._group_key)
        inner_rule: CompositionRule = kwargs.get("inner_rule", self._inner_rule)
        reducer: Reducer = kwargs.get("reducer", self._reducer)

        # 分组：按 group_key 将事件划分到不相交分组
        grouped: Dict[Hashable, list[PrivacyEvent]] = {}
        for idx, event in enumerate(events):
            grouped.setdefault(key(event, idx), []).append(event)

        # 对每个组应用内部规则，再用归约器合并
        group_results = tuple(inner_rule.apply(tuple(group)) for group in grouped.values())
        return reducer(group_results)

    def _max_reducer(self, results: Sequence[CompositionResult]) -> CompositionResult:
        # 最大化归约：返回 ε、δ 分量的逐组最大值，并附带每组明细
        if not results:
            return CompositionResult.zero(detail={"rule": self.name, "groups": 0, "aggregator": "max"})
        epsilon = max(result.epsilon for result in results)
        delta = max(result.delta for result in results)
        detail = {
            "rule": self.name,
            "groups": len(results),
            "aggregator": "max",
            "per_group": [{"epsilon": r.epsilon, "delta": r.delta} for r in results],
        }
        return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)


class HigherOrderCompositionRule(CompositionRule):
    """Higher-order composition that reuses a base rule and applies a transform."""
    # 高阶组合：复用基础规则（默认顺序组合）获得 base_result，再按阶数与变换函数修正
    # 实际可替换为更保守/精确的组合（如 advanced composition / zCDP 转换等）

    def __init__(
        self,
        order: int,
        *,
        base_rule: Optional[CompositionRule] = None,
        transform: Optional[
            Callable[[CompositionResult, int, Sequence[PrivacyEvent]], CompositionResult]
        ] = None,
        name: Optional[str] = None,
    ):
        if not isinstance(order, int): 
            raise ValidationError("order must be an integer")
        if order <= 0:
            raise ValidationError("order must be positive")
        super().__init__(name)
        self.order = int(order)
        self.base_rule = base_rule or SequentialCompositionRule(name=f"{self.name}BaseSequential")
        self._transform = transform or self._default_transform

    @staticmethod
    def _default_transform(
        base_result: CompositionResult, order: int, events: Sequence[PrivacyEvent]
    ) -> CompositionResult:
        # 默认变换：将基础结果按阶数线性放大；同时记录明细
        epsilon = base_result.epsilon * order
        delta = base_result.delta * order
        detail = {
            "rule": "HigherOrder",
            "order": order,
            "base": base_result.to_dict(),
            "count": len(events),
        }
        return CompositionResult(epsilon=epsilon, delta=delta, detail=detail)

    def apply(self, events: Sequence[PrivacyEvent], **kwargs: Any) -> CompositionResult:
        # 获取阶数与基础/变换策略，先计算 base_result，再进行自定义或默认变换
        order = int(kwargs.get("order", self.order))
        if not isinstance(order, int): 
            raise ValidationError("order must be an integer")
        if order <= 0:
            raise ValidationError("order must be positive")
        base_rule: CompositionRule = kwargs.get("base_rule", self.base_rule)
        transform = kwargs.get("transform", self._transform)
        base_result = base_rule.apply(events)
        return transform(base_result, order, events)

