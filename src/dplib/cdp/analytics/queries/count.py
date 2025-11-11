"""
Privacy-preserving COUNT query utilities.

Responsibilities:
    * accept arbitrary iterable data sources with optional predicates
    * default to Laplace noise calibrated for unit sensitivity
    * provide deterministic hooks for custom mechanisms (e.g., Gaussian)
"""

# 说明：差分隐私计数查询工具。
# 职责：
# - 输入可为任意可迭代对象，支持可选谓词过滤
# - 默认使用单位敏感度（Δ=1）的拉普拉斯机制并在内部完成校准
# - 也可注入自定义机制（需继承 BaseMechanism 且已校准）

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

import numpy as np

from dplib.cdp.mechanisms.laplace import LaplaceMechanism
from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError

Predicate = Callable[[Any], bool]  # 谓词类型：接收元素，返回布尔值


class PrivateCountQuery:
    """Release DP protected counts for arbitrary iterables."""

    # 对任意可迭代数据执行计数，并返回加入噪声的差分隐私计数。

    def __init__(
        self,
        epsilon: float,
        *,
        mechanism: Optional[BaseMechanism] = None,
        predicate: Optional[Predicate] = None,
    ):
        # 构造：校验 ε，保存可选谓词；准备并校准噪声机制（默认 Laplace Δ=1）。
        self._validate_epsilon(epsilon)
        self.epsilon = float(epsilon)
        self.predicate = predicate
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> None:
        # ε 必须为正数；否则抛出参数校验错误。
        if epsilon is None or float(epsilon) <= 0:
            raise ValidationError("epsilon must be a positive number for count queries")

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 准备噪声机制：
        # - 未提供时创建 LaplaceMechanism(ε, Δ = 1.0) 并 calibrate()；
        # - 提供时要求继承 BaseMechanism 且已校准。
        if mechanism is None:
            mech = LaplaceMechanism(epsilon=self.epsilon, sensitivity=1.0)
            mech.calibrate()
            return mech
        if not isinstance(mechanism, BaseMechanism):
            raise ValidationError("mechanism must inherit from BaseMechanism")
        if not mechanism.calibrated:
            raise ValidationError("provided mechanism must be calibrated before use")
        return mechanism

    @staticmethod
    def _ensure_iterable(data: Any) -> Iterable[Any]:
        # 输入必须是可迭代对象；字符串/字节串不被接受以避免逐字符计数的误用。
        if isinstance(data, (str, bytes)):
            raise ValidationError("count query input must not be a string")
        try:
            iter(data)
        except TypeError as exc:  # pragma: no cover - defensive
            raise ValidationError("count query input must be iterable") from exc
        return data

    def _count(self, data: Iterable[Any], predicate: Optional[Predicate]) -> int:
        # 真实计数：
        # - 若是 numpy 数组，走矢量化路径；
        # - 否则使用 Python 生成器统计；
        # - 无谓词时即为元素总数，有谓词时统计满足谓词的数量。
        if isinstance(data, np.ndarray):
            if predicate is None:
                return int(data.size)
            mask = np.vectorize(predicate, otypes=[bool])(data)
            return int(np.count_nonzero(mask))

        if predicate is None:
            return sum(1 for _ in data)
        return sum(1 for value in data if predicate(value))

    def evaluate(
        self, data: Iterable[Any], predicate: Optional[Predicate] = None
    ) -> float:
        """
        Execute the DP count query on the provided iterable.

        Args:
            data: Iterable collection to count over.
            predicate: Optional predicate overriding the default configured one.
        Returns:
            Noisy count as a floating point value.
        """
        # 流程：
        # 1) 选择谓词（参数优先于默认）；
        # 2) 校验输入可迭代；
        # 3) 计算真实计数；
        # 4) 通过机制 randomise() 加噪并返回浮点值。
        predicate = predicate or self.predicate
        iterable = self._ensure_iterable(data)
        true_count = float(self._count(iterable, predicate))
        return float(self.mechanism.randomise(true_count))
