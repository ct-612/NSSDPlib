"""
Unit tests for the LDP privacy accountant and mapping helpers.
"""
# 说明：LDPPrivacyAccountant 与 LDP 到 CDP 映射策略的单元测试。
# 覆盖：
# - 映射策略对 delta 与机制参数的解析
# - ldp_context 元数据补齐规则
# - 会计器预算校验与桥接转发行为

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from dplib.core.privacy.privacy_accountant import BudgetExceededError
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.composition.compose import ANONYMOUS_USER_KEY
from dplib.ldp.composition.ldp_cdp_mapping import (
    FALLBACK_DELTA_KEYS,
    FALLBACK_MECHANISM_KEYS,
    FALLBACK_MECHANISM_PARAMS_KEYS,
    RECOMMENDED_DELTA_KEY,
    RECOMMENDED_MECHANISM_KEY,
    RECOMMENDED_MECHANISM_PARAMS_KEY,
    default_ldp_to_cdp_mapper,
    normalize_cdp_event,
)
from dplib.ldp.composition.privacy_accountant import LDPPrivacyAccountant
from dplib.ldp.types import LDPToCDPEvent, LocalPrivacyUsage


class DummyCDPAccountant:
    # 模拟支持 add_event 的 CDP 会计器用于记录转发调用

    def __init__(self) -> None:
        # 初始化事件列表用于收集转发记录
        self.events: List[Dict[str, Any]] = []

    def add_event(self, epsilon: float, delta: float = 0.0, *, description: str | None = None, metadata: Dict[str, Any] | None = None) -> None:
        # 收集转发的事件参数用于断言
        self.events.append(
            {
                "epsilon": epsilon,
                "delta": delta,
                "description": description,
                "metadata": dict(metadata or {}),
            }
        )


class DummyComposedAccountant:
    # 模拟仅支持 add_composed_event 的 CDP 会计器

    def __init__(self) -> None:
        # 初始化事件列表用于收集转发记录
        self.events: List[Dict[str, Any]] = []

    def add_composed_event(self, events: List[Dict[str, Any]], *, description: str | None = None, metadata: Dict[str, Any] | None = None) -> None:
        # 收集转发的组合事件参数用于断言
        self.events.append(
            {
                "events": list(events),
                "description": description,
                "metadata": dict(metadata or {}),
            }
        )


def test_default_mapper_uses_recommended_keys() -> None:
    # 验证默认映射优先读取推荐字段名
    usage = LocalPrivacyUsage(
        user_id="u1",
        epsilon=0.4,
        metadata={
            RECOMMENDED_DELTA_KEY: 1e-6,
            FALLBACK_DELTA_KEYS[0]: 9e-6,
            RECOMMENDED_MECHANISM_KEY: "grr",
            FALLBACK_MECHANISM_KEYS[0]: "oue",
            RECOMMENDED_MECHANISM_PARAMS_KEY: {"k": 4},
            FALLBACK_MECHANISM_PARAMS_KEYS[0]: {"k": 99},
            "description": "ldp",
        },
    )
    event = default_ldp_to_cdp_mapper(usage)
    assert event.delta == pytest.approx(1e-6)
    assert event.mechanism == "grr"
    assert event.parameters["k"] == 4
    assert event.description == "ldp"


def test_default_mapper_uses_fallback_keys() -> None:
    # 验证默认映射在推荐字段缺失时回退到兼容字段名
    usage = LocalPrivacyUsage(
        user_id="u2",
        epsilon=0.5,
        metadata={
            FALLBACK_DELTA_KEYS[0]: 2e-6,
            FALLBACK_MECHANISM_KEYS[1]: "oue",
            FALLBACK_MECHANISM_PARAMS_KEYS[0]: {"p": 0.7},
        },
    )
    event = default_ldp_to_cdp_mapper(usage)
    assert event.delta == pytest.approx(2e-6)
    assert event.mechanism == "oue"
    assert event.parameters["p"] == 0.7


