"""
Lightweight privacy reporting utilities for CDP analytics.

Provides dataclasses to capture per-event usage, cumulative budget snapshots,
annotations, and JSON/markdown serialisation helpers.

Responsibilities
  - Define reporting records for events, snapshots, and annotations.
  - Aggregate accountant state into structured privacy reports.
  - Provide JSON/Markdown exports and optional PNG curve rendering.

Usage Context
  - Use with CDPPrivacyAccountant to summarize privacy spend.
  - Intended for downstream reporting or dashboard rendering.

Limitations
  - Report content reflects accountant state at construction time.
  - Rendering relies on matplotlib and does not provide interactive assets.
"""
# 说明：围绕 CDP 分析场景提供轻量级隐私预算使用记录与报告生成工具。
# 职责：
# - 定义事件记录、预算快照与注释等结构化报告数据模型
# - 聚合 CDPPrivacyAccountant/BudgetTracker 输出为可序列化报告
# - 提供 JSON/Markdown 导出与预算曲线 PNG 渲染
from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.privacy import PrivacyGuarantee, PrivacyModel
from dplib.core.privacy.budget_tracker import BudgetTracker
from dplib.core.privacy.privacy_accountant import PrivacyAccountant, PrivacyBudget, PrivacyEvent
from dplib.core.utils.serialization import serialize_to_json
from dplib.core.utils.param_validation import ParamValidationError, ensure_type


