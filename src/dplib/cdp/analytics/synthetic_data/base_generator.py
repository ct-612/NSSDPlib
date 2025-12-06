"""
Synthetic data generator abstractions.

Responsibilities:
    * provide a unified entry-point for DP synthetic data methods
    * manage common configuration, RNG plumbing, and privacy accounting hooks
    * expose `fit` / `sample` lifecycle plus serialisation helpers
"""
# 说明：差分隐私合成数据生成器的抽象基类与配置结构，统一 fit/sample 接口、随机数与隐私记账挂钩。
# 职责：
# - SyntheticGeneratorConfig：封装 method/epsilon/delta/seed 等基础配置，支持 dict 往返
# - SyntheticDataGenerator：抽象基类，负责标准化输入 Dataset、RNG 复用、隐私预算扣减与配置序列化
# - create_generator：简单工厂，按 method 延迟导入具体子类（marginal/bayesian/gan/copula）
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Type, TypeVar, Union, TYPE_CHECKING

import numpy as np

from dplib.core.data import Dataset, DatasetError, DatasetMetadata, BaseDomain
from dplib.core.privacy import PrivacyModel, PrivacyGuarantee
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.core.utils.random import create_rng

if TYPE_CHECKING:  # pragma: no cover - type hints only
    from dplib.cdp.composition.privacy_accountant import CDPPrivacyAccountant
    from dplib.core.privacy.budget_tracker import BudgetTracker, TrackedScope
else:  # pragma: no cover - runtime fallback
    CDPPrivacyAccountant = Any  # type: ignore
    BudgetTracker = Any  # type: ignore
    TrackedScope = Any  # type: ignore


Domain = Union[BaseDomain, Mapping[str, BaseDomain]]
DataLike = Union[Dataset, Iterable[Mapping[str, Any]], np.ndarray]
SampleLike = Union[Dataset, Mapping[str, np.ndarray], np.ndarray]
TGenerator = TypeVar("TGenerator", bound="SyntheticDataGenerator")


