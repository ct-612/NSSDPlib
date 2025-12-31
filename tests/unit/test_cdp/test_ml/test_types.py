"""
Unit tests for CDP ML type containers.
"""
# 说明：CDP ML 类型容器的单元测试，覆盖序列化与默认值行为。
# 覆盖：
# - TrainBatch 的 numpy 输入与 JSON 友好转换
# - TrainResult 的隐私摘要与数组字段序列化
# - MetricSpec 与 EvalResult 的默认值与往返

from __future__ import annotations

from dataclasses import is_dataclass

import numpy as np
import pytest

from dplib.cdp.ml.types import EvalResult, MetricSpec, PrivacySummary, TrainBatch, TrainResult


def test_train_batch_numpy_round_trip() -> None:
    # 验证 TrainBatch 对 numpy 输入的 JSON 友好转换与往返行为
    batch = TrainBatch(
        features=np.array([[1.0, 2.0], [3.0, 4.0]]),
        labels=np.array([0, 1]),
        sample_weight=None,
    )
    assert is_dataclass(TrainBatch)
    payload = batch.to_dict()
    assert isinstance(payload["features"], list)
    assert isinstance(payload["labels"], list)
    restored = TrainBatch.from_dict(payload)
    assert restored.features == payload["features"]
    assert restored.labels == payload["labels"]
    assert restored.sample_weight is None
    assert restored.metadata == {}


def test_train_result_round_trip_with_privacy() -> None:
    # 验证 TrainResult 对隐私摘要与数组指标的序列化与还原行为
    result = TrainResult(
        model_ref="model-v1",
        history={"loss": [1.0, 0.5]},
        metrics={"accuracy": np.array([0.75])},
        privacy=PrivacySummary(epsilon=1.0, delta=1e-5, method="rdp"),
        artifacts={"weights": np.array([1.0, 2.0])},
        metadata={"run_id": "r1"},
    )
    payload = result.to_dict()
    assert payload["metrics"]["accuracy"] == [0.75]
    restored = TrainResult.from_dict(payload)
    assert isinstance(restored.privacy, PrivacySummary)
    assert restored.privacy.epsilon == pytest.approx(1.0)
    assert restored.metrics["accuracy"] == [0.75]


def test_metric_spec_and_eval_result_defaults() -> None:
    # 验证指标规格与评估结果的默认值与往返行为
    spec = MetricSpec(name="accuracy")
    assert is_dataclass(MetricSpec)
    payload = spec.to_dict()
    restored_spec = MetricSpec.from_dict(payload)
    assert restored_spec.greater_is_better is True
    assert restored_spec.params == {}

    result = EvalResult(metrics={"accuracy": 0.9})
    assert is_dataclass(EvalResult)
    result_payload = result.to_dict()
    restored_result = EvalResult.from_dict(result_payload)
    assert restored_result.metrics["accuracy"] == 0.9
    assert restored_result.per_split == {}
    assert restored_result.per_class == {}
    assert restored_result.n_samples == {}
