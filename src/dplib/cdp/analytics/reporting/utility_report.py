"""
Utility reporting for DP query outputs.

Aggregates error metrics over multiple noisy outputs and exposes curve-friendly
structures for downstream visualisation or notebooks.

Responsibilities
  - Aggregate error metrics across multiple noisy outputs.
  - Define report and curve structures for utility summaries.
  - Provide JSON and Markdown export helpers for reporting.

Usage Context
  - Use to evaluate utility across runs or mechanisms.
  - Intended for notebooks, dashboards, or reporting pipelines.

Limitations
  - Assumes numeric inputs for error metric computation.
  - Reports are derived from provided samples and do not resample.
"""
# 说明：针对差分隐私查询结果的效用评估与报告工具，聚合误差指标并生成可视化友好的结构。
# 职责：
# - 描述 DP 查询误差评估所需的核心指标与记录结构
# - 对多次噪声输出进行误差统计聚合并生成全局与按查询的摘要
# - 提供误差随 epsilon 变化的曲线数据以及 JSON/Markdown 导出接口

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

from dplib.core.utils.param_validation import ensure, ensure_type
from dplib.core.utils.serialization import serialize_to_json


@dataclass
class ErrorMetrics:
    # 汇总单个查询或一组样本上的误差统计指标，用于评估 DP 机制效用
    mse: float      # 均方误差（Mean Squared Error）
    mae: float      # 平均绝对误差（Mean Absolute Error）
    rmse: float         # 均方根误差（Root Mean Squared Error）
    bias: float         # 偏差（Bias）
    variance: float         # 方差（Variance）
    max_error: Optional[float]  # 最大绝对误差（Max Absolute Error）
    n_samples: int
    metric_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 将误差指标转换为基础类型字典，便于序列化与下游消费
        return {
            "mse": float(self.mse),
            "mae": float(self.mae),
            "rmse": float(self.rmse),
            "bias": float(self.bias),
            "variance": float(self.variance),
            "max_error": None if self.max_error is None else float(self.max_error),
            "n_samples": int(self.n_samples),
            "metric_details": dict(self.metric_details),
        }


@dataclass
class QueryUtilityRecord:
    # 表示一次查询在特定机制和隐私参数下的真值、噪声输出与误差指标记录
    query_id: str
    mechanism: str
    epsilon: float
    delta: float
    true_value: Any
    noisy_values: Sequence[Any]
    error_metrics: ErrorMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 将查询效用记录展开为字典结构，包含误差指标和原始样本信息
        return {
            "query_id": self.query_id,
            "mechanism": self.mechanism,
            "epsilon": float(self.epsilon),
            "delta": float(self.delta),
            "true_value": self.true_value,
            "noisy_values": list(self.noisy_values),
            "error_metrics": self.error_metrics.to_dict(),
            "metadata": dict(self.metadata),
        }


@dataclass
class UtilityCurve:
    # 为绘图或可视化准备的一维曲线数据结构，支持分组与标签
    x: Sequence[float]
    y: Sequence[float]
    x_label: str
    y_label: str
    label: str
    group: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # 将曲线数据转换为字典，以兼容通用绘图库或前端展示
        return {
            "x": list(self.x),
            "y": list(self.y),
            "x_label": self.x_label,
            "y_label": self.y_label,
            "label": self.label,
            "group": self.group,
        }