def test_normalize_cdp_event_populates_context() -> None:
    # 验证 normalize_cdp_event 补齐 ldp_context 的用户与机制信息
    usage = LocalPrivacyUsage(user_id=None, epsilon=0.3, round_id=2)
    event = LDPToCDPEvent(
        epsilon=0.3,
        delta=0.01,
        mechanism="custom",
        parameters={"alpha": 1},
        metadata={"tag": "x"},
    )
    normalized = normalize_cdp_event(usage, event)
    context = normalized.metadata["ldp_context"]
    assert context["user_id"] == ANONYMOUS_USER_KEY
    assert context["round_id"] == 2
    assert context["source"] == "ldp"
    assert context["mechanism"] == "custom"
    assert context["mechanism_params"]["alpha"] == 1
    assert context["delta"] == pytest.approx(0.01)


def test_default_mapper_rejects_negative_delta() -> None:
    # 验证默认映射对负 delta 抛出 ParamValidationError
    usage = LocalPrivacyUsage(user_id="u3", epsilon=0.2, metadata={RECOMMENDED_DELTA_KEY: -1e-6})
    with pytest.raises(ParamValidationError):
        default_ldp_to_cdp_mapper(usage)


def test_accountant_tracks_spend_and_limits() -> None:
    # 验证会计器累计花费并触发 per-user 限额
    accountant = LDPPrivacyAccountant(per_user_epsilon_limit=0.5)
    accountant.add_usage(LocalPrivacyUsage("u1", 0.3))
    accountant.add_usage(LocalPrivacyUsage("u2", 0.2))
    assert accountant.get_user_spent("u1") == pytest.approx(0.3)
    assert accountant.get_total_spent() == pytest.approx(0.5)
    with pytest.raises(BudgetExceededError):
        accountant.add_usage(LocalPrivacyUsage("u1", 0.3))


def test_accountant_enforces_global_limit() -> None:
    # 验证会计器在超过全局预算时抛出 BudgetExceededError
    accountant = LDPPrivacyAccountant(global_epsilon_limit=0.4)
    accountant.add_usage(LocalPrivacyUsage("u1", 0.2))
    with pytest.raises(BudgetExceededError):
        accountant.add_usage(LocalPrivacyUsage("u2", 0.3))


def test_accountant_rejects_negative_usage() -> None:
    # 验证会计器对负 epsilon 抛出 ParamValidationError
    accountant = LDPPrivacyAccountant()
    with pytest.raises(ParamValidationError):
        accountant.add_usage(LocalPrivacyUsage("u1", -0.1))


def test_accountant_forwards_with_custom_mapper() -> None:
    # 验证会计器使用自定义映射并转发到 add_event
    def mapper(usage: LocalPrivacyUsage) -> LDPToCDPEvent:
        # 自定义映射返回机制与参数用于桥接
        return LDPToCDPEvent(
            epsilon=usage.epsilon,
            delta=0.02,
            mechanism="custom",
            parameters={"alpha": 0.5},
            metadata={"note": "x"},
        )

    stub = DummyCDPAccountant()
    accountant = LDPPrivacyAccountant(cdp_accountant=stub, ldp_to_cdp_mapper=mapper)
    accountant.add_usage(LocalPrivacyUsage("u9", 0.4, round_id=1))
    assert len(stub.events) == 1
    event = stub.events[0]
    context = event["metadata"]["ldp_context"]
    assert event["epsilon"] == pytest.approx(0.4)
    assert event["delta"] == pytest.approx(0.02)
    assert context["mechanism"] == "custom"
    assert context["mechanism_params"]["alpha"] == 0.5
    assert context["delta"] == pytest.approx(0.02)


def test_accountant_forwards_with_add_composed_event() -> None:
    # 验证会计器在无 add_event 时转发到 add_composed_event
    stub = DummyComposedAccountant()
    accountant = LDPPrivacyAccountant(cdp_accountant=stub)
    accountant.add_usage(LocalPrivacyUsage("u8", 0.1))
    assert len(stub.events) == 1
    payload = stub.events[0]["events"][0]
    assert payload["epsilon"] == pytest.approx(0.1)
