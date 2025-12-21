"""
Unit tests for the LDP-to-CDP accountant bridge.
"""
# 说明：LDP 记账器到 CDP 记账器的桥接测试
# 覆盖：
# - LDP 使用记录被映射并写入 CDP 事件
# - 负 delta 被拒绝并抛出 ParamValidationError
from __future__ import annotations

import pytest

from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.composition.privacy_accountant import LDPPrivacyAccountant
from dplib.ldp.types import LocalPrivacyUsage


def test_ldp_accountant_forwards_to_cdp() -> None:
    # 验证 LDP 使用记录被转发为 CDP 事件并带上下文
    cdp_accountant = CDPPrivacyAccountant()
    ldp_accountant = LDPPrivacyAccountant(cdp_accountant=cdp_accountant)
    # 构造包含机制信息与 delta 的使用记录
    usage = LocalPrivacyUsage(
        user_id="user-1",
        epsilon=0.4,
        round_id=1,
        metadata={
            "delta": 1e-6,
            "mechanism": "grr",
            "mechanism_params": {"k": 3},
            "description": "ldp-round",
        },
    )

    # 写入使用记录并触发桥接逻辑
    ldp_accountant.add_usage(usage)

    # 校验转发事件与上下文字段
    assert len(cdp_accountant.events) == 1
    event = cdp_accountant.events[0]
    assert event.epsilon == pytest.approx(0.4)
    assert event.delta == pytest.approx(1e-6)
    context = event.metadata["ldp_context"]
    assert context["user_id"] == "user-1"
    assert context["round_id"] == 1
    assert context["mechanism"] == "grr"
    assert context["mechanism_params"]["k"] == 3
    assert cdp_accountant.spent == (pytest.approx(0.4), pytest.approx(1e-6))


def test_ldp_accountant_rejects_negative_delta() -> None:
    # 验证负 delta 输入会被拒绝
    cdp_accountant = CDPPrivacyAccountant()
    ldp_accountant = LDPPrivacyAccountant(cdp_accountant=cdp_accountant)
    # 构造带负 delta 的使用记录
    usage = LocalPrivacyUsage(
        user_id="user-2",
        epsilon=0.1,
        metadata={"delta": -1e-6},
    )

    # 校验异常抛出
    with pytest.raises(ParamValidationError):
        ldp_accountant.add_usage(usage)
