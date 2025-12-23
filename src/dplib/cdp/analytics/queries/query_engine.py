"""
Query engine orchestrating DP analytics with optional accounting.

Responsibilities
  - Provide a unified execution entry for built-in queries.
  - Support simple query pipelines with optional carry-forward input.
  - Hook into PrivacyAccountant for spend recording.

Usage Context
  - Use when dispatching named DP queries with shared accounting.
  - Supports built-in query handlers and custom registrations.

Limitations
  - Assumes handlers return results paired with (epsilon, delta) spend.
  - Does not enforce specific accounting policies beyond recording events.
"""
# 说明：为内置差分隐私查询提供统一执行入口并可选接入隐私会计进行预算记录。
# 职责：
# - 通过名称注册表调度 count/sum/mean/variance/histogram/range 等内置查询处理器
# - 支持简单的查询流水线并可选择在步骤间传递前一结果作为下一步输入
# - 在配置 PrivacyAccountant 时按查询消费的 (ε, δ) 记录隐私支出元数据

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from dplib.core.privacy.base_mechanism import ValidationError
from dplib.core.privacy.privacy_accountant import PrivacyAccountant
from dplib.core.utils.param_validation import ensure

from .count import PrivateCountQuery
from .histogram import PrivateHistogramQuery
from .mean import PrivateMeanQuery
from .range import PrivateRangeQuery
from .sum import PrivateSumQuery
from .variance import PrivateVarianceQuery

Handler = Callable[[Iterable[Any], Dict[str, Any]], Tuple[Any, Tuple[float, float]]]


