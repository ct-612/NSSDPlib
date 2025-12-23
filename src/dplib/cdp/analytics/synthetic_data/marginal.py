"""
Marginal-based DP synthetic data generator.

Responsibilities
  - Estimate DP marginals (1-D or low-order) from discrete datasets.
  - Add calibrated noise via the selected mechanism.
  - Independently sample columns from noisy marginals.

Usage Context
  - Use for discrete or bucketized domains with mapping-based records.
  - Designed for lightweight synthetic generation via marginals.

Limitations
  - Sampling uses only 1-D marginals and ignores higher-order dependencies.
  - Marginal estimation assumes discrete or bucketized domains.
"""
# 说明：使用差分隐私边际直方图生成合成数据的实现（MVP 版），侧重接口与数据流打通，算法可后续替换。
# 职责：
# - 基于离散或分箱域从原始数据估计一维或低阶边际直方图
# - 使用配置的差分隐私机制对边际计数添加噪声并缓存结果
# - 在采样阶段独立地从各字段边际分布中抽样生成合成数据列
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence, Tuple

import numpy as np

from dplib.cdp.analytics.synthetic_data.base_generator import SyntheticDataGenerator
from dplib.core.data import Dataset, DatasetError
from dplib.core.data.domain import BaseDomain, BucketizedDomain, DiscreteDomain
from dplib.core.privacy import PrivacyModel
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.core.utils.random import create_rng
from dplib.cdp.mechanisms.laplace import LaplaceMechanism


