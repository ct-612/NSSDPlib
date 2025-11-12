"""
Budget tracking utilities for multi-tenant differential privacy workflows.

Responsibilities:
    * manage per-scope (task/user/session) privacy budgets via PrivacyAccountant
    * expose remaining/consumed budgets for instrumentation
    * trigger alert callbacks when configured thresholds are crossed
"""
# 说明：面向多租户/多作用域（任务/用户/会话）的隐私预算跟踪器。
# 职责：
# - 基于 PrivacyAccountant 管理每个作用域的 (ε, δ) 总预算与花费
# - 提供剩余额度/累计花费的查询接口，便于监控与指标采集
# - 当预算使用比例跨越阈值时触发告警回调（一次阈值只告警一次）

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .base_mechanism import MechanismError, ValidationError
from .privacy_accountant import PrivacyAccountant, PrivacyBudget, PrivacyEvent


class BudgetTrackerError(MechanismError):
    """Base exception for budget tracker failures."""
    # 跟踪器相关错误的基类


class ScopeNotRegisteredError(BudgetTrackerError):
    """Raised when attempting to spend against an unknown scope."""
    # 在未注册的作用域上记录花费时抛出


@dataclass(frozen=True)
class TrackedScope:
    """Identifier describing the logical budget namespace."""
    # 作用域标识：由 kind（类型）与 identifier（唯一 ID）构成，作为预算命名空间键

    kind: str
    identifier: str

    def __post_init__(self) -> None:
        # 基础校验：必须为非空字符串
        if not self.kind or not isinstance(self.kind, str):
            raise ValidationError("scope kind must be a non-empty string")
        if not self.identifier or not isinstance(self.identifier, str):
            raise ValidationError("scope identifier must be a non-empty string")


@dataclass
class BudgetAlert:
    """Alert emitted when a scope crosses a configured threshold."""
    # 告警实体：记录触发阈值的作用域、阈值、当前占比、已花费/剩余与消息

    scope: TrackedScope
    threshold: float
    ratio: float
    spent: PrivacyBudget
    remaining: Optional[PrivacyBudget]
    message: str
    metadata: Dict[str, str] = field(default_factory=dict)


AlertHandler = Callable[[BudgetAlert], None]
# 告警处理回调签名：接收 BudgetAlert，无返回值


