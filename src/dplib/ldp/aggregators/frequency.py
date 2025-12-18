"""
Frequency estimation aggregator for categorical LDP mechanisms.

Server-side estimator to recover category frequencies from LDP reports:
    - GRR: integer indices with closed-form p/q debiasing, then non-negativity and normalisation.
    - Bit vectors: debias per-bit when p/q are provided (OUE defaults supported), 
      otherwise return per-bit mean as an approximation (no exact RAPPOR/OLH debiasing yet).
"""
# 说明：为多种本地差分隐私机制提供统一的类别频率估计聚合器，支持 GRR 与基于比特向量的编码。
# 职责：
# - 根据 LDPReport 中的编码与元数据推断类别数和机制参数并进行 GRR 闭式去偏估计
# - 对 OUE 等比特向量机制在 p/q 可用时执行逐位去偏，否则退化为简单均值近似
# - 在元数据中记录使用的参数与近似策略便于上层分析和调试行为

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np

from .base import StatelessAggregator
from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import Estimate, LDPReport


class FrequencyAggregator(StatelessAggregator):
    """
    Aggregate categorical LDP reports into frequency estimates.

    Supports:
    - GRR: integer indices, prefers prob_true/prob_false from metadata; falls back to epsilon-based p/q.
    - Bit vectors: debias per-bit when p/q are available (OUE defaults supported); 
      otherwise return per-bit mean as approximation (RAPPOR/OLH debiasing not implemented).
    """

    def __init__(self, num_categories: Optional[int] = None, mechanism: Optional[str] = None):
        # 初始化频率聚合器，可选指定类别总数与机制名称，否则在运行时从报告推断
        if num_categories is not None and num_categories <= 0:
            raise ParamValidationError("num_categories must be positive")
        self.num_categories = int(num_categories) if num_categories is not None else None
        self.mechanism = mechanism

    def _infer_num_categories(self, reports: Sequence[LDPReport], values: Sequence[int]) -> int:
        # 尝试优先从报告 metadata 中推断 domain_size/num_categories, 否则退化为从最大索引加一推断
        if self.num_categories is not None:
            return self.num_categories
        for r in reports:
            meta = r.metadata or {}
            k = meta.get("domain_size") or meta.get("num_categories")
            if k:
                return int(k)
        if not values:
            raise ParamValidationError("cannot infer num_categories from empty reports")
        return max(values) + 1

    def _get_pq(self, reports: Sequence[LDPReport], k: int) -> tuple[float, float]:
        # 从首个报告 metadata 中读取 prob_true/prob_false, 若缺失则按 GRR 标准公式基于 epsilon 与 k 计算 p/q
        meta = reports[0].metadata or {}
        p = meta.get("prob_true")
        q = meta.get("prob_false")
        if p is not None and q is not None:
            return float(p), float(q)
        epsilon = float(reports[0].epsilon)
        exp_eps = np.exp(epsilon)
        denom = exp_eps + k - 1
        return exp_eps / denom, 1.0 / denom

    def _aggregate_grr(self, reports: Sequence[LDPReport], values: Sequence[int]) -> Estimate:
        # 针对 GRR 报告按闭式去偏公式恢复类别频率并做非负裁剪与归一化
        k = self._infer_num_categories(reports, values)
        p, q = self._get_pq(reports, k)
        if np.isclose(p, q):
            raise ParamValidationError("invalid parameters leading to p == q for GRR estimation")

        counts = np.zeros(k, dtype=float)
        for idx in values:
            if idx < 0 or idx >= k:
                raise ParamValidationError(f"encoded index {idx} out of range for num_categories={k}")
            counts[idx] += 1.0

        N = float(len(reports))
        raw = counts / N
        # GRR 去偏公式 est = (raw - q) / (p - q), 再裁剪为非负并归一化为概率分布
        est = (raw - q) / (p - q)
        est = np.clip(est, 0.0, None)
        total = est.sum()
        if total > 0:
            est = est / total
        else:
            est = np.full(k, 1.0 / k)

        metadata: Mapping[str, Any] = {
            "num_categories": k,
            "mechanism": self.mechanism or reports[0].mechanism_id,
            "n_reports": len(reports),
            "p": p,
            "q": q,
            "approximation": None,
        }
        return Estimate(metric="frequency", point=est, variance=None, confidence_interval=None, metadata=metadata)

    def _bit_vectors(self, reports: Sequence[LDPReport]) -> np.ndarray:
        # 将各报告中的编码统一拉平成一维数组并堆叠成二维矩阵，形状为 [n_reports, vector_len]
        vectors = []
        for report in reports:
            arr = np.asarray(report.encoded)
            if arr.ndim != 1:
                arr = arr.ravel()
            vectors.append(arr.astype(float))
        lengths = {vec.shape[0] for vec in vectors}
        if len(lengths) != 1:
            raise ParamValidationError("all bit vectors must have the same length")
        return np.stack(vectors, axis=0)

    def _bit_params(self, reports: Sequence[LDPReport], length: int) -> tuple[float, float, Mapping[str, Any]]:
        # 从 metadata 或机制标识中推断 bit 级 p/q 参数对，OUE 提供默认设置否则返回 None 表示无法去偏
        mechanism_id = (self.mechanism or reports[0].mechanism_id or "").lower()
        meta = reports[0].metadata or {}
        p = meta.get("p")
        q = meta.get("q")
        # 如果未指定，则使用 OUE 默认值
        if mechanism_id in {"oue", "ouemechanism"} or (p is None and q is None and mechanism_id):
            eps = float(reports[0].epsilon)
            if p is None:
                p = 0.5
            if q is None:
                q = 1.0 / (np.exp(eps) + 1.0)
        if p is None or q is None:
            # 兜底：按近似处理（由调用方决定后续策略）
            return None, None, meta  # type: ignore[return-value]
        return float(p), float(q), meta

    def _aggregate_bit_debiased(self, reports: Sequence[LDPReport]) -> Estimate:
        # 对比特向量编码先尝试根据 p/q 做逐位去偏，否则回退到简单均值聚合
        stacked = self._bit_vectors(reports)
        length = stacked.shape[1]
        p, q, first_meta = self._bit_params(reports, length)
        if p is None or q is None:
            return self._aggregate_bit_mean(reports, stacked)

        mean_vec = stacked.mean(axis=0)
        # 使用 (mean - q) / (p - q) 去偏并裁剪为非负再按和归一化
        est = (mean_vec - q) / (p - q)
        est = np.clip(est, 0.0, None)
        total = est.sum()
        if total > 0:
            est = est / total
        metadata: Mapping[str, Any] = {
            "num_categories": self.num_categories,
            "mechanism": self.mechanism or reports[0].mechanism_id,
            "n_reports": len(reports),
            "approximation": None,
            "p": p,
            "q": q,
        }
        metadata.update({k: v for k, v in first_meta.items() if k not in metadata})
        return Estimate(metric="frequency", point=est, variance=None, confidence_interval=None, metadata=metadata)

    def _aggregate_bit_mean(self, reports: Sequence[LDPReport], stacked: Optional[np.ndarray] = None) -> Estimate:
        # 作为近似策略仅对比特向量逐位取平均，不尝试根据机制模型进行去偏
        if stacked is None:
            stacked = self._bit_vectors(reports)
        mean_vec = stacked.mean(axis=0)
        metadata: Mapping[str, Any] = {
            "num_categories": self.num_categories,
            "mechanism": self.mechanism or reports[0].mechanism_id,
            "n_reports": len(reports),
            "approximation": "raw_bit_mean",
        }
        return Estimate(metric="frequency", point=mean_vec, variance=None, confidence_interval=None, metadata=metadata)

    def aggregate(self, reports: Sequence[LDPReport]) -> Estimate:
        # 顶层入口，根据编码类型分派到整数 GRR 聚合或比特向量聚合逻辑并返回 Estimate
        if len(reports) == 0:
            raise ParamValidationError("reports must be non-empty")

        encoded_values = [r.encoded for r in reports]
        if all(isinstance(v, (int, np.integer)) for v in encoded_values):
            return self._aggregate_grr(reports, [int(v) for v in encoded_values])

        return self._aggregate_bit_debiased(reports)

    def get_metadata(self) -> Mapping[str, Any]:
        # 返回聚合器基础配置包括类别数与机制标识用于外部 introspection
        return {"type": "frequency", "num_categories": self.num_categories, "mechanism": self.mechanism}
