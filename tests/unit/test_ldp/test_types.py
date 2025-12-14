"""
Unit tests for the LDP shared report and estimate types.
"""
# 说明：LDPReport 与 Estimate 等本地差分隐私共享类型的行为与互操作性的单元测试。
# 覆盖：
# - 验证 LDPReport 与 Estimate 是否为 dataclass 且字段读写行为符合预期
# - 验证 LDPReport 的 to_dict/from_dict 序列化往返（包括 ndarray 编码场景）的正确性
# - 验证 Estimate.as_numpy 对数组型字段的 numpy 转换以及等值与相等性判断逻辑

from __future__ import annotations

from dataclasses import is_dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pytest

from dplib.ldp.types import Estimate, LDPReport


def test_ldp_report_is_dataclass_and_fields() -> None:
    # 检查 LDPReport 是否为 dataclass 且各核心字段赋值与访问行为正确
    assert is_dataclass(LDPReport)
    ts = datetime(2024, 1, 1, 12, 0, 0)
    report = LDPReport(
        user_id="u1",
        mechanism_id="grr",
        encoded=1,
        epsilon=1.0,
        delta=0.0,
        round_id="r1",
        timestamp=ts,
        metadata={"round": 1},
    )
    assert report.user_id == "u1"
    assert report.mechanism_id == "grr"
    assert report.encoded == 1
    assert report.epsilon == 1.0
    assert report.delta == 0.0
    assert report.round_id == "r1"
    assert report.timestamp == ts
    assert report.metadata["round"] == 1


def test_ldp_report_to_from_dict_round_trip() -> None:
    # 验证 LDPReport 的 to_dict/from_dict 在 list/ndarray 编码场景下保持往返等价
    report = LDPReport(
        user_id=123,
        mechanism_id="oue",
        encoded=[1, 0, 1],
        epsilon=0.8,
        delta=0.0,
        round_id=None,
        timestamp=None,
        metadata={"client": "v1"},
    )
    payload = report.to_dict()
    restored = LDPReport.from_dict(payload)
    # 编码字段在反序列化后可能变为 ndarray，这里按类型区分比较方式确保内容一致
    if isinstance(restored.encoded, np.ndarray):
        assert np.array_equal(restored.encoded, report.encoded)
    else:
        assert restored.encoded == report.encoded
    assert restored.user_id == report.user_id
    assert restored.mechanism_id == report.mechanism_id
    assert restored.epsilon == report.epsilon
    assert restored.delta == report.delta
    assert restored.round_id == report.round_id
    assert dict(restored.metadata) == dict(report.metadata)


def test_ldp_report_equality() -> None:
    # 验证 LDPReport 在编码值相同与不同场景下的相等性和不等性判断
    r1 = LDPReport(user_id="u", mechanism_id="grr", encoded=0, epsilon=1.0, delta=0.0)
    r2 = LDPReport(user_id="u", mechanism_id="grr", encoded=0, epsilon=1.0, delta=0.0)
    r3 = LDPReport(user_id="u", mechanism_id="grr", encoded=1, epsilon=1.0, delta=0.0)
    assert r1 == r2
    assert r1 != r3


def test_estimate_is_dataclass_and_fields() -> None:
    # 检查 Estimate 是否为 dataclass 且频率估计相关字段能正确写入与读取
    assert is_dataclass(Estimate)
    est = Estimate(
        metric="frequency",
        point={"a": 0.6, "b": 0.4},
        variance={"a": 0.01, "b": 0.02},
        confidence_interval={"a": (0.5, 0.7)},
        metadata={"domain": ["a", "b"]},
    )
    assert est.metric == "frequency"
    assert est.point["a"] == 0.6
    assert est.variance["b"] == 0.02
    assert est.confidence_interval["a"] == (0.5, 0.7)
    assert est.metadata["domain"] == ["a", "b"]


def test_estimate_as_numpy() -> None:
    # 验证 Estimate.as_numpy 能将点估计、方差与置信区间转换为 numpy.ndarray 并保持数值一致
    est = Estimate(
        metric="mean",
        point=[1.0, 2.0],
        variance=[0.1, 0.2],
        confidence_interval=[(0.5, 1.5), (1.5, 2.5)],
    )
    converted = est.as_numpy()
    assert isinstance(converted.point, np.ndarray)
    assert isinstance(converted.variance, np.ndarray)
    assert isinstance(converted.confidence_interval, np.ndarray)
    assert np.allclose(converted.point, [1.0, 2.0])


def test_estimate_equality() -> None:
    # 验证 Estimate 在点估计相同与不同情况下的相等性判断逻辑
    e1 = Estimate(metric="mean", point=1.0, variance=0.1, confidence_interval=(0.0, 2.0))
    e2 = Estimate(metric="mean", point=1.0, variance=0.1, confidence_interval=(0.0, 2.0))
    e3 = Estimate(metric="mean", point=2.0, variance=0.1, confidence_interval=(0.0, 2.0))
    assert e1 == e2
    assert e1 != e3
