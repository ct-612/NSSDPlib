"""
Unit tests for the PrivacyAccountant helper.
"""
# 说明：针对隐私预算记账器的单元测试。
# 覆盖：
# - add_event 的基础花费记账、剩余额度计算与事件历史记录
# - can_allocate 的事前可用性检查与 BudgetExceededError 超额保护行为
# - 无界预算（total_epsilon=None）场景以及 reset 对状态清空的效果
# - serialize / deserialize 往返保持名称、总预算、累计花费与事件元数据一致
# - 基于 ModelSpec / PrivacyGuarantee 的 zCDP/RDP/CDP 折算路径与审计报告生成逻辑
# - 对非法参数（如负 epsilon）的 ParamValidationError 处理
# - 反序列化后审计 reports 与 CDP 等价参数 cdp_equivalent 的完整保留

from __future__ import annotations

import pytest

from dplib.core.privacy.privacy_accountant import (
    BudgetExceededError,
    PrivacyAccountant,
    PrivacyBudget,
)
from dplib.core.privacy.privacy_model import ModelSpec, PrivacyModel, MechanismType
from dplib.core.privacy.privacy_guarantee import PrivacyGuarantee
from dplib.core.utils.param_validation import ParamValidationError


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
    # can_allocate 用于事前检查而不修改状态；超限时 add_event 应抛 BudgetExceededError
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


def test_add_event_with_model_spec_and_guarantees_reports() -> None:
    # 组合 ModelSpec 与 PrivacyGuarantee，应走 _normalize_allocation 折算并生成多条审计报告
    spec_zcdp = ModelSpec(model=PrivacyModel.ZCDP, rho=0.5)
    spec_rdp = ModelSpec(model=PrivacyModel.RDP, alpha=5.0, epsilon=0.3)
    guar_cdp = PrivacyGuarantee.from_model_spec(
        ModelSpec(model=PrivacyModel.CDP, epsilon=0.1, delta=1e-6),
        mechanism=MechanismType.GAUSSIAN,
        description="cdp-guarantee",
    )
    accountant = PrivacyAccountant(total_epsilon=6.0, total_delta=1e-4)
    event = accountant.add_event(
        0.05,
        0.0,
        model_specs=[spec_zcdp, spec_rdp],
        guarantees=[guar_cdp],
        target_delta=1e-5,
    )
    # 3 条报告：zCDP、RDP 和 CDP guarantee
    assert event.reports and len(event.reports) == 3
    # metadata 中应注入 privacy 报告列表
    assert isinstance(event.metadata.get("privacy"), list)
    # 累计 ε 至少应不小于所有 CDP 等价花费的最大值（保守上界）
    assert accountant.spent.epsilon >= max(
        r["cdp_equivalent"]["epsilon"] for r in event.reports if "cdp_equivalent" in r
    )
    first = event.reports[0]
    # 事件的 model / cdp_equivalent 与首条报告应保持同步，便于快速消费
    assert event.model == first["model"]
    assert event.cdp_equivalent == first["cdp_equivalent"]


def test_add_event_validation_errors() -> None:
    # 负 epsilon 等非法预算应通过 ParamValidationError 失败
    accountant = PrivacyAccountant()
    with pytest.raises(ParamValidationError):
        accountant.add_event(-0.1, 0.0)


def test_deserialize_preserves_reports() -> None:
    # 序列化→反序列化后，应保留审计 reports 与 CDP 等价参数
    spec = ModelSpec(model=PrivacyModel.ZCDP, rho=0.2)
    accountant = PrivacyAccountant(total_epsilon=4.0, total_delta=1e-4)
    event = accountant.add_event(0.0, 0.0, model_spec=spec, target_delta=1e-5)
    payload = accountant.serialize()
    restored = PrivacyAccountant.deserialize(payload)
    restored_event = restored.events[0]
    assert restored_event.reports
    assert restored_event.cdp_equivalent == event.cdp_equivalent
