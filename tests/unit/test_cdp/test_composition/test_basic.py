"""
Unit tests for basic CDP composition helpers.

Covers:
    * linear_addition: sums ε/δ linearly; matches manual totals
    * sequential_composition: accepts PrivacyEvent sequences and composes additively
    * parallel_composition: groups by `group_key`, composes per group, then takes per-coordinate max
    * repeated_mechanism: repeating the same mechanism N times equals N× linear scaling
"""
# 说明：针对CDP基础组合工具的正确性验证。
# 覆盖：
# - 验证线性求和：直接对 ε、δ 分量做线性相加，期望与手工加总吻合
# - 顺序组合：接受 PrivacyEvent 序列并按顺序线性合成
# - 并行组合：通过 group_key 将事件分组，组内使用顺序合成，跨组对 ε、δ 取最大
# - 重复机制：同一机制重复 N 次应等价于参数的 N 倍线性放大

import pytest

from dplib.cdp.composition.basic import (
    linear_addition,
    parallel_composition,
    repeated_mechanism,
    sequential_composition,
)
from dplib.core.privacy.privacy_accountant import PrivacyEvent


def test_linear_addition_matches_manual_sum() -> None:
    # 线性相加：ε、δ 分别求和，应与手动加总一致
    result = linear_addition([0.2, 0.3], [1e-5, 2e-5])
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(3e-5)


def test_sequential_composition_wrapper_accepts_privacy_events() -> None:
    # 顺序组合封装：直接接受 PrivacyEvent 对象并线性相加
    events = [
        PrivacyEvent(0.4, 1e-5),
        PrivacyEvent(0.1, 0.0),
    ]
    result = sequential_composition(events)
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(1e-5)


def test_parallel_composition_uses_group_key() -> None:
    # 并行组合：按 metadata["group"] 分组；对各组顺序合成后取分量最大
    events = [
        {"epsilon": 0.5, "delta": 1e-5, "metadata": {"group": "region-a"}},
        {"epsilon": 0.2, "delta": 0.0, "metadata": {"group": "region-a"}},
        {"epsilon": 0.1, "delta": 0.0, "metadata": {"group": "region-b"}},
    ]
    result = parallel_composition(events, group_key=lambda event, _idx: event.metadata["group"])
    assert result.epsilon == pytest.approx(0.7)   # region-a: 0.5+0.2=0.7；region-b: 0.1 → 取最大
    assert result.delta == pytest.approx(1e-5)    # region-a: 1e-5；region-b: 0 → 取最大


def test_repeated_mechanism_equals_linear_scaling() -> None:
    # 重复机制合成：重复 10 次应等价于线性缩放 10 倍
    result = repeated_mechanism(0.05, 1e-6, repetitions=10)
    assert result.epsilon == pytest.approx(0.5)
    assert result.delta == pytest.approx(1e-5)
