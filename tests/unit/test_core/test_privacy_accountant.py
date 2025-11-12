"""
Unit tests for the PrivacyAccountant helper.
"""
# 说明：针对隐私预算记账器的单元测试。
# 覆盖：
# - 事件追加、可分配性判定、无界模式、重置行为以及序列化往返一致性

from __future__ import annotations

import pytest

from dplib.core.privacy.privacy_accountant import (
    BudgetExceededError,
    PrivacyAccountant,
    PrivacyBudget,
)


def test_add_event_updates_spent_and_remaining() -> None:
    # 添加事件应正确更新累计花费与剩余预算，并记录事件描述
    accountant = PrivacyAccountant(total_epsilon=1.0, total_delta=1e-5)
    event = accountant.add_event(0.2, 2e-6, description="laplace")

    assert event.description == "laplace"
    assert accountant.spent == PrivacyBudget(0.2, 2e-6)
    remaining = accountant.remaining
    assert remaining is not None
    assert remaining.epsilon == pytest.approx(0.8)
    assert remaining.delta == pytest.approx(8e-6)
    assert len(accountant.events) == 1


def test_can_allocate_prevents_overflow() -> None:
    # can_allocate 用于事前检查不修改状态；超限时 add_event 应抛异常
    accountant = PrivacyAccountant(total_epsilon=0.5, total_delta=1e-6)
    accountant.add_event(0.4, 8e-7)
    assert accountant.can_allocate(0.1, 2e-7)
    assert accountant.can_allocate(0.11, 2e-7) is False

    with pytest.raises(BudgetExceededError):
        accountant.add_event(0.2, 1e-7)


def test_unbounded_accountant_allows_arbitrary_events() -> None:
    # 无界预算（未设置 total_epsilon）应允许任意事件；remaining 为 None
    accountant = PrivacyAccountant()
    accountant.add_event(5.0, 0.1)
    accountant.add_event(1.0)
    assert accountant.remaining is None
    assert len(accountant.events) == 2


def test_reset_clears_history() -> None:
    # reset 应清空事件历史并将累计花费置零
    accountant = PrivacyAccountant(total_epsilon=1.0)
    accountant.add_event(0.3)
    accountant.reset()
    assert accountant.spent == PrivacyBudget(0.0, 0.0)
    assert accountant.events == ()


def test_serialize_roundtrip_preserves_state() -> None:
    # 序列化→反序列化往返应保持名称、总预算、累计花费与事件元数据一致
    accountant = PrivacyAccountant(total_epsilon=1.0, total_delta=1e-5, name="acc")
    accountant.add_event(0.4, 2e-6, description="step-1", metadata={"stage": 1})
    payload = accountant.serialize()

    restored = PrivacyAccountant.deserialize(payload)
    assert restored.name == "acc"
    assert restored.total_budget == PrivacyBudget(1.0, 1e-5)
    assert restored.spent == accountant.spent
    assert len(restored.events) == 1
    assert restored.events[0].metadata == {"stage": 1}
