"""
Utility reporting for DP query outputs.

Aggregates error metrics over noisy outputs, provides curve data, and can render
summary charts for reports.

Responsibilities
  - Aggregate error metrics and per-query summaries from DP samples.
  - Provide utility curve data and PNG rendering helpers.
  - Export report data to JSON and Markdown.

Usage Context
  - Use to compare utility across epsilon settings, queries, or mechanisms.
  - Intended for notebooks, dashboards, and reporting pipelines.

Limitations
  - Assumes numeric inputs for error metric computation.
  - Reports are derived from provided samples and do not resample.
  - Rendering relies on matplotlib for PNG output.
"""
# 说明：面向差分隐私查询效用评估与报告输出，聚合误差指标并支持曲线渲染。
# 职责：
# - 定义误差/记录/曲线/报告数据结构并汇总样本统计
# - 提供按 epsilon 的误差曲线与偏差/方差对比曲线 PNG 输出
# - 提供 JSON/Markdown 导出与查询级汇总

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

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

    # ------------------------------------------------------------------ charts
    # 使用曲线数据绘制 PNG，便于在报告中比较误差趋势
    def render_error_vs_epsilon_png(
        self,
        path: Union[str, Path],
        *,
        metric: str = "mse",
        query_id: Optional[str] = None,
        mechanism: Optional[str] = None,
        title: Optional[str] = None,
        dpi: int = 150,
        figsize: Tuple[float, float] = (8.0, 4.0),
        label_fontsize: int = 10,
        tick_label_fontsize: int = 9,
        y_tick_step: Optional[float] = None,
    ) -> Path:
        """Render error-vs-epsilon curves into a PNG file."""
        # 依据指定误差指标绘制随 epsilon 变化的曲线图，支持按查询或机制过滤
        # 从统计曲线接口获取数据并进行基础校验
        curves = self.get_error_vs_epsilon(metric, query_id=query_id, mechanism=mechanism)
        ensure(len(curves) > 0, "no error curves available to render")

        # 延迟导入 matplotlib，没有显示环境时使用 Agg 后端
        import sys
        import matplotlib

        if "matplotlib.pyplot" not in sys.modules:
            try:
                matplotlib.use("Agg")
            except Exception:
                pass
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)
        for curve in curves:
            ax.plot(curve.x, curve.y, marker="o", markersize=2, label=curve.label)
        ax.set_xlabel(curves[0].x_label, fontsize=label_fontsize)
        ax.set_ylabel(curves[0].y_label, fontsize=label_fontsize)
        ax.set_title(title or f"{metric} vs epsilon")
        if len(curves) > 1:
            ax.legend()
        ax.tick_params(axis="both", labelsize=tick_label_fontsize)
        if y_tick_step is not None:
            from matplotlib.ticker import MultipleLocator

            ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

        # 输出路径由调用方控制，确保目录存在
        fig.tight_layout()
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

    def render_metrics_vs_epsilon_png(
        self,
        path: Union[str, Path],
        *,
        query_id: str,
        mechanism: Optional[str] = None,
        metrics: Optional[Sequence[str]] = None,
        title: Optional[str] = None,
        normalize: bool = True,
        dpi: int = 150,
        figsize: Tuple[float, float] = (9.0, 4.5),
        label_fontsize: int = 10,
        tick_label_fontsize: int = 9,
        y_tick_step: Optional[float] = None,
    ) -> Path:
        """Render multiple error metrics vs epsilon in a single PNG chart.

        When normalize=True, each metric is scaled by its max absolute value to keep lines visible.
        """
        # 组织要绘制的指标列表并逐项构造误差曲线
        metric_list = metrics or ("mse", "mae", "rmse", "bias", "variance")
        ensure(len(metric_list) > 0, "metrics must be non-empty")
        curves: List[Tuple[str, UtilityCurve]] = []
        for metric in metric_list:
            metric_curves = self.get_error_vs_epsilon(metric, query_id=query_id, mechanism=mechanism)
            if metric_curves:
                curves.append((metric, metric_curves[0]))
        ensure(len(curves) > 0, "no metric curves available to render")

        plot_curves: List[Tuple[str, str, Sequence[float], Sequence[float]]] = []
        for metric, curve in curves:
            if normalize:
                # 归一化到自身量级，避免尺度差导致曲线不可见
                values = np.asarray(curve.y, dtype=float)
                scale = float(np.max(np.abs(values))) if values.size else 0.0
                scaled = values if scale <= 0 else values / scale
                plot_curves.append((metric, f"{metric} (norm)", curve.x, scaled.tolist()))
            else:
                plot_curves.append((metric, metric, curve.x, list(curve.y)))

        # 延迟导入 matplotlib，避免可选依赖在模块加载期报错
        import sys
        import matplotlib

        if "matplotlib.pyplot" not in sys.modules:
            try:
                matplotlib.use("Agg")
            except Exception:
                pass
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)
        plotted = []
        for label_text, legend_label, x_vals, y_vals in plot_curves:
            line = ax.plot(x_vals, y_vals, marker="o", markersize=2, label=legend_label)[0]
            plotted.append((label_text, line, x_vals, y_vals))
        ax.set_xlabel(curves[0][1].x_label, fontsize=label_fontsize)
        ax.set_ylabel("normalized metric" if normalize else "metric", fontsize=label_fontsize)
        chart_title = title or f"metrics vs epsilon (query={query_id})"
        ax.set_title(chart_title)
        ax.legend()
        ax.tick_params(axis="both", labelsize=tick_label_fontsize)
        if normalize:
            ax.axhline(0.0, color="#666666", linestyle="--", linewidth=0.8, alpha=0.6)
        if y_tick_step is not None:
            from matplotlib.ticker import MultipleLocator

            ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

        # 在折线末端标注指标名称，减少图例遮挡导致的误判
        for idx, (label_text, line, x_vals, y_vals) in enumerate(plotted):
            if not x_vals:
                continue
            y_offset = (idx % 3 - 1) * 6
            ax.annotate(
                label_text,
                (x_vals[-1], y_vals[-1]),
                xytext=(4, y_offset),
                textcoords="offset points",
                color=line.get_color(),
                fontsize=8,
                ha="left",
                va="center",
            )

        # 保存 PNG 并关闭资源，避免绘图句柄泄漏
        fig.tight_layout()
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

    def render_metrics_vs_epsilon_grid_png(
        self,
        path: Union[str, Path],
        *,
        query_ids: Sequence[str],
        mechanism: Optional[str] = None,
        metrics: Optional[Sequence[str]] = None,
        title: Optional[str] = None,
        normalize: bool = True,
        dpi: int = 150,
        figsize: Optional[Tuple[float, float]] = None,
        label_fontsize: int = 9,
        tick_label_fontsize: int = 8,
        y_tick_step: Optional[float] = None,
    ) -> Path:
        """Render multiple query charts into a single PNG."""
        # 为多个查询绘制误差指标随 epsilon 变化的子图网格，便于横向对比
        ensure(len(query_ids) > 0, "query_ids must be non-empty")
        metric_list = metrics or ("mse", "mae", "rmse", "bias", "variance")
        ensure(len(metric_list) > 0, "metrics must be non-empty")

        import sys
        import matplotlib

        if "matplotlib.pyplot" not in sys.modules:
            try:
                matplotlib.use("Agg")
            except Exception:
                pass
        import matplotlib.pyplot as plt

        nrows = len(query_ids)
        if figsize is None:
            figsize = (9.0, 3.6 * nrows)
        fig, axes = plt.subplots(nrows=nrows, ncols=1, figsize=figsize, sharex=True)
        if nrows == 1:
            axes = [axes]

        for ax, query_id in zip(axes, query_ids):
            plot_curves: List[Tuple[str, Sequence[float], Sequence[float]]] = []
            for metric in metric_list:
                metric_curves = self.get_error_vs_epsilon(metric, query_id=query_id, mechanism=mechanism)
                if not metric_curves:
                    continue
                curve = metric_curves[0]
                y_vals = np.asarray(curve.y, dtype=float)
                if normalize:
                    scale = float(np.max(np.abs(y_vals))) if y_vals.size else 0.0
                    if scale > 0:
                        y_vals = y_vals / scale
                plot_curves.append((metric, list(curve.x), y_vals.tolist()))
            ensure(len(plot_curves) > 0, f"no metric curves available for query_id={query_id}")

            plotted = []
            for metric, x_vals, y_vals in plot_curves:
                legend = f"{metric} (norm)" if normalize else metric
                line = ax.plot(x_vals, y_vals, marker="o", markersize=2, label=legend)[0]
                plotted.append((metric, line, x_vals, y_vals))
            ax.set_ylabel("normalized metric" if normalize else "metric", fontsize=label_fontsize)
            ax.set_title(f"query={query_id}", fontsize=label_fontsize)
            ax.legend(fontsize=max(label_fontsize - 1, 7))
            ax.tick_params(axis="both", labelsize=tick_label_fontsize)
            if normalize:
                ax.axhline(0.0, color="#666666", linestyle="--", linewidth=0.8, alpha=0.6)
            if y_tick_step is not None:
                from matplotlib.ticker import MultipleLocator

                ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

            for idx, (metric, line, x_vals, y_vals) in enumerate(plotted):
                if not x_vals:
                    continue
                y_offset = (idx % 3 - 1) * 6
                ax.annotate(
                    metric,
                    (x_vals[-1], y_vals[-1]),
                    xytext=(4, y_offset),
                    textcoords="offset points",
                    color=line.get_color(),
                    fontsize=8,
                    ha="left",
                    va="center",
                )

        axes[-1].set_xlabel("epsilon", fontsize=label_fontsize)
        if title:
            fig.suptitle(title, fontsize=label_fontsize + 1)
        fig.tight_layout()
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

    def render_bias_variance_tradeoff_png(
        self,
        query_id: str,
        path: Union[str, Path],
        *,
        title: Optional[str] = None,
        dpi: int = 150,
        figsize: Tuple[float, float] = (8.0, 4.0),
        label_fontsize: int = 10,
        tick_label_fontsize: int = 9,
        y_tick_step: Optional[float] = None,
    ) -> Path:
        """Render bias/variance tradeoff curves into a PNG file."""
        # 基于 bias/variance 曲线绘制比较线，直观展示机制权衡
        curves = self.get_bias_variance_tradeoff(query_id=query_id)
        ensure(len(curves) > 0, "no bias/variance curves available to render")

        # 延迟导入 matplotlib，避免可选依赖在模块加载期报错
        import sys
        import matplotlib

        if "matplotlib.pyplot" not in sys.modules:
            try:
                matplotlib.use("Agg")
            except Exception:
                pass
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=figsize)
        for curve in curves:
            ax.plot(curve.x, curve.y, marker="o", markersize=2, label=curve.label)
        ax.set_xlabel(curves[0].x_label, fontsize=label_fontsize)
        ax.set_ylabel("metric", fontsize=label_fontsize)
        ax.set_title(title or f"bias/variance vs epsilon ({query_id})")
        ax.legend()
        ax.tick_params(axis="both", labelsize=tick_label_fontsize)
        if y_tick_step is not None:
            from matplotlib.ticker import MultipleLocator

            ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

        # 保存 PNG 并关闭资源，避免绘图句柄泄漏
        fig.tight_layout()
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

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
