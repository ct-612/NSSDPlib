"""
Unit tests for the SyntheticDataGenerator base class and its budget integration.
"""
# 说明：SyntheticDataGenerator 基类及其隐私预算集成行为的单元测试。
# 覆盖：
# - fit 对原始数组输入的 Dataset 规范化与字段映射
# - sample 在 as_dataset=True 时的数据集封装与字段完整性
# - _consume_budget 与 CDPPrivacyAccountant 和 BudgetTracker 的花费记录联动路径

from __future__ import annotations

import numpy as np

from dplib.cdp.analytics.synthetic_data.base_generator import SyntheticDataGenerator
from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
from dplib.core.data import Dataset
from dplib.core.data.domain import DiscreteDomain
from dplib.core.privacy.budget_tracker import BudgetTracker


class _DummyGenerator(SyntheticDataGenerator):
    method = "dummy"

    def __init__(self, *args, **kwargs):
        # 初始化占位生成器实例并透传所有参数给基类，同时设置拟合标记和观测数据缓存
        super().__init__(*args, **kwargs)
        self.fitted = False
        self._seen = None

    def _fit_internal(self, dataset: Dataset) -> None:
        # 标记生成器已完成拟合并记录输入数据集，后续用于行为断言
        self.fitted = True
        self._seen = dataset
        # 消耗少量隐私预算以覆盖会计路径和预算跟踪逻辑
        self._consume_budget(0.1, 0.0, description="dummy fit")

    def _sample_internal(self, n: int):
        # 在简单离散空间中采样值并通过基类工具转换为 Dataset
        rng = self._require_rng()
        values = rng.integers(0, 3, size=(n, len(self._domain_fields()) or 1))
        return self._dataset_from_array(values)


def test_fit_coerces_inputs_to_dataset() -> None:
    # 验证 fit 能将 ndarray 输入规范化为 Dataset 并按照域字段名组织记录
    domain = {
        "x": DiscreteDomain(["a", "b", "c"]),
        "y": DiscreteDomain([1, 2, 3]),
    }
    data = np.array([[1, 2], [3, 4]])
    gen = _DummyGenerator(domain=domain, epsilon=1.0, seed=0)

    gen.fit(data)

    assert gen.fitted is True
    assert isinstance(gen._seen, Dataset)
    assert len(gen._seen) == 2
    assert set(gen._seen[0].keys()) == {"x", "y"}


def test_sample_wraps_as_dataset() -> None:
    # 验证 sample 在 as_dataset=True 时返回 Dataset 且记录数量与字段集合符合预期
    domain = {"x": DiscreteDomain(["a", "b", "c"])}
    gen = _DummyGenerator(domain=domain, epsilon=1.0, seed=1)
    gen.fitted = True  # skip fit for sampling test

    sampled = gen.sample(5, as_dataset=True)

    assert isinstance(sampled, Dataset)
    assert len(sampled) == 5
    first = sampled[0]
    assert isinstance(first, dict)
    assert set(first.keys()) == {"x"}


def test_consume_budget_records_spending() -> None:
    # 验证 _consume_budget 会同步更新 CDPPrivacyAccountant 与 BudgetTracker 的花费记录
    domain = {"x": DiscreteDomain(["a", "b"])}
    accountant = CDPPrivacyAccountant(total_epsilon=1.0, total_delta=0.5)
    tracker = BudgetTracker()
    scope = tracker.register_scope("test", "g1", total_epsilon=1.0, total_delta=0.5)
    gen = _DummyGenerator(
        domain=domain,
        epsilon=0.4,
        delta=0.1,
        seed=2,
        accountant=accountant,
        budget_tracker=tracker,
        budget_scope=scope,
    )

    gen._consume_budget(0.2, 0.05, description="unit-test spend")

    # CDPPrivacyAccountant 应通过其内部核心会计器记录本次隐私预算花费
    spent_eps, spent_delta = accountant.spent
    assert spent_eps == 0.2
    assert spent_delta == 0.05

    # BudgetTracker 也应在指定作用域上记录相同的 epsilon 和 delta 花费
    spent_scope = tracker.spent(scope)
    assert spent_scope.epsilon == 0.2
    assert spent_scope.delta == 0.05
