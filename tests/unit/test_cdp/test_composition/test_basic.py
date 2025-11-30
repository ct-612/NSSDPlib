"""
Unit tests for basic CDP composition helpers.
"""
# 说明：中心差分隐私基础组合与工程化辅助函数的单元测试。
# 覆盖：
# - 验证 linear_addition 对多次机制的 ε 和 δ 进行线性累加
# - 验证 sequential_composition 对异构输入事件归一化与顺序组合的行为
# - 验证 parallel_composition 在分组与自定义 reducer 情况下的组合逻辑
# - 验证 repeated_mechanism 对重复次数的线性缩放与非法重复次数的校验
# - 验证 post_processing_invariance 的后处理不变性标记与元数据保持
# - 验证 group_privacy 在纯 DP 与近似 DP 下对 ε 和 δ 的缩放与放大公式

import math

import pytest

from dplib.cdp.composition.basic import (
    group_privacy,
    linear_addition,
    parallel_composition,
    post_processing_invariance,
    repeated_mechanism,
    sequential_composition,
)
from dplib.core.privacy.composition import CompositionResult, SequentialCompositionRule
from dplib.core.privacy.privacy_accountant import PrivacyEvent
from dplib.core.utils.param_validation import ParamValidationError


def test_linear_addition_sums_components() -> None:
    # 验证 linear_addition 正确按分量对 ε 与 δ 进行求和
    result = linear_addition([0.2, 0.3], [1e-5, 2e-5])
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(3e-5)
    assert result.detail["rule"] == "linear"


def test_sequential_composition_normalizes_inputs() -> None:
    # 验证 sequential_composition 能接受元组与字典形式事件并进行归一化组合
    events = [(0.1, 1e-6), {"epsilon": 0.2, "delta": 2e-6}]
    result = sequential_composition(events)
    assert result.epsilon == pytest.approx(0.3)
    assert result.delta == pytest.approx(3e-6)
    assert result.detail["rule"] == "sequential"
    assert result.detail["count"] == 2


def test_parallel_composition_group_key_and_max_reducer() -> None:
    # 验证 parallel_composition 按 group_key 分组并使用默认最大值聚合各组结果
    events = [
        {"epsilon": 0.5, "delta": 1e-5, "metadata": {"group": "region-a"}},
        {"epsilon": 0.2, "delta": 0.0, "metadata": {"group": "region-a"}},
        {"epsilon": 0.1, "delta": 0.0, "metadata": {"group": "region-b"}},
    ]
    result = parallel_composition(events, group_key=lambda event, _idx: event.metadata["group"])
    assert result.epsilon == pytest.approx(0.7)  # region-a dominates
    assert result.delta == pytest.approx(1e-5)
    assert result.detail["aggregator"] == "max"
    assert result.detail["groups"] == 2


def test_parallel_composition_respects_custom_reducer() -> None:
    # 验证 parallel_composition 在传入自定义 reducer 与 inner_rule 时按预期组合
    events = [
        {"epsilon": 0.1, "delta": 1e-6, "metadata": {"g": "a"}},
        {"epsilon": 0.2, "delta": 1e-6, "metadata": {"g": "b"}},
    ]

    def sum_reducer(results: tuple[CompositionResult, ...]) -> CompositionResult:
        # 自定义 reducer 使用逐组求和的方式聚合 ε 与 δ
        return CompositionResult(
            epsilon=sum(r.epsilon for r in results),
            delta=sum(r.delta for r in results),
            detail={"aggregator": "sum", "groups": len(results)},
        )

    result = parallel_composition(
        events,
        group_key=lambda event, _idx: event.metadata["g"],
        reducer=sum_reducer,
        inner_rule=SequentialCompositionRule(),
    )
    assert result.epsilon == pytest.approx(0.3)
    assert result.delta == pytest.approx(2e-6)
    assert result.detail["aggregator"] == "sum"
    assert result.detail["groups"] == 2


def test_repeated_mechanism_scales_linearly() -> None:
    # 验证 repeated_mechanism 对同一机制重复次数进行线性缩放
    result = repeated_mechanism(0.05, 1e-6, repetitions=10)
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(1e-5)


def test_repeated_mechanism_invalid_repetitions() -> None:
    # 验证 repeated_mechanism 对非法重复次数抛出 ParamValidationError
    with pytest.raises(ParamValidationError):
        repeated_mechanism(0.1, repetitions=0)


def test_post_processing_invariance_preserves_privacy_event() -> None:
    # 验证 post_processing_invariance 保持 ε 和 δ 不变并在元数据中标记后处理
    event = {"epsilon": 0.4, "delta": 1e-4, "metadata": {"tag": "x"}}
    processed = post_processing_invariance(event)
    assert processed.epsilon == pytest.approx(0.4)
    assert processed.delta == pytest.approx(1e-4)
    assert processed.metadata["composition"]["post_processing"] is True
    assert processed.metadata["tag"] == "x"


def test_group_privacy_scales_pure_dp_linearly() -> None:
    # 验证 group_privacy 在纯 DP 情况下只对 ε 进行线性缩放且 δ 保持为零
    result = group_privacy((0.3, 0.0), group_size=3)
    assert result.epsilon == pytest.approx(0.9)
    assert result.delta == 0.0
    assert result.detail["group_size"] == 3


def test_group_privacy_amplifies_delta_for_approx_dp() -> None:
    # 验证 group_privacy 在近似 DP 情况下按放大公式对 δ 进行指数加权
    event = PrivacyEvent(0.2, 1e-6)
    result = group_privacy(event, group_size=2)
    expected_delta = 1e-6 * (1 + math.exp(0.2))
    assert result.epsilon == pytest.approx(0.4)
    assert result.delta == pytest.approx(expected_delta)


def test_group_privacy_invalid_group_size() -> None:
    # 验证 group_privacy 在 group_size 非正时触发参数校验错误
    with pytest.raises(ParamValidationError):
        group_privacy((0.1, 0.0), group_size=0)
