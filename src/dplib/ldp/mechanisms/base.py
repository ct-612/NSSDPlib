"""Base class for Local Differential Privacy mechanisms."""
# 说明：本地差分隐私（LDP）机制的统一基类，约定隐私模型、参数校验与报表封装接口。
# 职责：
# - 将 privacy_model 固定为 LDP 并在构造阶段校验 epsilon 合法性与类型
# - 提供 generate_report 统一构造 LDPReport 的入口，封装扰动值与用户/轮次元数据
# - 兼容 BaseMechanism 的序列化/反序列化接口，同时将敏感度标定退化为空操作

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Optional, Union

from dplib.core.privacy.base_mechanism import BaseMechanism, ValidationError
from dplib.core.privacy.privacy_model import PrivacyModel
from dplib.ldp.ldp_utils import ensure_epsilon
from dplib.ldp.types import EncodedValue, LDPReport


class BaseLDPMechanism(BaseMechanism, ABC):
    """
    Common base class for all LDP mechanisms.

    Guarantees `privacy_model = PrivacyModel.LDP`, validates epsilon, and
    provides a unified report constructor for downstream aggregators.
    """

    privacy_model: PrivacyModel = PrivacyModel.LDP

    def __init__(
        self,
        epsilon: float,
        delta: float = 0.0,
        *,
        identifier: Optional[str] = None,
        rng: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        # 在初始化阶段通过 ensure_epsilon 包装 ValidationError 统一校验 epsilon 合法性
        try:
            ensure_epsilon(epsilon)
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
        self._identifier = identifier
        super().__init__(epsilon=epsilon, delta=delta, rng=rng, name=name or identifier) 
        # LDP 机制通常不需要基于全局敏感度的标定流程
        self.calibrate()

    @property
    def mechanism_id(self) -> str:
        """Stable identifier (explicit identifier if provided, else class-derived)."""
        # 返回显式提供的 identifier，若为空则回退到基类根据类名等规则生成的机制标识
        return self._identifier or super().mechanism_id

    @abstractmethod
    def randomise(self, value: EncodedValue) -> EncodedValue:
        """Apply mechanism-specific perturbation to an encoded local value."""
        # 在子类中实现具体的本地扰动策略，对单个 EncodedValue 应用机制特定的随机化
        raise NotImplementedError

    def generate_report(
        self,
        value: EncodedValue,
        *,
        user_id: Optional[Union[str, int]] = None,
        round_id: Optional[Union[str, int]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> LDPReport:
        """
        Perturb the provided value and wrap it as an LDPReport for aggregation.
        """
        # 调用 randomise 生成扰动值并合并内部元数据与调用方元信息，封装为 LDPReport 供聚合端消费
        perturbed = self.randomise(value)
        report_metadata = dict(self._meta)
        if metadata:
            report_metadata.update(metadata)

        return LDPReport(
            user_id=user_id,
            mechanism_id=self.mechanism_id,
            encoded=perturbed,
            epsilon=self.epsilon,
            delta=self.delta,
            round_id=round_id,
            metadata=report_metadata,
        )

    # LDP 机制很少依赖敏感度参数进行标定，此处保持空实现占位钩子行为
    def _calibrate_parameters(self, *, sensitivity: Optional[float] = None, **kwargs: Any) -> None:
        # 覆盖基类的标定入口以忽略敏感度和其他参数，保持接口兼容又不引入多余计算
        del sensitivity, kwargs

    def serialize(self) -> dict[str, Any]:
        """Include privacy model and identifier in the serialized snapshot."""
        # 在基类序列化结果基础上补充 LDP 隐私模型标记与机制 identifier 字段
        base = super().serialize()
        base.update(
            {
                "privacy_model": self.privacy_model.value,
                "identifier": self._identifier,
            }
        )
        return base

    @classmethod
    def deserialize(cls, data: Mapping[str, Any]) -> "BaseLDPMechanism":
        """
        Restore a mechanism from serialized data produced by `serialize`.
        """
        # 从序列化字典中校验 epsilon 字段是否存在并重建机制实例，同时恢复 meta 与 calibrated 状态
        if "epsilon" not in data:
            raise ValidationError("serialized data missing 'epsilon' field")
        inst = cls(
            epsilon=float(data["epsilon"]),
            delta=float(data.get("delta", 0.0)),
            identifier=data.get("identifier") or data.get("mechanism"),
            rng=None,
            name=data.get("name"),
        )
        inst._meta = dict(data.get("meta", {}))
        inst._calibrated = bool(data.get("calibrated", False))
        return inst
