"""
Shared ML payload types for the CDP ML base layer.

Responsibilities
  - Define batch, metric, and result containers for training and evaluation.
  - Provide JSON-friendly serialization helpers for ML payloads.
  - Normalize privacy summaries for downstream reporting.

Usage Context
  - Used by trainers, evaluators, and backends to exchange structured ML data.

Limitations
  - Serialization is lossy for array-like fields that are converted to lists.
"""
# 说明：CDP ML 基础层共享类型定义，覆盖训练批次、评估结果与隐私摘要等载体。
# 职责：
# - TrainBatch/TrainResult/EvalResult：统一训练与评估过程中的输入输出结构
# - MetricSpec：评估指标规格描述（名称、聚合方式、参数）
# - PrivacySummary：训练/评估过程中的隐私预算汇总载体
# - JSON 友好转换：对 numpy/array 等数组类字段做可序列化处理

from __future__ import annotations

import array
from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any, Dict, Mapping, Optional

import numpy as np


def _jsonify(value: Any) -> Any:
    # 递归将对象转换为 JSON 友好的基础结构，重点处理 ndarray 与 array.array
    if value is None:
        return None
    if is_dataclass(value):
        return {item.name: _jsonify(getattr(value, item.name)) for item in fields(value)}
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _jsonify(value.to_dict())
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, array.array):
        return value.tolist()
    if isinstance(value, Mapping):
        return {key: _jsonify(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(item) for item in value]
    return value


@dataclass
class TrainBatch:
    """
    Container for a single training batch.

    - Configuration
      - features: Input features for the batch.
      - labels: Target labels for the batch.
      - sample_weight: Optional per-sample weights.
      - metadata: Additional batch metadata.

    - Behavior
      - Provides JSON-friendly serialization for array-like fields.

    - Usage Notes
      - Use as the standard input payload between data loaders and trainers.
    """
    # 训练批次载体，统一特征、标签与样本权重等输入格式

    features: Any
    labels: Any
    sample_weight: Optional[Any] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将批次数据转换为 JSON 友好的字典结构
        return {
            "features": _jsonify(self.features),
            "labels": _jsonify(self.labels),
            "sample_weight": _jsonify(self.sample_weight),
            "metadata": _jsonify(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TrainBatch":
        """Create TrainBatch from a dictionary payload."""
        # 从字典载荷还原训练批次对象，保持基础结构不做额外推断
        return cls(
            features=data["features"],
            labels=data["labels"],
            sample_weight=data.get("sample_weight"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MetricSpec:
    """
    Metric specification used for evaluation configuration.

    - Configuration
      - name: Name of the metric.
      - average: Optional averaging strategy for classification metrics.
      - greater_is_better: Whether a higher metric value is better.
      - params: Additional metric parameters.

    - Behavior
      - Provides JSON-friendly serialization of metric parameters.

    - Usage Notes
      - Use to configure evaluation pipelines consistently.
    """
    # 评估指标规格，描述指标名称、聚合方式及参数

    name: str
    average: Optional[str] = None
    greater_is_better: bool = True
    params: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将评估指标规格转换为可 JSON 序列化的字典
        return {
            "name": self.name,
            "average": self.average,
            "greater_is_better": self.greater_is_better,
            "params": _jsonify(self.params),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MetricSpec":
        """Create MetricSpec from a dictionary payload."""
        # 从字典还原指标规格对象，兼容缺省字段
        return cls(
            name=data["name"],
            average=data.get("average"),
            greater_is_better=bool(data.get("greater_is_better", True)),
            params=data.get("params", {}),
        )


@dataclass
class PrivacySummary:
    """
    Summary of privacy budget or accounting outcome.

    - Configuration
      - epsilon: Epsilon value if available.
      - delta: Delta value if available.
      - method: Accounting method or mechanism label.
      - details: Extra accounting details.

    - Behavior
      - Provides JSON-friendly serialization for downstream reporting.

    - Usage Notes
      - Use to attach privacy metadata to training or evaluation results.
    """
    # 隐私预算汇总载体，记录 epsilon/delta 与会计方法等信息

    epsilon: Optional[float] = None
    delta: Optional[float] = None
    method: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将隐私摘要导出为 JSON 友好的字典
        return {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "method": self.method,
            "details": _jsonify(self.details),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PrivacySummary":
        """Create PrivacySummary from a dictionary payload."""
        # 从字典还原隐私摘要对象，兼容缺省字段
        return cls(
            epsilon=data.get("epsilon"),
            delta=data.get("delta"),
            method=data.get("method"),
            details=data.get("details", {}),
        )


@dataclass
class TrainResult:
    """
    Result container emitted by training loops.

    - Configuration
      - model_ref: Optional backend-specific model handle.
      - history: Training history such as loss curves.
      - metrics: Final training metrics.
      - privacy: Optional privacy summary.
      - artifacts: Artifacts such as checkpoints or plots.
      - metadata: Additional metadata for auditing.

    - Behavior
      - Serializes nested dataclasses and array-like fields into JSON-friendly forms.

    - Usage Notes
      - Use as the standard output for training routines.
    """
    # 训练结果载体，统一输出模型引用、历史记录、指标与隐私摘要

    model_ref: Optional[Any] = None
    history: Mapping[str, Any] = field(default_factory=dict)
    metrics: Mapping[str, Any] = field(default_factory=dict)
    privacy: Optional[PrivacySummary] = None
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将训练结果转换为 JSON 友好的字典结构
        return {
            "model_ref": _jsonify(self.model_ref),
            "history": _jsonify(self.history),
            "metrics": _jsonify(self.metrics),
            "privacy": _jsonify(self.privacy) if self.privacy is not None else None,
            "artifacts": _jsonify(self.artifacts),
            "metadata": _jsonify(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TrainResult":
        """Create TrainResult from a dictionary payload."""
        # 从字典还原训练结果对象，并在需要时恢复隐私摘要结构
        privacy_payload = data.get("privacy")
        if isinstance(privacy_payload, PrivacySummary):
            privacy = privacy_payload
        elif isinstance(privacy_payload, Mapping):
            privacy = PrivacySummary.from_dict(privacy_payload)
        else:
            privacy = None
        return cls(
            model_ref=data.get("model_ref"),
            history=data.get("history", {}),
            metrics=data.get("metrics", {}),
            privacy=privacy,
            artifacts=data.get("artifacts", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EvalResult:
    """
    Evaluation result container with optional granular metrics.

    - Configuration
      - metrics: Overall evaluation metrics.
      - per_split: Metrics per data split (train/val/test).
      - per_class: Metrics per class label.
      - n_samples: Sample counts per split or subset.
      - metadata: Additional metadata for auditing.

    - Behavior
      - Provides JSON-friendly serialization of nested metrics.

    - Usage Notes
      - Use for evaluation outputs and reporting.
    """
    # 评估结果载体，支持按数据划分或类别输出的指标

    metrics: Mapping[str, Any] = field(default_factory=dict)
    per_split: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    per_class: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    n_samples: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export to a JSON-friendly dictionary."""
        # 将评估结果导出为 JSON 友好的字典结构
        return {
            "metrics": _jsonify(self.metrics),
            "per_split": _jsonify(self.per_split),
            "per_class": _jsonify(self.per_class),
            "n_samples": _jsonify(self.n_samples),
            "metadata": _jsonify(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EvalResult":
        """Create EvalResult from a dictionary payload."""
        # 从字典还原评估结果对象，兼容缺省字段
        return cls(
            metrics=data.get("metrics", {}),
            per_split=data.get("per_split", {}),
            per_class=data.get("per_class", {}),
            n_samples=data.get("n_samples", {}),
            metadata=data.get("metadata", {}),
        )
