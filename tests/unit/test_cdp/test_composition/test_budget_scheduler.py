"""
Unit tests for the CDP budget scheduler.
"""
# 说明：针对中心差分隐私预算调度器 BudgetScheduler 及 Allocation 容器的行为验证测试。
# 覆盖：
# - 均匀分配 allocate_uniform 对 ε 和 δ 等分的逻辑
# - 按权重比例分配 allocate_proportional 的计算与异常分支
# - 时间窗口分配 allocate_windows 在均匀与几何衰减场景下的行为
# - remaining_after_allocation 接口在预算用尽时不产生负值的保护
# - 非法窗口数量与衰减参数时抛出 ParamValidationError 的边界条件

import pytest

from dplib.cdp.composition.budget_scheduler import Allocation, BudgetScheduler
from dplib.core.utils.param_validation import ParamValidationError


def test_allocate_uniform_splits_evenly() -> None:
    # 验证 allocate_uniform 会按键数量将总 ε 和 δ 等分并返回 Allocation 实例
    scheduler = BudgetScheduler(total_epsilon=1.0, total_delta=1e-4)
    allocations = scheduler.allocate_uniform({"a": 1, "b": 1, "c": 1})
    assert len(allocations) == 3
    assert all(isinstance(a, Allocation) for a in allocations.values())
    assert allocations["a"].epsilon == pytest.approx(1.0 / 3)
    assert allocations["a"].delta == pytest.approx(1e-4 / 3)


def test_allocate_proportional_uses_weights() -> None:
    # 验证 allocate_proportional 按权重比例切分总预算且重权重项获得更大份额
    scheduler = BudgetScheduler(total_epsilon=2.0, total_delta=2e-5)
    allocations = scheduler.allocate_proportional({"heavy": 2.0, "light": 1.0})
    assert allocations["heavy"].epsilon == pytest.approx(4 / 3)
    assert allocations["light"].epsilon == pytest.approx(2 / 3)
    assert allocations["heavy"].delta == pytest.approx((2e-5) * (2 / 3))
    assert allocations["light"].delta == pytest.approx((2e-5) * (1 / 3))


def test_allocate_proportional_rejects_negative_or_empty() -> None:
    # 验证 allocate_proportional 对空权重或包含负权重时抛出 ParamValidationError
    scheduler = BudgetScheduler(total_epsilon=1.0, total_delta=1e-5)
    with pytest.raises(ParamValidationError):
        scheduler.allocate_proportional({})
    with pytest.raises(ParamValidationError):
        scheduler.allocate_proportional({"bad": -1.0})


def test_allocate_windows_uniform_and_decay() -> None:
    # 验证 allocate_windows 在均匀与几何衰减模式下的窗口预算分配与总和守恒
    scheduler = BudgetScheduler(total_epsilon=1.0, total_delta=0.0)
    uniform = scheduler.allocate_windows(2, decay=1.0)
    assert len(uniform) == 2
    assert uniform[0].epsilon == pytest.approx(0.5)
    decayed = scheduler.allocate_windows(3, decay=0.5)
    eps_total = sum(a.epsilon for a in decayed)
    assert eps_total == pytest.approx(1.0)
    assert decayed[0].epsilon > decayed[1].epsilon > decayed[2].epsilon


def test_remaining_after_allocation_never_negative() -> None:
    # 验证剩余预算计算在全部分配完时不会产生负数结果
    scheduler = BudgetScheduler(total_epsilon=0.5, total_delta=0.0)
    allocations = scheduler.allocate_uniform({"x": 1, "y": 1})
    remaining = scheduler.remaining_after_allocation(allocations)
    assert remaining.epsilon == pytest.approx(0.0)
    assert remaining.delta == pytest.approx(0.0)


def test_allocate_windows_invalid_args() -> None:
    # 验证 allocate_windows 对非正窗口数量或非正衰减参数进行参数校验
    scheduler = BudgetScheduler(total_epsilon=1.0, total_delta=0.0)
    with pytest.raises(ParamValidationError):
        scheduler.allocate_windows(0)
    with pytest.raises(ParamValidationError):
        scheduler.allocate_windows(2, decay=0)