@dataclass
class SyntheticGeneratorConfig:
    """Lightweight configuration container for synthetic data generators."""

    method: str
    epsilon: float
    delta: float = 0.0
    seed: Optional[int] = None
    privacy_model: PrivacyModel = PrivacyModel.CDP
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        # 序列化为 JSON 友好的字典表示，extra 做浅拷贝以避免外部修改
        return {
            "method": self.method,
            "epsilon": float(self.epsilon),
            "delta": float(self.delta),
            "seed": self.seed,
            "privacy_model": self.privacy_model.value,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SyntheticGeneratorConfig":
        # 从字典构造配置，校验必需字段与基本类型
        ensure("method" in payload, "config must include 'method'", error=ParamValidationError)
        ensure("epsilon" in payload, "config must include 'epsilon'", error=ParamValidationError)
        method = str(payload["method"])
        epsilon = float(payload.get("epsilon", 0.0))
        delta = float(payload.get("delta", 0.0))
        seed = payload.get("seed")
        privacy_model_value = payload.get("privacy_model", PrivacyModel.CDP.value)
        privacy_model = privacy_model_value if isinstance(privacy_model_value, PrivacyModel) else PrivacyModel.from_str(str(privacy_model_value))
        extra = dict(payload.get("extra") or {})
        return cls(
            method=method,
            epsilon=epsilon,
            delta=delta,
            seed=None if seed is None else int(seed),
            privacy_model=privacy_model,
            extra=extra,
        )


class SyntheticDataGenerator(ABC):
    """
    Abstract base class for DP synthetic data generators.

    Subclasses only implement `_fit_internal` and `_sample_internal`; all
    common plumbing (dataset normalisation, RNG, privacy accounting, config
    round-trips) is handled here.
    """

    method: str = "base"

    def __init__(
        self,
        domain: Domain,
        epsilon: float,
        *,
        delta: float = 0.0,
        privacy_model: PrivacyModel = PrivacyModel.CDP,
        accountant: Optional["CDPPrivacyAccountant"] = None,
        budget_tracker: Optional["BudgetTracker"] = None,
        budget_scope: Optional["TrackedScope"] = None,
        rng: Optional[np.random.Generator] = None,
        seed: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ):
        # 初始化生成器的域信息、隐私参数以及记账器与预算跟踪器等外部依赖
        self.domain = domain
        self.epsilon = float(epsilon)
        self.delta = float(delta)
        self.privacy_model = privacy_model
        self.accountant = accountant
        self.budget_tracker = budget_tracker
        self._budget_scope = budget_scope
        self._seed = seed
        self._rng = create_rng(rng or seed) if (rng is not None or seed is not None) else None
        self._metadata = dict(metadata or {})

    # ------------------------------------------------------------------ lifecycle
    def fit(self: TGenerator, data: DataLike) -> TGenerator:
        """Public entry to fit the generator on a dataset."""
        # 将输入数据统一转换为 Dataset 并委托子类实现进行拟合
        dataset = self._coerce_dataset(data)
        self._fit_internal(dataset)
        return self

    def sample(self, n: int, *, as_dataset: bool = True) -> SampleLike:
        """Sample `n` synthetic records; optionally wrap as Dataset."""
        # 采样指定数量的合成记录并根据 as_dataset 控制是否包装为 Dataset
        ensure(n > 0, "sample size must be positive", error=ParamValidationError)
        raw = self._sample_internal(int(n))
        if not as_dataset:
            return raw
        return self._wrap_as_dataset(raw)

    # ---------------------------------------------------------------- privacy/RNG
    def get_privacy_spent(self) -> Union[PrivacyGuarantee, Tuple[float, float]]:
        """Return current privacy spending from attached accountant or fall back to configured epsilon/delta."""
        # 优先从绑定的记账器读取当前隐私消耗否则退化为构造时配置的 epsilon/delta
        if self.accountant is not None:
            spent = getattr(self.accountant, "spent", None)
            if isinstance(spent, tuple):
                eps, dlt = spent
            elif hasattr(spent, "epsilon"):
                eps, dlt = float(spent.epsilon), float(getattr(spent, "delta", 0.0))
            else:  # pragma: no cover - defensive
                eps, dlt = self.epsilon, self.delta
            return PrivacyGuarantee(
                model=self.privacy_model,
                epsilon=float(eps),
                delta=float(dlt),
                meta={"source": self.__class__.__name__},
            )
        return float(self.epsilon), float(self.delta)

    def _require_rng(self) -> np.random.Generator:
        """Ensure an RNG is available (using provided seed if needed)."""
        # 懒加载内部 RNG 实例优先复用已有种子以保证采样可重现
        if self._rng is None:
            self._rng = create_rng(self._seed)
        return self._rng

    def _consume_budget(self, epsilon: float, delta: float = 0.0, *, description: Optional[str] = None) -> None:
        """Record privacy spending to attached accountant/budget tracker if present."""
        # 将一次操作的隐私支出同步到记账器与预算跟踪器并附带描述与元数据以便审计
        desc = description or f"{self.__class__.__name__} spend"
        meta = {"generator": self.__class__.__name__}

        if self.accountant is not None:
            try:
                # 适配多种记账器接口优先调用 add_event 回退到内部 _accountant 或组合事件接口
                if hasattr(self.accountant, "add_event"):
                    self.accountant.add_event(epsilon, delta, description=desc, metadata=meta)  # type: ignore[arg-type]
                elif hasattr(self.accountant, "_accountant"):
                    inner = getattr(self.accountant, "_accountant")
                    if hasattr(inner, "add_event"):
                        inner.add_event(epsilon, delta, description=desc, metadata=meta)  # type: ignore[arg-type]
                elif hasattr(self.accountant, "add_composed_event"):
                    self.accountant.add_composed_event([{"epsilon": epsilon, "delta": delta}], description=desc, metadata=meta)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - defensive
                pass

        if self.budget_tracker is not None and hasattr(self.budget_tracker, "spend"):
            try:
                # 如未显式指定作用域则在存在唯一可用 scope 时自动推断默认作用域
                scope = self._budget_scope
                if scope is None and hasattr(self.budget_tracker, "scopes"):
                    scopes = tuple(self.budget_tracker.scopes())  # type: ignore[call-arg]
                    if len(scopes) == 1:
                        scope = scopes[0]
                if scope is not None:
                    self.budget_tracker.spend(scope, epsilon, delta, description=desc, metadata=meta)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - defensive
                pass

    # ---------------------------------------------------------------- serialization
    def to_config(self) -> Mapping[str, Any]:
        """Export generator configuration (excluding learned parameters)."""
        # 导出当前生成器的静态配置与方法特定参数便于持久化与复现
        cfg = SyntheticGeneratorConfig(
            method=getattr(self, "method", self.__class__.__name__.lower()),
            epsilon=self.epsilon,
            delta=self.delta,
            seed=self._seed,
            privacy_model=self.privacy_model,
            extra=self._config_extra(),
        )
        payload = cfg.to_dict()
        if self._metadata:
            payload["metadata"] = dict(self._metadata)
        return payload

    @classmethod
    def from_config(
        cls: Type[TGenerator],
        domain: Domain,
        config: SyntheticGeneratorConfig | Mapping[str, Any],
        *,
        accountant: Optional["CDPPrivacyAccountant"] = None,
        budget_tracker: Optional["BudgetTracker"] = None,
        budget_scope: Optional["TrackedScope"] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> TGenerator:
        """Construct a generator from configuration."""
        # 从配置对象或字典恢复生成器实例并校验 method 与类属性 method 一致
        cfg = config if isinstance(config, SyntheticGeneratorConfig) else SyntheticGeneratorConfig.from_dict(config)
        expected = getattr(cls, "method", None)
        if expected and cfg.method.lower() != str(expected).lower():
            raise ParamValidationError(f"config method '{cfg.method}' does not match generator '{expected}'")
        rng = create_rng(cfg.seed) if cfg.seed is not None else None
        extra = dict(cfg.extra)
        extra.update(kwargs)
        return cls(
            domain=domain,
            epsilon=cfg.epsilon,
            delta=cfg.delta,
            privacy_model=cfg.privacy_model,
            accountant=accountant,
            budget_tracker=budget_tracker,
            budget_scope=budget_scope,
            rng=rng,
            seed=cfg.seed,
            metadata=metadata,
            **extra,
        )

    # ------------------------------------------------------------------ internals
    def _coerce_dataset(self, data: DataLike) -> Dataset:
        """Normalise input data into a Dataset instance."""
        # 接受 Dataset/ndarray/记录迭代器等多种输入并统一归一化为 Dataset
        if isinstance(data, Dataset):
            return data
        if isinstance(data, np.ndarray):
            return self._dataset_from_array(data)
        if isinstance(data, Iterable):
            records = list(data)
            if not records:
                return Dataset([], metadata=DatasetMetadata(format="records"))
            if isinstance(records[0], Mapping):
                return Dataset.from_records(records)  # type: ignore[arg-type]
            raise DatasetError("iterable inputs must yield mapping records for synthetic generators")
        raise DatasetError("unsupported data input type for synthetic generator")

    def _dataset_from_array(self, values: np.ndarray) -> Dataset:
        """Wrap a 2-D numpy array into a Dataset using domain field names when available."""
        # 将二维数组视为按列字段的表格并结合域字段名或自动生成列名构造 Dataset
        arr = np.asarray(values)
        if arr.ndim != 2:
            raise DatasetError("ndarray input must be 2-D for synthetic generators")
        field_names = self._domain_fields()
        if field_names and len(field_names) != arr.shape[1]:
            raise DatasetError("number of columns does not match domain fields")
        columns = field_names or tuple(f"col_{idx}" for idx in range(arr.shape[1]))
        records = [dict(zip(columns, row.tolist())) for row in arr]
        return Dataset.from_records(records)

    def _wrap_as_dataset(self, sample: SampleLike) -> Dataset:
        """Coerce sample output into Dataset for downstream consumers."""
        # 将多种可能的采样输出形式转换为 Dataset 统一给下游消费
        if isinstance(sample, Dataset):
            return sample
        if isinstance(sample, Mapping):
            return Dataset.from_arrays(sample)  # type: ignore[arg-type]
        if isinstance(sample, np.ndarray):
            return self._dataset_from_array(sample)
        raise DatasetError("unsupported sample output type")

    def _domain_fields(self) -> Tuple[str, ...]:
        """Best-effort extraction of field names from domain if it is mapping-like."""
        # 若 domain 为映射类型则使用键集合作为字段名否则返回空元组
        if isinstance(self.domain, Mapping):
            return tuple(self.domain.keys())
        return tuple()

    def _config_extra(self) -> Dict[str, Any]:
        """Hook for subclasses to append method-specific config values."""
        # 子类可覆盖该方法以在配置导出时附加方法相关的额外参数
        return {}

    # ---------------------------------------------------------------- abstract hooks
    @abstractmethod
    def _fit_internal(self, dataset: Dataset) -> None:
        """Subclasses implement DP model fitting here."""
        # 抽象接口由具体合成模型子类实现拟合阶段逻辑
        ...

    @abstractmethod
    def _sample_internal(self, n: int) -> SampleLike:
        """Subclasses implement sampling logic here."""
        # 抽象接口由具体合成模型子类实现采样阶段逻辑
        ...


# --------------------------------------------------------------------------- factory
def create_generator(
    method: str,
    domain: Domain,
    config: SyntheticGeneratorConfig | Mapping[str, Any],
    *,
    accountant: Optional["CDPPrivacyAccountant"] = None,
    budget_tracker: Optional["BudgetTracker"] = None,
    metadata: Optional[Mapping[str, Any]] = None,
    **kwargs: Any,
) -> SyntheticDataGenerator:
    """
    Factory helper that instantiates a generator by method name.

    Lazy imports are used to avoid circular dependencies when multiple
    generators share helpers.
    """
    # 根据 method 字符串选择具体生成器子类并通过 from_config 构造实例避免提前导入带来的循环依赖

    normalized = method.lower()
    if normalized == "marginal":
        from .marginal import MarginalGenerator

        return MarginalGenerator.from_config(
            domain=domain,
            config=config,
            accountant=accountant,
            budget_tracker=budget_tracker,
            metadata=metadata,
            **kwargs,
        )
    if normalized == "bayesian":
        from .bayesian import BayesianNetworkGenerator

        return BayesianNetworkGenerator.from_config(
            domain=domain,
            config=config,
            accountant=accountant,
            budget_tracker=budget_tracker,
            metadata=metadata,
            **kwargs,
        )
    if normalized == "gan":
        from .gan import DPSyntheticGAN

        return DPSyntheticGAN.from_config(
            domain=domain,
            config=config,
            accountant=accountant,
            budget_tracker=budget_tracker,
            metadata=metadata,
            **kwargs,
        )
    if normalized == "copula":
        from .copula import CopulaGenerator

        return CopulaGenerator.from_config(
            domain=domain,
            config=config,
            accountant=accountant,
            budget_tracker=budget_tracker,
            metadata=metadata,
            **kwargs,
        )
    raise ParamValidationError(f"unknown synthetic data generation method '{method}'")
