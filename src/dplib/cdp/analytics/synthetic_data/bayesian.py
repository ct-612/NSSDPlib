"""
Bayesian network based DP synthetic data generator.

Responsibilities:
    * fit conditional probability tables (CPTs) with DP noise given a fixed structure
    * support simple topological sampling to generate synthetic records
    * provide placeholders for future structure learning strategies
"""
# 说明：基于给定贝叶斯网络结构的差分隐私合成数据生成器（MVP），当前仅支持用户显式提供结构。
# 职责：
# - 在给定贝叶斯网络结构下对各节点的条件概率表进行差分隐私拟合
# - 基于拟合好的条件概率表按拓扑顺序采样生成合成记录
# - 预留未来引入结构学习算法的扩展入口但当前不提供实现
from __future__ import annotations

from itertools import product
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np

from dplib.cdp.analytics.synthetic_data.base_generator import SyntheticDataGenerator
from dplib.core.data import Dataset, DatasetError
from dplib.core.data.domain import BaseDomain, BucketizedDomain, DiscreteDomain
from dplib.core.privacy import PrivacyModel
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.cdp.mechanisms.laplace import LaplaceMechanism


class BayesianNetworkGenerator(SyntheticDataGenerator):
    """Synthetic generator using DP conditional probability tables."""
    # 基于 DP 条件概率表的贝叶斯网络合成数据生成器实现

    method = "bayesian"

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
        structure: Optional[Sequence[Tuple[str, Tuple[str, ...]]]] = None,
        max_parents: int = 2,
        structure_learning: str = "none",
        mechanism: BaseMechanism | str = "laplace",
    ):
        # 初始化贝叶斯网络生成器并保存结构、隐私模型、机制类型等核心配置
        # 通过父类构造函数接入统一的预算会计和 RNG 管理能力
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
        self.structure = tuple(structure or ())
        self.max_parents = max_parents
        self.structure_learning = structure_learning
        self.mechanism = mechanism
        self._parent_map: Dict[str, Tuple[str, ...]] = {}
        self._value_orders: Dict[str, Tuple[Any, ...]] = {}
        self._cpts: Dict[str, Dict[Tuple[Any, ...], np.ndarray]] = {}

    # ------------------------------------------------------------------ fit/sample
    def _fit_internal(self, dataset: Dataset) -> None:
        """Fit CPTs with DP noise for a fixed network structure."""
        # 在固定网络结构前提下为每个节点拟合带噪条件概率表并记录到内部状态
        # 当前假设结构已由上层提供，不执行结构学习
        if self.structure_learning != "none":
            raise NotImplementedError("structure learning is not implemented")
        ensure(self.structure, "network structure is required", error=ParamValidationError)
        # 将总隐私预算按节点数均分，每个节点的 CPT 拟合使用相同 epsilon 份额
        eps_per = float(self.epsilon) / max(len(self.structure), 1)
        mech_factory = self._prepare_mechanism(eps_per)

        for node, parents in self.structure:
            self._validate_node(node, parents)
            self._parent_map[node] = tuple(parents)
            node_values = self._unique_values(dataset, node)
            self._value_orders[node] = node_values
            parent_value_lists = tuple(self._unique_values(dataset, parent) for parent in parents)

            combos = list(product(*parent_value_lists)) if parents else [tuple()]
            cpt: Dict[Tuple[Any, ...], np.ndarray] = {}
            for combo in combos:
                # 针对每一组父节点取值统计目标节点各取值的频数作为原始直方图
                counts = self._counts_for_assignment(dataset, node, parents, combo, node_values)
                mech = mech_factory()
                mech.calibrate(sensitivity=1.0)
                # 对计数向量添加差分隐私噪声并截断到非负，再归一化得到条件分布
                noisy = np.asarray(mech.randomise(counts), dtype=float)
                noisy = np.maximum(noisy, 0.0)
                total = noisy.sum()
                probs = noisy / total if total > 0 else np.ones_like(noisy) / len(noisy)
                cpt[tuple(combo)] = probs
            self._cpts[node] = cpt

        # 拟合完成后记录本次训练消耗的总隐私预算，便于外部预算会计追踪
        self._consume_budget(self.epsilon, self.delta)

    def _sample_internal(self, n: int) -> Dataset:
        """Sample synthetic records according to fitted CPTs."""
        # 按拓扑顺序逐节点采样生成 n 条合成记录
        # 若某些父赋值组合未在 CPT 中出现则回退到域上的均匀分布
        order = self._topological_order()
        rng = self._require_rng()
        records = []
        for _ in range(n):
            record: Dict[str, Any] = {}
            for node in order:
                parents = self._parent_map.get(node, tuple())
                parent_values = tuple(record[p] for p in parents) if parents else tuple()
                probs = self._cpts.get(node, {}).get(parent_values)
                values = self._value_orders.get(node, tuple())
                if probs is None or not values:
                    # fallback: uniform sampling from domain if CPT missing
                    # 当缺少对应 CPT 或节点取值顺序时，从节点域中均匀采样作为保底策略
                    domain = self.domain[node]
                    if isinstance(domain, DiscreteDomain):
                        values = domain.categories
                    elif isinstance(domain, BucketizedDomain):
                        values = tuple(range(len(domain.edges) - 1))
                    probs = np.ones(len(values)) / len(values)
                choice = rng.choice(values, p=probs)
                record[node] = choice
            records.append(record)
        return Dataset.from_records(records)

    # ------------------------------------------------------------------ helpers
    def _validate_node(self, node: str, parents: Sequence[str]) -> None:
        # 校验节点及其父节点是否都在域中定义且父节点数不超过配置上限
        ensure(node in self.domain, f"node '{node}' missing from domain", error=ParamValidationError)
        ensure(len(parents) <= self.max_parents, "too many parents for node", error=ParamValidationError)
        for parent in parents:
            ensure(parent in self.domain, f"parent '{parent}' missing from domain", error=ParamValidationError)

    def _unique_values(self, dataset: Dataset, field: str) -> Tuple[Any, ...]:
        # 从数据集中提取指定字段的去重取值列表，用于确定离散节点的取值空间顺序
        values = []
        for record in dataset.to_list():
            if not isinstance(record, Mapping):
                raise DatasetError("bayesian generator expects mapping-based records")
            values.append(record.get(field))
        unique = tuple(np.unique(values))
        if not unique:
            raise DatasetError(f"field '{field}' has no observed values")
        return unique

    def _counts_for_assignment(
        self,
        dataset: Dataset,
        node: str,
        parents: Sequence[str],
        assignment: Tuple[Any, ...],
        node_values: Tuple[Any, ...],
    ) -> np.ndarray:
        # 在给定父节点赋值 assignment 的条件下统计目标节点在 node_values 上的计数直方图
        counts = np.zeros(len(node_values), dtype=float)
        for record in dataset.to_list():
            if not isinstance(record, Mapping):
                raise DatasetError("bayesian generator expects mapping-based records")
            if parents:
                parent_tuple = tuple(record.get(parent) for parent in parents)
                if parent_tuple != assignment:
                    continue
            value = record.get(node)
            if value in node_values:
                idx = node_values.index(value)
                counts[idx] += 1
        return counts

    def _prepare_mechanism(self, epsilon: float):
        # 根据配置的 mechanism 类型构造局部工厂函数，为每个 CPT 条件分布提供独立机制实例
        def _factory() -> BaseMechanism:
            if isinstance(self.mechanism, BaseMechanism):
                return self.mechanism
            name = str(self.mechanism).lower()
            if name == "laplace":
                return LaplaceMechanism(epsilon=epsilon, rng=self._require_rng())
            raise ParamValidationError(f"unsupported mechanism '{self.mechanism}' for bayesian generator")

        return _factory

    def _topological_order(self) -> Tuple[str, ...]:
        """Simple topological sort based on provided structure."""
        # 基于给定结构的父子关系构造简单的拓扑排序结果，保证采样时父节点先于子节点
        indegree: Dict[str, int] = {}
        deps: Dict[str, set[str]] = {}
        for node, parents in self.structure:
            indegree.setdefault(node, 0)
            indegree[node] += len(parents)
            deps[node] = set(parents)
            for parent in parents:
                indegree.setdefault(parent, 0)
        queue = [node for node, deg in indegree.items() if deg == 0]
        order = []
        while queue:
            current = queue.pop(0)
            order.append(current)
            for node, parents in deps.items():
                if current in parents:
                    indegree[node] -= 1
                    if indegree[node] == 0:
                        queue.append(node)
        return tuple(order) if order else tuple(indegree.keys())

    def _config_extra(self) -> Dict[str, Any]:
        # 将结构、父节点上限和机制名称等特定配置导出为可序列化字典，便于重建同一生成器实例
        return {
            "structure": [(node, tuple(parents)) for node, parents in self.structure],
            "max_parents": self.max_parents,
            "structure_learning": self.structure_learning,
            "mechanism": self.mechanism if isinstance(self.mechanism, str) else self.mechanism.__class__.__name__,
        }