class BudgetTracker:
    """Track privacy budgets across multiple scopes with alerting."""
    # 多作用域预算跟踪器：注册作用域 → 记录花费 → 自动评估并触发阈值告警

    def __init__(
        self,
        thresholds: Sequence[float] | None = None,
        *,
        alert_handler: Optional[AlertHandler] = None,
    ):
        """
        Args:
            thresholds: Fractional progress checkpoints (e.g. [0.5, 0.9, 1.0]).
            alert_handler: Optional callback invoked for newly triggered alerts.
        """
        # 初始化阈值（去重、排序、正数校验），注册告警回调，维护作用域→记账器映射、
        # 已触发阈值集合以及告警历史
        self._thresholds: Tuple[float, ...] = self._normalize_thresholds(thresholds)
        self._alert_handler = alert_handler
        self._accounts: Dict[TrackedScope, PrivacyAccountant] = {}
        self._triggered: Dict[TrackedScope, set[float]] = {}
        self._alerts: List[BudgetAlert] = []

    # ------------------------------------------------------------------ setup
    @staticmethod
    def _normalize_thresholds(thresholds: Sequence[float] | None) -> Tuple[float, ...]:
        # 归一化阈值列表：默认 (0.5, 0.8, 1.0)，去重、排序，并确保全为正数
        if thresholds is None:
            thresholds = (0.5, 0.8, 1.0)
        unique = sorted({float(value) for value in thresholds})
        for value in unique:
            if value <= 0:
                raise ValidationError("thresholds must be positive floating point values")
        return tuple(unique)

    def register_scope(
        self,
        kind: str,
        identifier: str,
        *,
        total_epsilon: float,
        total_delta: float = 0.0,
        slack: float = 1e-12,
    ) -> TrackedScope:
        """Register a new budget scope backed by a PrivacyAccountant."""
        # 注册新作用域并创建对应的 PrivacyAccountant；初始化已触发阈值集合
        scope = TrackedScope(kind, identifier)
        accountant = PrivacyAccountant(
            total_epsilon=total_epsilon,
            total_delta=total_delta,
            name=f"{scope.kind}:{scope.identifier}",
            slack=slack,
        )
        self._accounts[scope] = accountant
        self._triggered[scope] = set()
        return scope

    # ------------------------------------------------------------------ queries
    def scopes(self) -> Tuple[TrackedScope, ...]:
        """Return all registered scopes."""
        # 返回当前已注册的所有作用域（不可变视图）
        return tuple(self._accounts.keys())

    def get_accountant(self, scope: TrackedScope) -> PrivacyAccountant:
        """Return the accountant associated with `scope`."""
        # 获取作用域对应的记账器，若未注册则报错
        if scope not in self._accounts:
            raise ScopeNotRegisteredError(f"scope {scope} not registered")
        return self._accounts[scope]

    def remaining(self, scope: TrackedScope) -> Optional[PrivacyBudget]:
        """Convenience wrapper around the underlying accountant."""
        # 便捷获取作用域剩余预算
        return self.get_accountant(scope).remaining

    def spent(self, scope: TrackedScope) -> PrivacyBudget:
        """Return the total spent budget for the scope."""
        # 便捷获取作用域累计花费
        return self.get_accountant(scope).spent

    @property
    def alerts(self) -> Tuple[BudgetAlert, ...]:
        """Immutable copy of emitted alerts."""
        # 返回历史告警的不可变副本
        return tuple(self._alerts)

    # ------------------------------------------------------------------ spending
    def spend(
        self,
        scope: TrackedScope,
        epsilon: float,
        delta: float = 0.0,
        *,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> PrivacyEvent:
        """Record spending for the provided scope."""
        # 在作用域上登记一次花费事件，并评估是否触发阈值告警
        accountant = self.get_accountant(scope)
        event = accountant.add_event(
            epsilon,
            delta,
            description=description,
            metadata=metadata,
        )
        self._evaluate_alerts(scope)
        return event

    # ------------------------------------------------------------------ alerts
    def _evaluate_alerts(self, scope: TrackedScope) -> None:
        # 根据当前花费占比与阈值判断是否产生新告警；同一阈值只告警一次
        accountant = self._accounts[scope]
        total = accountant.total_budget
        if total is None or total.epsilon == 0 and total.delta == 0:
            return
        spent = accountant.spent
        ratio = self._compute_ratio(spent, total)
        triggered = self._triggered[scope]
        for threshold in self._thresholds:
            if threshold in triggered:
                continue
            if ratio >= threshold:
                alert = BudgetAlert(
                    scope=scope,
                    threshold=threshold,
                    ratio=ratio,
                    spent=spent,
                    remaining=accountant.remaining,
                    message=f"{scope.kind}:{scope.identifier} reached {ratio:.2f} of budget (threshold {threshold})",
                )
                triggered.add(threshold)
                self._alerts.append(alert)
                if self._alert_handler:
                    self._alert_handler(alert)

    @staticmethod
    def _compute_ratio(spent: PrivacyBudget, total: PrivacyBudget) -> float:
        # 占比定义：分别计算 ε 与 δ 的使用比例，取两者的最大值作为总体使用率
        eps_ratio = spent.epsilon / total.epsilon if total.epsilon > 0 else 0.0
        delta_ratio = spent.delta / total.delta if total.delta > 0 else 0.0
        return max(eps_ratio, delta_ratio)

    # ------------------------------------------------------------------ serialization
    def serialize(self) -> Dict[str, Any]:
        """Return JSON-friendly representation of the tracker state."""
        # 导出跟踪器当前状态：阈值列表、历史告警、各作用域的记账器快照与已触发阈值
        return {
            "thresholds": list(self._thresholds),
            "alerts": [
                {
                    "scope": {"kind": alert.scope.kind, "identifier": alert.scope.identifier},
                    "threshold": alert.threshold,
                    "ratio": alert.ratio,
                    "spent": alert.spent.to_dict(),
                    "remaining": None if alert.remaining is None else alert.remaining.to_dict(),
                    "message": alert.message,
                    "metadata": dict(alert.metadata),
                }
                for alert in self._alerts
            ],
            "scopes": [
                {
                    "scope": {"kind": scope.kind, "identifier": scope.identifier},
                    "accountant": accountant.serialize(),
                    "triggered_thresholds": list(self._triggered.get(scope, set())),
                }
                for scope, accountant in self._accounts.items()
            ],
        }

    @classmethod
    def deserialize(
        cls,
        payload: Dict[str, Any],
        *,
        alert_handler: Optional[AlertHandler] = None,
    ) -> "BudgetTracker":
        # 从序列化数据恢复跟踪器：重建告警历史、各作用域的记账器与已触发阈值集合
        tracker = cls(payload.get("thresholds"), alert_handler=alert_handler)
        tracker._alerts = [
            BudgetAlert(
                scope=TrackedScope(alert["scope"]["kind"], alert["scope"]["identifier"]),
                threshold=alert["threshold"],
                ratio=alert["ratio"],
                spent=PrivacyBudget(alert["spent"]["epsilon"], alert["spent"]["delta"]),
                remaining=(
                    None
                    if alert.get("remaining") is None
                    else PrivacyBudget(alert["remaining"]["epsilon"], alert["remaining"]["delta"])
                ),
                message=alert.get("message", ""),
                metadata=dict(alert.get("metadata") or {}),
            )
            for alert in payload.get("alerts", [])
        ]

        for scope_entry in payload.get("scopes", []):
            scope = TrackedScope(scope_entry["scope"]["kind"], scope_entry["scope"]["identifier"])
            accountant = PrivacyAccountant.deserialize(scope_entry["accountant"])
            tracker._accounts[scope] = accountant
            tracker._triggered[scope] = set(scope_entry.get("triggered_thresholds", []))
        return tracker