class MarginalGenerator(SyntheticDataGenerator):
    """
    Synthetic generator using DP marginal histograms.

    - Configuration
      - domain: Mapping of field names to domains.
      - epsilon: Privacy budget for marginal estimation.
      - delta: Optional delta parameter for approximate DP.
      - marginals: Optional explicit list of marginals to estimate.
      - max_order: Maximum order used for auto-generated marginals.
      - mechanism: Mechanism or name used for count noise.
      - epsilon_split: Strategy name for epsilon allocation.

    - Behavior
      - Estimates noisy marginals and caches value grids.
      - Samples columns independently using 1-D marginals.

    - Usage Notes
      - Provide explicit marginals to control estimation scope.
    """
    # 使用差分隐私边际直方图的合成数据生成器，实现简单独立列采样策略

    method = "marginal"

    def __init__(
        self,
        domain: Mapping[str, BaseDomain],
        epsilon: float,
        *,
        delta: float = 0.0,
        privacy_model: PrivacyModel = PrivacyModel.CDP,
        accountant=None,
        budget_tracker=None,
        budget_scope=None,
        rng: Optional[np.random.Generator] = None,
        seed: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        marginals: Optional[Sequence[Tuple[str, ...]]] = None,
        max_order: int = 2,
        mechanism: BaseMechanism | str = "laplace",
        epsilon_split: str = "uniform",
    ):
        # 初始化边际生成器配置，包括域、候选边际、阶数上限以及噪声机制和隐私预算分配策略
        # 若未显式指定边际集合则基于域字段自动生成一阶与二阶组合
        super().__init__(
            domain=domain,
            epsilon=epsilon,
            delta=delta,
            privacy_model=privacy_model,
            accountant=accountant,
            budget_tracker=budget_tracker,
            budget_scope=budget_scope,
            rng=rng,
            seed=seed,
            metadata=metadata,
        )
        self.marginals: Sequence[Tuple[str, ...]] = marginals or self._auto_marginals(max_order=max_order)
        self.max_order = max_order
        self.mechanism = mechanism
        self.epsilon_split = epsilon_split
        self._noisy_marginals: Dict[Tuple[str, ...], np.ndarray] = {}
        self._value_grids: Dict[Tuple[str, ...], Tuple[Tuple[Any, ...], ...]] = {}

    # ------------------------------------------------------------------ fit/sample
    def _fit_internal(self, dataset: Dataset) -> None:
        """Estimate noisy marginals and cache value grids."""
        # 对配置的每个边际计算计数张量并添加差分隐私噪声，同时缓存取值网格与噪声结果
        ensure(self.marginals, "at least one marginal is required", error=ParamValidationError)
        eps_per = self._allocate_epsilon()
        for marginal in self.marginals:
            self._validate_fields(marginal)
            grid, counts = self._compute_counts(dataset, marginal)
            noisy = self._add_noise(counts, eps_per)
            self._value_grids[marginal] = grid
            self._noisy_marginals[marginal] = noisy
        # 拟合完成后标记消耗一次完整的 (epsilon, delta) 预算
        self._consume_budget(self.epsilon, self.delta)

    def _sample_internal(self, n: int) -> Dataset:
        """Independently sample columns using available 1-D marginals."""
        # 仅使用一维边际为每个字段构建采样分布，缺失字段回退为域上的均匀分布
        rng = self._require_rng()
        field_marginals: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        for fields, counts in self._noisy_marginals.items():
            if len(fields) != 1:
                continue
            values = np.asarray(self._value_grids[fields][0])
            probs = counts.astype(float)
            probs = np.maximum(probs, 0.0)
            total = probs.sum()
            if total <= 0:
                probs = np.ones_like(probs, dtype=float)
                total = probs.sum()
            probs = probs / total
            field_marginals[fields[0]] = (values, probs)
        ensure(field_marginals, "at least one 1-D marginal is required for sampling", error=DatasetError)

        samples: Dict[str, np.ndarray] = {}
        for field in self._domain_fields():
            if field not in field_marginals:
                # fallback: uniform over domain categories if available
                # 对未提供边际的字段从域的类别或分箱索引上均匀采样作为保底策略
                domain = self.domain[field]
                if isinstance(domain, DiscreteDomain):
                    values = np.asarray(domain.categories)
                elif isinstance(domain, BucketizedDomain):
                    values = np.arange(len(domain.edges) - 1)
                else:
                    continue
                probs = np.ones(len(values), dtype=float) / len(values)
                field_marginals[field] = (values, probs)
            values, probs = field_marginals[field]
            samples[field] = rng.choice(values, size=n, p=probs)
        return Dataset.from_arrays(samples)

    # ------------------------------------------------------------------ helpers
    def _allocate_epsilon(self) -> float:
        """Simple epsilon split across marginals."""
        # 在当前实现中将总 epsilon 在所有边际之间做简单均分（后续可扩展为加权分配策略）
        if not self.marginals:
            return float(self.epsilon)
        if self.epsilon_split == "uniform":
            return float(self.epsilon) / float(len(self.marginals))
        # TODO:placeholder for weighted strategy
        return float(self.epsilon) / float(len(self.marginals))

    def _validate_fields(self, fields: Sequence[str]) -> None:
        # 校验边际字段集合类型、非空性以及对应域是否存在且类型受支持
        ensure_type(fields, (tuple, list), label="marginal fields")
        ensure(fields, "marginal fields cannot be empty", error=ParamValidationError)
        for field in fields:
            ensure(field in self.domain, f"field '{field}' missing from domain", error=ParamValidationError)
            ensure_type(
                self.domain[field],
                (DiscreteDomain, BucketizedDomain, BaseDomain),
                label=f"{field}.domain",
            )

    def _compute_counts(
        self,
        dataset: Dataset,
        fields: Sequence[str],
    ) -> Tuple[Tuple[Tuple[Any, ...], ...], np.ndarray]:
        """Compute raw counts for the specified marginal."""
        # 为给定字段集合构造取值网格并统计对应的联合计数张量
        value_lists: Tuple[Tuple[Any, ...], ...] = tuple(
            self._extract_field_values(dataset, field) for field in fields
        )
        value_grids = tuple(tuple(np.unique(values)) for values in value_lists)
        counts = defaultdict(int)
        for record in dataset.to_list():
            if not isinstance(record, Mapping):
                raise DatasetError("marginal generator expects mapping-based records")
            key = tuple(record.get(field) for field in fields)
            counts[key] += 1

        shape = tuple(len(grid) for grid in value_grids)
        tensor = np.zeros(shape, dtype=float)
        for key, count in counts.items():
            # 根据记录取值在各字段取值网格中的索引定位计数张量坐标
            index = tuple(value_grids[idx].index(key[idx]) for idx in range(len(fields)))
            tensor[index] = float(count)
        return value_grids, tensor

    def _extract_field_values(self, dataset: Dataset, field: str) -> Tuple[Any, ...]:
        # 从数据集中提取指定字段的所有取值序列，用于后续去重生成取值网格
        values = []
        for record in dataset.to_list():
            if not isinstance(record, Mapping):
                raise DatasetError("marginal generator expects mapping-based records")
            values.append(record.get(field))
        return tuple(values)

    def _add_noise(self, counts: np.ndarray, epsilon: float) -> np.ndarray:
        """Add DP noise using provided mechanism or default Laplace."""
        # 使用指定机制对计数张量施加差分隐私噪声并返回浮点数组形式
        mech = self._prepare_mechanism(epsilon)
        mech.calibrate(sensitivity=1.0)
        noisy = mech.randomise(counts)
        return np.asarray(noisy, dtype=float)

    def _prepare_mechanism(self, epsilon: float) -> BaseMechanism:
        # 构造或复用边际噪声机制实例，默认采用 Laplace 机制
        if isinstance(self.mechanism, BaseMechanism):
            return self.mechanism
        name = str(self.mechanism).lower()
        if name == "laplace":
            return LaplaceMechanism(epsilon=epsilon, rng=self._require_rng())
        raise ParamValidationError(f"unsupported mechanism '{self.mechanism}' for marginal generator")

    def _auto_marginals(self, *, max_order: int) -> Sequence[Tuple[str, ...]]:
        """Auto-generate low-order marginals from domain field names."""
        # 在未显式配置时基于域字段自动生成一阶边际和所有成对二阶边际
        fields = self._domain_fields()
        if not fields:
            return ()
        singles = [(field,) for field in fields]
        if max_order <= 1 or len(fields) < 2:
            return singles
        pairs = [(fields[i], fields[j]) for i in range(len(fields)) for j in range(i + 1, len(fields))]
        return singles + pairs

    def _config_extra(self) -> Dict[str, Any]:
        # 导出边际生成器特有配置，便于序列化和重建同配置的实例
        return {
            "marginals": [tuple(fields) for fields in self.marginals],
            "max_order": self.max_order,
            "mechanism": self.mechanism if isinstance(self.mechanism, str) else self.mechanism.__class__.__name__,
            "epsilon_split": self.epsilon_split,
        }
