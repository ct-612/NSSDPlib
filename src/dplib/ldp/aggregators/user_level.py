"""User-level wrapper to group reports per user and merge per-user estimates."""
# 说明：在服务端按 user_id 维度对 LDP 报告做用户级聚合并将各用户估计结果合并为全局估计。
# 职责：
# - 将同一用户的多轮或多维 LDPReport 分组交给内部聚合器生成 per-user 级别 Estimate
# - 支持配置匿名用户的分组策略以及按用户数量或报告数量进行加权合并
# - 通过可插拔 reducer 与权重模式灵活控制不同用户估计结果的合并方式

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional, Sequence

import numpy as np

from .base import BaseAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


class UserLevelAggregator(BaseAggregator):
    """Group reports by user_id, aggregate per-user with an inner aggregator, then merge."""

    def __init__(
        self,
        inner_aggregator: BaseAggregator,
        *,
        reducer: Optional[Callable[[Sequence[Any]], Any]] = None,
        anonymous_strategy: str = "group",
        weight_mode: str = "equal",
    ):
        """
        Args:
            inner_aggregator: Aggregator applied to each user's reports.
            reducer: Custom reducer to merge per-user Estimate.point; defaults to mean.
            anonymous_strategy: Handling for reports with user_id=None:
                - "group": treat all as a single anonymous user (default)
                - "separate": each anonymous report forms its own user
                - "drop": discard anonymous reports
            weight_mode: "equal" (default) or "report_count" to weight by number of reports per user.
        """
        # 初始化用户级聚合器，记录内部聚合器实例、匿名用户处理策略以及跨用户合并的权重模式和自定义 reducer
        self.inner_aggregator = inner_aggregator
        self.reducer = reducer
        if anonymous_strategy not in {"group", "separate", "drop"}:
            raise ParamValidationError("anonymous_strategy must be 'group', 'separate', or 'drop'")
        self.anonymous_strategy = anonymous_strategy
        if weight_mode not in {"equal", "report_count"}:
            raise ParamValidationError("weight_mode must be 'equal' or 'report_count'")
        self.weight_mode = weight_mode

    def _compute_weights(self, grouped: Dict[Any, list[LDPReport]]) -> Optional[np.ndarray]:
        # 根据 weight_mode 选择是否按报告数量生成用户级权重向量并做归一化
        if self.weight_mode == "equal":
            return None
        if self.weight_mode == "report_count":
            weights = np.array([len(reports) for reports in grouped.values()], dtype=float)
            total = weights.sum()
            return weights / total if total > 0 else None
        return None

    def _combine_points(self, points: Sequence[Any], weights: Optional[np.ndarray] = None) -> Any:
        # 按数值或数组类型对 per-user 点估计做均值或加权均值合并，无法统一处理时退化为返回首个估计
        if len(points) == 0:
            raise ParamValidationError("no points to combine")
        if self.reducer is not None:
            return self.reducer(points)

        if all(isinstance(p, (int, float, np.number)) for p in points):
            if weights is not None and len(weights) == len(points):
                return float(np.average(points, weights=weights))
            return float(np.mean(points))

        try:
            arrays = [np.asarray(p) for p in points]
            shapes = {arr.shape for arr in arrays}
            if len(shapes) == 1:
                if weights is not None and len(weights) == len(arrays):
                    stacked = np.stack(arrays, axis=0)
                    total = float(np.sum(weights))
                    if total > 0:
                        return np.average(stacked, axis=0, weights=weights)
                    return np.mean(stacked, axis=0)
                return np.mean(np.stack(arrays, axis=0), axis=0)
        except Exception:
            pass

        # 兜底：直接返回首个 point，留给上层自行后处理
        return points[0]

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 按照 user_id 将报告分组处理匿名用户策略后，对每个用户调用内部聚合器，再合并各用户估计
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        grouped: Dict[Any, list[LDPReport]] = {}
        for report in reports:
            if report.user_id is None:
                if self.anonymous_strategy == "drop":
                    continue
                if self.anonymous_strategy == "separate":
                    uid = f"__anon__{len(grouped)}_{len(reports)}"
                else:
                    uid = "__anonymous__"
            else:
                uid = report.user_id
            grouped.setdefault(uid, []).append(report)

        user_estimates = []
        for uid, user_reports in grouped.items():
            est = self.inner_aggregator.aggregate(user_reports)
            user_estimates.append(est)

        weights = self._compute_weights(grouped)
        combined_point = self._combine_points([est.point for est in user_estimates], weights=weights)
        numeric_variances = [
            float(est.variance) for est in user_estimates if isinstance(est.variance, (int, float, np.number))
        ]
        if numeric_variances:
            if weights is not None and len(weights) == len(numeric_variances):
                combined_variance = float(np.average(numeric_variances, weights=weights[: len(numeric_variances)]))
            else:
                combined_variance = float(np.mean(numeric_variances))
        else:
            combined_variance = None

        metadata: Mapping[str, Any] = {
            "user_level": True,
            "num_users": len(grouped),
            "n_reports": len(reports),
            "inner_metric": user_estimates[0].metric if user_estimates else None,
            "anonymous_strategy": self.anonymous_strategy,
            "weight_mode": self.weight_mode,
        }

        return Estimate(
            metric=user_estimates[0].metric if user_estimates else "unknown",
            point=combined_point,
            variance=combined_variance,
            confidence_interval=None,
            metadata=metadata,
        )

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回用户级聚合器的类型名称、内部聚合器标识以及匿名策略和加权模式等配置元信息
        return {
            "type": "user_level",
            "inner_aggregator": self.inner_aggregator.__class__.__name__,
            "anonymous_strategy": self.anonymous_strategy,
            "weight_mode": self.weight_mode,
        }

    def reset(self) -> None:
        # 将重置调用透传给内部聚合器，自身不维护其他持久状态
        self.inner_aggregator.reset()
        return None