class QueryEngine:
    """
    Lightweight dispatcher for analytics queries with optional accounting.

    - Configuration
      - accountant: Optional PrivacyAccountant used to record spend events.

    - Behavior
      - Dispatches named queries and records privacy spend when configured.
      - Supports pipelines with optional carry-forward inputs.

    - Usage Notes
      - Register custom handlers to extend built-in query support.
    """

    def __init__(self, *, accountant: Optional[PrivacyAccountant] = None):
        # 初始化查询引擎并构建内置查询名到处理器的注册表，可选挂载 PrivacyAccountant
        self._accountant = accountant
        self._registry: Dict[str, Handler] = {
            "count": self._run_count,
            "sum": self._run_sum,
            "mean": self._run_mean,
            "variance": self._run_variance,
            "histogram": self._run_histogram,
            "range": self._run_range,
        }

    def register(self, name: str, handler: Handler) -> None:
        """Register a custom query handler."""
        # 允许外部按名称注册自定义查询处理器覆盖或扩展默认行为
        ensure(name, "query name must be non-empty", error=ValidationError)
        self._registry[name.lower()] = handler

    def execute(self, name: str, *, data: Iterable[Any], **kwargs: Any) -> Any:
        """
        Execute a single query by name.

        kwargs are forwarded to the registered handler.
        """
        # 按名称查找对应处理器执行单次查询并在有会计实例时记录隐私支出
        handler = self._registry.get(name.lower())
        if handler is None:
            raise ValidationError(f"unknown query '{name}'")
        metadata = kwargs.pop("accounting_metadata", None)
        result, spend = handler(data, kwargs)
        self._record_spend(name, spend, metadata=metadata)
        return result

    def pipeline(
        self,
        data: Iterable[Any],
        steps: Sequence[Mapping[str, Any]],
        *,
        carry: bool = False,
    ) -> List[Any]:
        """
        Execute a sequence of queries.

        Args:
            data: Base dataset used as input for each step (unless carry=True).
            steps: Iterable of {"query": str, **params}.
            carry: When True, feed previous result into the next step.
        """
        # 顺序执行一组查询步骤，可选择将上一步结果作为下一步输入形成简单流水线
        results: List[Any] = []
        current: Iterable[Any] = data
        for step in steps:
            query_name = step.get("query")
            if not query_name:
                raise ValidationError("each pipeline step requires 'query'")
            params = {k: v for k, v in step.items() if k != "query"}
            result = self.execute(query_name, data=current, **params)
            results.append(result)
            if carry:
                current = result  # type: ignore[assignment]
        return results

    # ------------------------------------------------------------------ handlers
    def _run_count(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造带可选谓词与机制的计数查询并返回结果与对应 ε 消耗
        epsilon = self._require_param(params, "epsilon")
        predicate = params.get("predicate")
        mechanism = params.get("mechanism")
        query = PrivateCountQuery(epsilon=epsilon, mechanism=mechanism, predicate=predicate)
        return query.evaluate(data), (query.epsilon, 0.0)

    def _run_sum(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造带边界与可选机制的求和查询并记录纯 ε 消耗
        epsilon = self._require_param(params, "epsilon")
        bounds = self._require_param(params, "bounds")
        mechanism = params.get("mechanism")
        query = PrivateSumQuery(epsilon=epsilon, bounds=bounds, mechanism=mechanism)
        return query.evaluate(data), (query.epsilon, 0.0)

    def _run_mean(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造均值查询支持自定义 ε 拆分与复用外部 sum/count 查询
        epsilon = self._require_param(params, "epsilon")
        bounds = self._require_param(params, "bounds")
        query = PrivateMeanQuery(
            epsilon=epsilon,
            bounds=bounds,
            sum_epsilon=params.get("sum_epsilon"),
            count_epsilon=params.get("count_epsilon"),
            sum_query=params.get("sum_query"),
            count_query=params.get("count_query"),
            min_count=params.get("min_count", 1e-6),
        )
        return query.evaluate(data), (query.epsilon, 0.0)

    def _run_variance(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造方差查询支持 ddof 配置与 sum/sum-of-squares/count 多路 ε 拆分
        epsilon = self._require_param(params, "epsilon")
        bounds = self._require_param(params, "bounds")
        query = PrivateVarianceQuery(
            epsilon=epsilon,
            bounds=bounds,
            ddof=params.get("ddof", 1),
            sum_epsilon=params.get("sum_epsilon"),
            squares_epsilon=params.get("squares_epsilon"),
            count_epsilon=params.get("count_epsilon"),
            sum_query=params.get("sum_query"),
            squares_query=params.get("squares_query"),
            count_query=params.get("count_query"),
            min_count=params.get("min_count", 1e-6),
        )
        return query.evaluate(data), (query.epsilon, 0.0)

    def _run_histogram(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造直方图查询支持最大贡献次数与自定义机制
        epsilon = self._require_param(params, "epsilon")
        bins = self._require_param(params, "bins")
        query = PrivateHistogramQuery(
            epsilon=epsilon,
            bins=bins,
            mechanism=params.get("mechanism"),
            max_contribution=params.get("max_contribution", 1),
        )
        return query.evaluate(data), (query.epsilon, 0.0)

    def _run_range(self, data: Iterable[Any], params: Dict[str, Any]) -> Tuple[Any, Tuple[float, float]]:
        # 构造区间查询（sum/count/mean），基于一次性噪声前缀表回答多个区间
        epsilon = self._require_param(params, "epsilon")
        bounds = self._require_param(params, "bounds")
        ranges = self._require_param(params, "ranges")
        query = PrivateRangeQuery(
            epsilon=epsilon,
            bounds=bounds,
            mechanism=params.get("mechanism"),
            max_contribution=params.get("max_contribution", 1),
            metric=params.get("metric", "sum"),
            min_count=params.get("min_count", 1e-6),
        )
        return query.evaluate(data, ranges=ranges), (query.epsilon, 0.0)

    # ----------------------------------------------------------- accounting utils
    def _require_param(self, params: Dict[str, Any], name: str) -> Any:
        # 从参数字典中提取必需字段，缺失时抛出统一的 ValidationError
        if name not in params:
            raise ValidationError(f"parameter '{name}' is required")
        return params[name]

    def _record_spend(self, query: str, spend: Tuple[float, float], *, metadata: Optional[Dict[str, Any]]) -> None:
        # 若存在 PrivacyAccountant 则将当前查询的 (ε, δ) 消耗记录为一个事件
        if self._accountant is None:
            return
        epsilon, delta = spend
        self._accountant.add_event(
            epsilon,
            delta,
            description=f"{query} query",
            metadata=metadata or {"query": query},
        )