@dataclass
class PrivacyUsageRecord:
    # 表示单次隐私事件的使用记录，包括机制、模型、预算和时间戳等元信息
    event_id: str
    name: Optional[str]
    mechanism: Optional[str]
    privacy_model: PrivacyModel
    epsilon: float
    delta: float
    timestamp: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 将使用记录序列化为易于 JSON 导出的字典形式
        return {
            "event_id": self.event_id,
            "name": self.name,
            "mechanism": self.mechanism,
            "privacy_model": self.privacy_model.value,
            "epsilon": float(self.epsilon),
            "delta": float(self.delta),
            "timestamp": None if self.timestamp is None else self.timestamp.isoformat(),
            "tags": dict(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass
class PrivacyBudgetSnapshot:
    # 表示在某个 step 时刻的累计预算使用和剩余预算快照
    step: int
    cumulative_epsilon: float
    cumulative_delta: float
    remaining_epsilon: Optional[float]
    remaining_delta: Optional[float]
    event_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # 将预算快照转换为基础类型字典，便于轨迹导出与可视化
        return {
            "step": int(self.step),
            "cumulative_epsilon": float(self.cumulative_epsilon),
            "cumulative_delta": float(self.cumulative_delta),
            "remaining_epsilon": None if self.remaining_epsilon is None else float(self.remaining_epsilon),
            "remaining_delta": None if self.remaining_delta is None else float(self.remaining_delta),
            "event_id": self.event_id,
        }


@dataclass
class PrivacyAnnotation:
    # 对预算使用情况给出信息、警告或严重级别的注释与诊断提示
    level: str  # info | warning | critical
    message: str
    related_event_ids: Optional[Sequence[str]] = None
    code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # 将注释对象转换为字典，保留等级、信息和关联事件列表
        return {
            "level": self.level,
            "message": self.message,
            "related_event_ids": None if self.related_event_ids is None else list(self.related_event_ids),
            "code": self.code,
        }


@dataclass
class PrivacyReport:
    # 汇总隐私模型、总预算、已用与剩余预算以及事件时间线与注释的综合报告体
    model: PrivacyModel
    total_budget: Optional[PrivacyGuarantee]
    spent: PrivacyGuarantee
    remaining: Optional[PrivacyGuarantee]
    events: List[PrivacyUsageRecord] = field(default_factory=list)
    timeline: List[PrivacyBudgetSnapshot] = field(default_factory=list)
    annotations: List[PrivacyAnnotation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ factories
    # 工厂方法与从会计器构造报告的相关工具
    @classmethod
    def from_accountant(
        cls,
        accountant: CDPPrivacyAccountant,
        *,
        budget_tracker: Optional[BudgetTracker] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "PrivacyReport":
        """Construct a report from an accountant (and optional tracker)."""
        # 基于 CDPPrivacyAccountant（及可选 BudgetTracker）聚合生成隐私报告实例
        if not isinstance(accountant, CDPPrivacyAccountant):
            raise ParamValidationError("accountant must be CDPPrivacyAccountant")
        # 访问底层核心会计器以获取总预算、已用预算和事件序列
        core: PrivacyAccountant = accountant._accountant  # type: ignore[attr-defined]
        total_budget = (
            None
            if core.total_budget is None
            else PrivacyGuarantee(model=PrivacyModel.CDP, epsilon=core.total_budget.epsilon, delta=core.total_budget.delta)
        )
        spent_budget = core.spent
        remaining_budget = core.remaining
        report = cls(
            model=PrivacyModel.CDP,
            total_budget=total_budget,
            spent=PrivacyGuarantee(model=PrivacyModel.CDP, epsilon=spent_budget.epsilon, delta=spent_budget.delta),
            remaining=(
                None
                if remaining_budget is None
                else PrivacyGuarantee(model=PrivacyModel.CDP, epsilon=remaining_budget.epsilon, delta=remaining_budget.delta)
            ),
            metadata=dict(metadata or {}),
        )
        for idx, event in enumerate(core.events):
            record = cls._record_from_event(event, default_event_id=f"evt-{idx+1}")
            report.events.append(record)
        report.compute_timeline()
        report.generate_annotations()
        return report

    @staticmethod
    def _record_from_event(event: PrivacyEvent, default_event_id: str) -> PrivacyUsageRecord:
        # 将底层 PrivacyEvent 转换为带有模型、标签和元数据的 PrivacyUsageRecord
        model = PrivacyModel.from_str(event.model) if event.model else PrivacyModel.CDP
        tags = {}
        metadata = dict(event.metadata or {})
        if "tags" in metadata and isinstance(metadata["tags"], Mapping):
            tags = dict(metadata.pop("tags"))
        event_id = metadata.pop("event_id", default_event_id)
        timestamp = metadata.pop("timestamp", None)
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = None
        return PrivacyUsageRecord(
            event_id=str(event_id),
            name=event.description,
            mechanism=event.mechanism,
            privacy_model=model,
            epsilon=float(event.epsilon),
            delta=float(event.delta),
            timestamp=timestamp,
            tags=tags,
            metadata=metadata,
        )

    # ------------------------------------------------------------------ mutations
    # 报告对象上与事件列表和时间线相关的可变更新操作
    def add_event(self, record: PrivacyUsageRecord) -> None:
        # 向报告中追加一条新的隐私使用记录并保持类型安全
        ensure_type(record, PrivacyUsageRecord)
        self.events.append(record)

    def compute_timeline(self) -> None:
        """Build cumulative epsilon/delta snapshots from events."""
        # 根据事件顺序构建累计 epsilon/delta 以及剩余额度的时间线快照列表
        self.timeline.clear()
        eps = 0.0
        dlt = 0.0
        total = self.total_budget
        remaining_eps = None if total is None or total.epsilon is None else float(total.epsilon)
        remaining_dlt = None if total is None or total.delta is None else float(total.delta)
        for idx, event in enumerate(self.events):
            eps += event.epsilon
            dlt += event.delta
            if remaining_eps is not None:
                remaining_eps = max(remaining_eps - event.epsilon, 0.0)
            if remaining_dlt is not None:
                remaining_dlt = max(remaining_dlt - event.delta, 0.0)
            self.timeline.append(
                PrivacyBudgetSnapshot(
                    step=idx + 1,
                    cumulative_epsilon=eps,
                    cumulative_delta=dlt,
                    remaining_epsilon=remaining_eps,
                    remaining_delta=remaining_dlt,
                    event_id=event.event_id,
                )
            )

    def generate_annotations(
        self,
        *,
        thresholds: Optional[Mapping[str, float]] = None,
    ) -> None:
        """Produce budget usage annotations based on thresholds."""
        # 基于总预算使用比例和阈值配置生成 info/warning/critical 级别的注释
        self.annotations.clear()
        total = self.total_budget
        if total is None or total.epsilon is None:
            return
        eps_total = float(total.epsilon)
        eps_spent = float(self.spent.epsilon or 0.0)
        ratio = eps_spent / eps_total if eps_total > 0 else 0.0
        th = thresholds or {}
        warn_ratio = float(th.get("epsilon_warning_ratio", 0.8))
        critical_ratio = float(th.get("epsilon_critical_ratio", 0.95))
        if ratio >= critical_ratio:
            self.annotations.append(
                PrivacyAnnotation(
                    level="critical",
                    message=f"🔴 Critical: epsilon usage reached {ratio:.2f} of budget",
                    related_event_ids=[e.event_id for e in self.events],
                    code="epsilon_critical",
                )
            )
        elif ratio >= warn_ratio:
            self.annotations.append(
                PrivacyAnnotation(
                    level="warning",
                    message=f"🟠 Warning: epsilon usage reached {ratio:.2f} of budget",
                    related_event_ids=[e.event_id for e in self.events],
                    code="epsilon_warning",
                )
            )
        else:
            self.annotations.append(
                PrivacyAnnotation(
                    level="info",
                    message=f"🔵 Info: epsilon usage at {ratio:.2f} of budget",
                    related_event_ids=[e.event_id for e in self.events],
                    code="epsilon_ok",
                )
            )

    # ------------------------------------------------------------------ exports
    # 导出可用于绘制曲线或序列化报告的数据结构
    def get_epsilon_curve(self) -> Dict[str, Any]:
        # 构造 epsilon 随 step 变化的曲线数据字典，用于绘图或可视化
        x = [snap.step for snap in self.timeline]
        y = [snap.cumulative_epsilon for snap in self.timeline]
        return {"x": x, "y": y, "label": "epsilon", "x_label": "step", "y_label": "cumulative_epsilon"}

    def get_delta_curve(self) -> Dict[str, Any]:
        # 构造 delta 随 step 变化的曲线数据字典，用于绘图或可视化
        x = [snap.step for snap in self.timeline]
        y = [snap.cumulative_delta for snap in self.timeline]
        return {"x": x, "y": y, "label": "delta", "x_label": "step", "y_label": "cumulative_delta"}

    def render_budget_curves_png(
        self,
        path: Union[str, Path],
        *,
        title: str = "Privacy Budget Curves",
        dpi: int = 150,
        figsize: Tuple[float, float] = (10.0, 4.0),
        label_fontsize: int = 10,
        tick_label_fontsize: int = 9,
        y_tick_step: Optional[float] = None,
    ) -> Path:
        """Render epsilon/delta curves into a PNG for reporting."""
        # 使用 get_epsilon_curve / get_delta_curve 的数据绘制折线图
        eps_curve = self.get_epsilon_curve()
        dlt_curve = self.get_delta_curve()

        import sys
        import matplotlib

        if "matplotlib.pyplot" not in sys.modules:
            try:
                matplotlib.use("Agg")
            except Exception:
                pass
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 2, figsize=figsize, sharex=True)
        axes[0].plot(eps_curve["x"], eps_curve["y"], marker="o", markersize=2, color="#4C78A8")
        axes[0].set_title(eps_curve["label"])
        axes[0].set_xlabel(eps_curve["x_label"], fontsize=label_fontsize)
        axes[0].set_ylabel(eps_curve["y_label"], fontsize=label_fontsize)
        axes[0].tick_params(axis="both", labelsize=tick_label_fontsize)

        axes[1].plot(dlt_curve["x"], dlt_curve["y"], marker="o", markersize=2, color="#F58518")
        axes[1].set_title(dlt_curve["label"])
        axes[1].set_xlabel(dlt_curve["x_label"], fontsize=label_fontsize)
        axes[1].set_ylabel(dlt_curve["y_label"], fontsize=label_fontsize)
        axes[1].tick_params(axis="both", labelsize=tick_label_fontsize)

        if y_tick_step is not None:
            from matplotlib.ticker import MultipleLocator

            for ax in axes:
                ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

        fig.suptitle(title)
        fig.tight_layout()
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=dpi)
        plt.close(fig)
        return out_path

    def to_dict(self) -> Dict[str, Any]:
        # 将整个报告对象序列化为嵌套字典结构，便于 JSON 或持久化存储
        return {
            "model": self.model.value,
            "total_budget": None if self.total_budget is None else self.total_budget.to_dict(),
            "spent": self.spent.to_dict(),
            "remaining": None if self.remaining is None else self.remaining.to_dict(),
            "events": [event.to_dict() for event in self.events],
            "timeline": [snap.to_dict() for snap in self.timeline],
            "annotations": [ann.to_dict() for ann in self.annotations],
            "metadata": dict(self.metadata),
        }

    def to_json(self) -> str:
        # 使用统一的 JSON 序列化工具将报告导出为 JSON 字符串
        return serialize_to_json(self.to_dict())

    def to_markdown(self) -> str:
        # 以 Markdown 表格形式导出时间线信息，方便在文档或报告中直接展示
        header = "| step | eps | delta | remaining_eps | remaining_delta |\n| --- | --- | --- | --- | --- |\n"
        rows = []
        for snap in self.timeline:
            rows.append(
                f"| {snap.step} | {snap.cumulative_epsilon:.4f} | {snap.cumulative_delta:.4g} | "
                f"{'' if snap.remaining_epsilon is None else f'{snap.remaining_epsilon:.4f}'} | "
                f"{'' if snap.remaining_delta is None else f'{snap.remaining_delta:.4g}'} |"
            )
        return header + "\n".join(rows)
