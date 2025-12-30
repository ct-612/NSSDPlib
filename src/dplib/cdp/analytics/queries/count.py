"""
Privacy-preserving COUNT query utilities.

Responsibilities
  - Accept arbitrary iterable data sources with optional predicates.
  - Default to Laplace noise calibrated for unit sensitivity.
  - Allow custom calibrated mechanisms to be supplied for noise generation.

Usage Context
  - Use to compute a noisy count from an in-memory iterable.
  - Intended for record-level contribution with unit sensitivity.

Limitations
  - Requires a calibrated mechanism; uses Laplace when none is provided.
  - Operates on materialized iterables and returns a float count.
"""
# 说明：针对任意可迭代数据源提供带 Laplace 噪声的计数查询工具。
# 职责：
# - 接受可选谓词过滤逻辑并统一处理多种输入容器类型
# - 默认构造单位敏感度（Δ=1）的 Laplace 机制并允许外部注入已校准机制
# - 对真实计数结果添加噪声后返回浮点形式的差分隐私计数值

from __future__ import annotations

from typing import Any, Callable, Iterable, List, Optional

import numpy as np

from dplib.core.data.statistics import count as count_values
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.cdp.mechanisms.laplace import LaplaceMechanism

Predicate = Callable[[Any], bool]  # 谓词类型：接收元素，返回布尔值


class PrivateCountQuery:
    """
    Release DP protected counts for arbitrary iterables.

    - Configuration
      - epsilon: Privacy budget used when constructing a default mechanism.
      - mechanism: Optional calibrated mechanism to apply noise.
      - predicate: Optional filter applied before counting.

    - Behavior
      - Materializes inputs to count records deterministically.
      - Adds noise using the configured mechanism and returns a float.

    - Usage Notes
      - Provide a calibrated mechanism to override the default Laplace mechanism.
    """

    def __init__(
        self,
        epsilon: float,
        *,
        mechanism: Optional[BaseMechanism] = None,
        predicate: Optional[Predicate] = None,
    ):
        # 校验 epsilon 与可选 predicate 并准备计数查询使用的噪声机制
        self.epsilon = self._validate_epsilon(epsilon)
        if predicate is not None:
            ensure(callable(predicate), "predicate must be callable", error=ParamValidationError)
        self.predicate = predicate
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将传入的 epsilon 转为浮点并要求其为正数否则抛出 ParamValidationError
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ParamValidationError("epsilon must be a positive number for count queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for count queries", error=ParamValidationError)
        return numeric

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 若未提供机制则创建单位敏感度（Δ=1）的 Laplace 机制并完成校准，否则校验外部机制类型与已校准状态
        if mechanism is None:
            mech = LaplaceMechanism(epsilon=self.epsilon, sensitivity=1.0)
            mech.calibrate()
            return mech
        ensure_type(mechanism, (BaseMechanism,), label="mechanism")
        ensure(mechanism.calibrated, "provided mechanism must be calibrated before use", error=ParamValidationError)
        return mechanism

    @staticmethod
    def _materialize_iterable(data: Any) -> List[Any]:
        # 将输入统一转换为列表并显式拒绝字符串类型或不可迭代对象
        if isinstance(data, (str, bytes)):
            raise ParamValidationError("count query input must not be a string")
        try:
            iterable = data if isinstance(data, np.ndarray) or isinstance(data, list) else list(data)  # type: ignore[arg-type]
        except TypeError as exc:  # pragma: no cover - defensive
            raise ParamValidationError("count query input must be iterable") from exc
        return list(iterable)

    def _count(self, data: List[Any], predicate: Optional[Predicate]) -> int:
        # 若未提供谓词则直接统计元素数量否则按谓词过滤后计数
        if predicate is None:
            return int(count_values(data))
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
        # 结合可选覆盖谓词完成计数并通过已配置机制对真实计数添加噪声
        effective_predicate = predicate or self.predicate
        materialized = self._materialize_iterable(data)
        true_count = float(self._count(materialized, effective_predicate))
        return float(self.mechanism.randomise(true_count))