@dataclass
class UtilityReport:
    # 效用评估报告主体，包含原始记录、全局与按查询聚合的误差统计信息
    records: List[QueryUtilityRecord] = field(default_factory=list)
    global_summary: Optional[ErrorMetrics] = None
    per_query_summary: Dict[str, ErrorMetrics] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ factories
    # 工厂方法相关工具，用于从原始样本集合构建 UtilityReport
    @staticmethod
    def compute_error_metrics(true_values: Any, noisy_values: Any) -> ErrorMetrics:
        # 基于真值和噪声输出计算 MSE/MAE/RMSE/bias/variance 等误差指标
        truth = np.asarray(true_values, dtype=float)
        noisy = np.asarray(noisy_values, dtype=float)
        ensure(truth.shape == noisy.shape or noisy.ndim >= truth.ndim, "shape mismatch between true and noisy values")
        diff = noisy - truth
        mse = float(np.mean(diff ** 2))
        mae = float(np.mean(np.abs(diff)))
        rmse = float(math.sqrt(mse))
        bias = float(np.mean(diff))
        variance = float(np.var(diff))
        max_error = float(np.max(np.abs(diff))) if diff.size else None
        return ErrorMetrics(
            mse=mse,
            mae=mae,
            rmse=rmse,
            bias=bias,
            variance=variance,
            max_error=max_error,
            n_samples=int(diff.size if diff.size else len(noisy_values)),
            metric_details={},
        )

    @classmethod
    def from_samples(
        cls,
        samples: Sequence[Mapping[str, Any]],
        *,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "UtilityReport":
        # 从包含 query_id/true_value/noisy_values 等键的样本字典序列构建完整效用报告
        report = cls(metadata=dict(metadata or {}))
        for item in samples:
            query_id = str(item["query_id"])
            mechanism = str(item.get("mechanism") or "")
            epsilon = float(item.get("epsilon", 0.0))
            delta = float(item.get("delta", 0.0))
            true_value = item["true_value"]
            noisy_values = item["noisy_values"]
            metrics = cls.compute_error_metrics(true_value, noisy_values)
            record = QueryUtilityRecord(
                query_id=query_id,
                mechanism=mechanism,
                epsilon=epsilon,
                delta=delta,
                true_value=true_value,
                noisy_values=noisy_values,
                error_metrics=metrics,
                metadata=dict(item.get("metadata") or {}),
            )
            report.records.append(record)
        report.compute_per_query_summary()
        report.compute_global_summary()
        return report

    # ------------------------------------------------------------------ mutations
    # 报告对象上与记录集合相关的可变操作
    def add_record(self, record: QueryUtilityRecord) -> None:
        # 向报告中追加一条查询效用记录并进行类型检查
        ensure_type(record, QueryUtilityRecord)
        self.records.append(record)

    # ------------------------------------------------------------------ summaries
    # 生成全局与按查询聚合的误差摘要统计
    def compute_global_summary(self) -> ErrorMetrics:
        # 对全部记录按样本数加权聚合误差指标，得到全局效用概览
        ensure(len(self.records) > 0, "no records to summarise")
        totals = {"mse": 0.0, "mae": 0.0, "rmse": 0.0, "bias": 0.0, "variance": 0.0}
        total_weight = 0
        for record in self.records:
            # 使用样本数作为权重对各查询的误差指标做加权平均
            weight = max(record.error_metrics.n_samples, 1)
            total_weight += weight
            totals["mse"] += record.error_metrics.mse * weight
            totals["mae"] += record.error_metrics.mae * weight
            totals["rmse"] += record.error_metrics.rmse * weight
            totals["bias"] += record.error_metrics.bias * weight
            totals["variance"] += record.error_metrics.variance * weight
        averaged = {k: v / total_weight for k, v in totals.items()}
        max_error = max((rec.error_metrics.max_error or 0.0) for rec in self.records)
        self.global_summary = ErrorMetrics(
            mse=averaged["mse"],
            mae=averaged["mae"],
            rmse=averaged["rmse"],
            bias=averaged["bias"],
            variance=averaged["variance"],
            max_error=max_error,
            n_samples=total_weight,
            metric_details={},
        )
        return self.global_summary

    def compute_per_query_summary(self) -> Dict[str, ErrorMetrics]:
        # 按 query_id 对记录分组并分别做加权平均，得到每个查询的误差概览
        summary: Dict[str, ErrorMetrics] = {}
        grouped: Dict[str, List[QueryUtilityRecord]] = {}
        for rec in self.records:
            grouped.setdefault(rec.query_id, []).append(rec)
        for query_id, items in grouped.items():
            totals = {"mse": 0.0, "mae": 0.0, "rmse": 0.0, "bias": 0.0, "variance": 0.0}
            total_weight = 0
            max_error = 0.0
            for rec in items:
                weight = max(rec.error_metrics.n_samples, 1)
                total_weight += weight
                totals["mse"] += rec.error_metrics.mse * weight
                totals["mae"] += rec.error_metrics.mae * weight
                totals["rmse"] += rec.error_metrics.rmse * weight
                totals["bias"] += rec.error_metrics.bias * weight
                totals["variance"] += rec.error_metrics.variance * weight
                if rec.error_metrics.max_error is not None:
                    max_error = max(max_error, rec.error_metrics.max_error)
            averaged = {k: v / total_weight for k, v in totals.items()}
            summary[query_id] = ErrorMetrics(
                mse=averaged["mse"],
                mae=averaged["mae"],
                rmse=averaged["rmse"],
                bias=averaged["bias"],
                variance=averaged["variance"],
                max_error=max_error,
                n_samples=total_weight,
                metric_details={},
            )
        self.per_query_summary = summary
        return self.per_query_summary

    # ------------------------------------------------------------------ curves
    # 生成适合绘图的 (误差-ε) 曲线数据 或 (偏差/方差-ε) 对比曲线数据
    def get_error_vs_epsilon(
        self,
        metric: str = "mse",
        *,
        query_id: Optional[str] = None,
        mechanism: Optional[str] = None,
    ) -> List[UtilityCurve]:
        # 构造给定误差指标随 epsilon 变化的曲线，可按查询或机制进行过滤
        filtered = [
            rec
            for rec in self.records
            if (query_id is None or rec.query_id == query_id)
            and (mechanism is None or rec.mechanism == mechanism)
        ]
        if not filtered:
            return []
        filtered.sort(key=lambda r: r.epsilon)
        x = [rec.epsilon for rec in filtered]
        y = [getattr(rec.error_metrics, metric) for rec in filtered]
        label_parts = [metric]
        if query_id:
            label_parts.append(f"query={query_id}")
        if mechanism:
            label_parts.append(f"mechanism={mechanism}")
        label = ", ".join(label_parts)
        return [
            UtilityCurve(
                x=x,
                y=y,
                x_label="epsilon",
                y_label=metric,
                label=label,
                group=query_id or mechanism,
            )
        ]

    def get_bias_variance_tradeoff(self, *, query_id: str) -> List[UtilityCurve]:
        # 针对单个查询生成偏差与方差随 epsilon 变化的两条对比曲线
        curves: List[UtilityCurve] = []
        subset = [rec for rec in self.records if rec.query_id == query_id]
        if not subset:
            return curves
        subset.sort(key=lambda r: r.epsilon)
        epsilons = [rec.epsilon for rec in subset]
        biases = [rec.error_metrics.bias for rec in subset]
        variances = [rec.error_metrics.variance for rec in subset]
        curves.append(
            UtilityCurve(
                x=epsilons,
                y=biases,
                x_label="epsilon",
                y_label="bias",
                label=f"bias (query={query_id})",
                group=query_id,
            )
        )
        curves.append(
            UtilityCurve(
                x=epsilons,
                y=variances,
                x_label="epsilon",
                y_label="variance",
                label=f"variance (query={query_id})",
                group=query_id,
            )
        )
        return curves

    # ------------------------------------------------------------------ exports
    # 将报告导出为字典、JSON 或 Markdown 表格，方便日志记录与文档展示
    def to_dict(self) -> Dict[str, Any]:
        # 汇总所有记录与摘要信息为嵌套字典结构
        return {
            "records": [rec.to_dict() for rec in self.records],
            "global_summary": None if self.global_summary is None else self.global_summary.to_dict(),
            "per_query_summary": {k: v.to_dict() for k, v in self.per_query_summary.items()},
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        # 使用统一序列化工具将报告转换为 JSON 字符串
        return serialize_to_json(self.to_dict())

    def to_markdown(self) -> str:
        # 以 Markdown 表格形式导出每条查询的误差指标，便于在文档或报告中展示
        header = "| query | mechanism | epsilon | mse | mae | rmse | bias | variance |\n"
        header += "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        rows = []
        for rec in self.records:
            m = rec.error_metrics
            rows.append(
                f"| {rec.query_id} | {rec.mechanism} | {rec.epsilon:.3f} | "
                f"{m.mse:.4f} | {m.mae:.4f} | {m.rmse:.4f} | {m.bias:.4f} | {m.variance:.4f} |"
            )
        return header + "\n".join(rows)
