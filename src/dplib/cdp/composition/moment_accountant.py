"""
Lightweight moments accountant for multi-step DP composition.

Tracks cumulative (α, ε)-RDP values across steps and converts to the
tightest (ε, δ)-DP guarantee by minimising over provided orders. Designed
to serve iterative algorithms（如 DP-SGD）或多轮查询的精确会计。
"""
# 说明：用于多步差分隐私组合的轻量级矩会计工具基于 RDP 累积推导最优 (ε, δ)-DP 保证。
# 职责：
# - 在一组预定义阶数上累计每一步的 (α, ε)-RDP 贡献
# - 在给定 δ 下遍历所有阶数并选择提供最紧 (ε, δ) 界的阶数
# - 提供读取当前 RDP 累积值、转换为 DP 保证以及重置状态等接口

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple

from dplib.core.privacy.privacy_model import rdp_to_cdp
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type


@dataclass
class MomentAccountant:
    """
    Tracks cumulative RDP at multiple orders and returns the best (ε, δ)-DP.

    orders: sequence of α values to track and search over.
    """

    orders: Tuple[float, ...]
    _rdp: Dict[float, float] = field(default_factory=dict, init=False)

    def __init__(self, orders: Optional[Sequence[float]] = None):
        # 使用指定或默认阶数集合初始化矩会计器并为每个阶数设置累积 ε 初始值
        if orders is None:
            orders = (1.5, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
        # 基本合法性检查：阶数需大于 1
        for alpha in orders:
            ensure(alpha > 1, "rdp order must be > 1")
        self.orders = tuple(float(alpha) for alpha in orders)
        self._rdp = {alpha: 0.0 for alpha in self.orders}

    # ------------------------------ mutation
    def add_rdp(self, order: float, epsilon: float) -> None:
        """Accumulate RDP at a specific order."""
        # 在指定阶数上累加一次 RDP ε 并执行类型与非负性校验
        ensure(order in self._rdp, f"order {order} not tracked by accountant")
        ensure_type(epsilon, (int, float), label="epsilon")
        ensure(epsilon >= 0, "epsilon must be non-negative")
        self._rdp[order] += float(epsilon)

    def add_step(self, rdp_epsilons: Mapping[float, float]) -> None:
        """Add a step of RDP contributions: mapping {order: epsilon}."""
        # 为一次算法迭代添加按阶数拆分的 RDP 贡献映射
        for order, eps in rdp_epsilons.items():
            self.add_rdp(float(order), float(eps))

    def add_steps(self, steps: Iterable[Mapping[float, float]]) -> None:
        """Bulk add multiple steps."""
        # 批量添加多次迭代的 RDP 贡献便于从外部日志或分析结果导入
        for step in steps:
            self.add_step(step)

    # ------------------------------ queries
    def get_rdp(self) -> Dict[float, float]:
        """Return a copy of cumulative RDP map."""
        # 返回当前各阶数累计 RDP 的浅拷贝避免外部直接修改内部状态
        return dict(self._rdp)

    def get_epsilon(self, delta: float) -> float:
        """
        Convert accumulated RDP to the tightest (ε, δ)-DP by minimising over orders.
        """
        # 在给定 δ 下遍历所有阶数通过 rdp_to_cdp 转换并取最小 ε 作为最优界
        ensure_type(delta, (int, float), label="delta")
        ensure(0 < delta < 1, "delta must be in (0,1)")
        candidates = []
        for order, eps in self._rdp.items():
            candidates.append(rdp_to_cdp(order, eps, delta))
        if not candidates:
            raise ParamValidationError("no RDP orders tracked; cannot compute epsilon")
        return min(candidates)

    def spent(self, delta: float) -> Tuple[float, float]:
        """Return (epsilon, delta) using current RDP totals at best order."""
        # 便捷接口直接返回最优 ε 与对应输入的 δ 组成的 DP 开销对
        eps = self.get_epsilon(delta)
        return eps, float(delta)

    def reset(self) -> None:
        """Reset accumulated RDP to zero."""
        # 将所有阶数的累计 RDP 清零用于重新开始记账或多阶段算法
        for order in self._rdp:
            self._rdp[order] = 0.0
