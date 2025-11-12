"""
Tests for generic DP composition rules.
"""
# 说明：通用 DP 合成规则的单元测试。
# 覆盖：
# - 事件标准化：将 dict/tuple 转为 PrivacyEvent
# - 顺序组合：ε、δ 线性相加，并产出事件计数元数据
# - 并行组合：按分组键聚合，每组内部顺序合成，最终取各组结果的分量最大值
# - 高阶组合：在基础顺序合成结果上按 order 缩放

import pytest

from dplib.core.privacy.composition import (
    HigherOrderCompositionRule,
    ParallelCompositionRule,
    SequentialCompositionRule,
    normalize_privacy_event,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent


def test_normalize_privacy_event_from_dict() -> None:
    # 字典输入应被标准化为 PrivacyEvent，且字段值保持一致
    event = normalize_privacy_event({"epsilon": 0.3, "delta": 1e-5, "description": "test"})
    assert isinstance(event, PrivacyEvent)
    assert event.epsilon == pytest.approx(0.3)
    assert event.delta == pytest.approx(1e-5)
    assert event.description == "test"


def test_sequential_composition_adds_eps_and_delta() -> None:
    # 顺序规则：两条事件的 ε、δ 线性相加；detail 中记录事件数量
    rule = SequentialCompositionRule()
    result = rule.compose([(0.2, 1e-5), (0.1, 2e-5)])
    assert result.epsilon == pytest.approx(0.3)
    assert result.delta == pytest.approx(3e-5)
    assert result.detail["count"] == 2


def test_parallel_composition_groups_and_takes_max() -> None:
    # 并行规则：按 metadata["group"] 分组，每组先顺序合成，再对组间取分量最大
    rule = ParallelCompositionRule()
    events = [
        {"epsilon": 0.5, "delta": 1e-5, "metadata": {"group": "A"}},
        {"epsilon": 0.2, "delta": 1e-5, "metadata": {"group": "A"}},
        {"epsilon": 0.1, "delta": 0.0, "metadata": {"group": "B"}},
    ]
    result = rule.compose(
        events,
        group_key=lambda event, _idx: event.metadata.get("group"),
    )
    assert result.epsilon == pytest.approx(0.7)   # 组 A: 0.5+0.2=0.7；组 B: 0.1 → 取最大 0.7
    assert result.delta == pytest.approx(2e-5)    # 组 A: 1e-5+1e-5=2e-5；组 B: 0 → 取最大 2e-5
    assert result.detail["groups"] == 2


def test_higher_order_default_scales_base_result() -> None:
    # 高阶规则：基础顺序结果按 order=3 放大
    base_rule = SequentialCompositionRule()
    base_result = base_rule.compose([(0.2, 1e-5), (0.1, 2e-5)])
    higher_rule = HigherOrderCompositionRule(order=3, base_rule=base_rule)
    result = higher_rule.compose([(base_result.epsilon, base_result.delta)])
    assert result.epsilon == pytest.approx(0.9) # (0.1+0.2) * 3 = 0.9
    assert result.delta == pytest.approx(9e-5) # (1e-5+2e-5) * 3 = 9e-5
    assert result.detail["order"] == 3
