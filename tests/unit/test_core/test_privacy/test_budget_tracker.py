"""
Unit tests for the BudgetTracker helper.
"""
# 说明：BudgetTracker（多作用域预算跟踪器）的单元测试。
# 覆盖：
# - 花费记录与阈值告警回调
# - 作用域注册校验与未注册作用域错误
# - 状态序列化/反序列化往返一致性

from __future__ import annotations

from typing import List

import pytest

from dplib.core.privacy import (
    BudgetAlert,
    BudgetTracker,
    ScopeNotRegisteredError,
    TrackedScope,
)


def test_budget_tracker_spend_and_alert(monkeypatch) -> None:
    # 用回调收集告警；验证跨越 0.5 与 1.0 阈值时各触发一次
    alerts: List[BudgetAlert] = []
    tracker = BudgetTracker(thresholds=[0.5, 1.0], alert_handler=alerts.append)
    scope = tracker.register_scope("task", "alpha", total_epsilon=1.0)

    tracker.spend(scope, 0.4)
    assert tracker.spent(scope).epsilon == pytest.approx(0.4)
    assert tracker.remaining(scope).epsilon == pytest.approx(0.6)
    assert alerts == []

    tracker.spend(scope, 0.2)  # crosses 0.5
    assert len(alerts) == 1
    assert alerts[0].threshold == pytest.approx(0.5)

    tracker.spend(scope, 0.4)  # crosses 1.0
    assert len(alerts) == 2
    assert alerts[1].threshold == pytest.approx(1.0)


def test_scope_validation_and_errors() -> None:
    # 未注册作用域上花费应抛 ScopeNotRegisteredError；已注册作用域应可正常花费
    tracker = BudgetTracker()
    scope = tracker.register_scope("user", "bob", total_epsilon=0.5)
    with pytest.raises(ScopeNotRegisteredError):
        tracker.spend(TrackedScope("user", "unknown"), 0.1)
    tracker.spend(scope, 0.1)


def test_tracker_serialization_roundtrip() -> None:
    # 序列化→反序列化后应保持作用域、已花费与告警历史一致
    tracker = BudgetTracker(thresholds=[0.5])
    scope = tracker.register_scope("session", "s1", total_epsilon=1.0, total_delta=1e-6)
    tracker.spend(scope, 0.6, 2e-7)
    payload = tracker.serialize()

    restored = BudgetTracker.deserialize(payload)
    restored_scope = next(iter(restored.scopes()))
    assert restored_scope.kind == "session"
    assert restored.spent(restored_scope).epsilon == pytest.approx(0.6)
    assert restored.spent(restored_scope).delta == pytest.approx(2e-7)
    assert len(restored.alerts) == 1
