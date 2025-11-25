"""
Unit tests for the BudgetTracker helper.
"""
# 说明：BudgetTracker（多作用域预算跟踪器）的单元测试。
# 覆盖：
# - 多阈值告警流程：跨越 0.5 / 1.0 等阈值时分别触发一次告警（回调收集 BudgetAlert）
# - 作用域注册与校验：无效阈值配置抛 ParamValidationError，未注册作用域花费抛 ScopeNotRegisteredError
# - 序列化 / 反序列化往返：保持作用域集合、累计花费与告警历史的一致性
# - 通过 spend 传入 ModelSpec / PrivacyGuarantee 时，审计 reports 与 metadata["privacy"] 的正确传播，
#   以及序列化后恢复的事件中应仍保留 reports 信息

from __future__ import annotations

from typing import Any, List

import pytest

from dplib.core.privacy import (
    BudgetAlert,
    BudgetTracker,
    ScopeNotRegisteredError,
    TrackedScope,
)
from dplib.core.utils.param_validation import ParamValidationError
from dplib.core.privacy.privacy_model import ModelSpec, PrivacyModel, MechanismType
from dplib.core.privacy.privacy_guarantee import PrivacyGuarantee


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
    # 无效阈值配置抛 ParamValidationError
    # 未注册作用域上花费应抛 ScopeNotRegisteredError，已注册作用域应可正常花费
    tracker = BudgetTracker()
    with pytest.raises(ParamValidationError):
        BudgetTracker(thresholds=[-0.1])
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


def test_spend_with_multiple_models_propagates_reports() -> None:
    # 通过 spend 传入 zCDP ModelSpec 与 CDP PrivacyGuarantee，验证 reports 与 metadata["privacy"] 的传播
    tracker = BudgetTracker(thresholds=[1.0])
    scope = tracker.register_scope("session", "m1", total_epsilon=6.0, total_delta=1e-4)
    spec_zcdp = ModelSpec(model=PrivacyModel.ZCDP, rho=0.5)
    guar_cdp = PrivacyGuarantee.from_model_spec(
        ModelSpec(model=PrivacyModel.CDP, epsilon=0.1, delta=1e-6), mechanism=MechanismType.GAUSSIAN
    )
    event = tracker.spend(
        scope,
        0.0,
        0.0,
        model_specs=[spec_zcdp],
        guarantees=[guar_cdp],
        target_delta=1e-5,
    )
    assert event.reports
    assert isinstance(event.metadata.get("privacy"), list)
    assert event.model == event.reports[0]["model"]
    payload = tracker.serialize()
    restored = BudgetTracker.deserialize(payload)
    restored_scope = next(iter(restored.scopes()))
    restored_event = restored.get_accountant(restored_scope).events[0]
    assert restored_event.reports
