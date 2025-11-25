"""
Privacy guarantee representations used for audit/reporting.
Provides a structured container with validation, conversion, and serialisation
helpers that align with the privacy model registry.
"""
# 说明：审计 / 报告阶段使用的隐私保证表示容器，实现与隐私模型注册表对齐的结构化描述。
# 职责：
# - PrivacyGuarantee：封装隐私模型、机制类型及其数值参数（epsilon/delta/rho/alpha/mu）和元信息
# - 提供 validate() / as_cdp_view() 等方法，用于校验模型配置、机制支持情况和模型间转换
# - 提供 to_dict() / to_report() 等方法，将隐私保证转换为可记录、可下游消费的结构化负载
# - 与 privacy_model 模块中的 ModelSpec / MechanismType / PrivacyModel 等保持类型与语义一致

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from .privacy_model import (
    MechanismType,
    ModelSpec,
    PrivacyModel,
    ensure_supported_model,
    mechanism_supports,
)
from dplib.core.utils.param_validation import ParamValidationError


@dataclass
class PrivacyGuarantee:
    """Container describing a privacy guarantee for audit/reporting."""

    model: PrivacyModel
    mechanism: Optional[MechanismType] = None
    epsilon: Optional[float] = None
    delta: Optional[float] = None
    rho: Optional[float] = None
    alpha: Optional[float] = None
    mu: Optional[float] = None
    description: Optional[str] = None
    proof: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> "PrivacyGuarantee":
        # 使用 ModelSpec 执行参数级别的合法性校验，并检查机制是否支持指定隐私模型
        spec = self.to_model_spec().validate()
        if self.mechanism is not None:
            ensure_supported_model(self.mechanism, spec.model)
        return self

    def to_dict(self) -> Dict[str, Any]:
        # 导出为简单的字典结构，保留原始字段与数值参数快照，方便序列化或日志记录
        parameters = self.to_model_spec().to_parameters()
        return {
            "mechanism": self.mechanism.value if self.mechanism else None,
            "model": self.model.value,
            "epsilon": self.epsilon,
            "delta": self.delta,
            "rho": self.rho,
            "alpha": self.alpha,
            "mu": self.mu,
            "parameters": parameters,
            "description": self.description,
            "proof": self.proof,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_model_spec(
        cls,
        spec: ModelSpec,
        *,
        mechanism: Optional[MechanismType] = None,
        **kwargs: Any,
    ) -> "PrivacyGuarantee":
        # 从已验证的 ModelSpec 构造 PrivacyGuarantee，并按模型类型选择性填充参数
        spec.validate()
        if mechanism is not None and not mechanism_supports(mechanism, spec.model):
            ensure_supported_model(mechanism, spec.model)
        if spec.model == PrivacyModel.PURE_DP:
            return cls(model=spec.model, mechanism=mechanism, epsilon=float(spec.epsilon), **kwargs)
        if spec.model == PrivacyModel.LDP:
            return cls(model=spec.model, mechanism=mechanism, epsilon=float(spec.epsilon), **kwargs)
        if spec.model == PrivacyModel.CDP:
            return cls(
                model=spec.model,
                mechanism=mechanism,
                epsilon=float(spec.epsilon),
                delta=float(spec.delta),
                **kwargs,
            )
        if spec.model == PrivacyModel.ZCDP:
            return cls(model=spec.model, mechanism=mechanism, rho=float(spec.rho), **kwargs)
        if spec.model == PrivacyModel.RDP:
            return cls(
                model=spec.model,
                mechanism=mechanism,
                epsilon=float(spec.epsilon),
                alpha=float(spec.alpha),
                **kwargs,
            )
        if spec.model == PrivacyModel.GDP:
            return cls(model=spec.model, mechanism=mechanism, mu=float(spec.mu), **kwargs)
        raise ParamValidationError("unsupported model spec")

    def to_model_spec(self) -> ModelSpec:
        """Materialise the underlying ModelSpec for validation/conversion."""
        # 将当前实例中的数值参数打包为 ModelSpec，用于统一的校验和模型转换逻辑
        return ModelSpec(
            model=self.model,
            epsilon=self.epsilon,
            delta=self.delta,
            rho=self.rho,
            alpha=self.alpha,
            mu=self.mu,
        )

    def as_cdp_view(self, delta: Optional[float] = None, rdp_order: Optional[float] = None) -> "PrivacyGuarantee":
        """
        Convert guarantee to (epsilon, delta)-DP form when possible.
        For zCDP/RDP/GDP, requires a target delta to compute equivalent epsilon.
        """
        # 将当前保证转换为 CDP 视图，并保留说明、证明与元数据
        spec = self.to_model_spec().as_cdp(delta=delta, rdp_order=rdp_order)
        return PrivacyGuarantee(
            model=PrivacyModel.CDP,
            mechanism=self.mechanism,
            epsilon=spec.epsilon,
            delta=spec.delta,
            description=self.description,
            proof=self.proof,
            meta=dict(self.meta),
        )

    def to_report(self) -> Dict[str, Any]:
        """
        Structured report payload for logging or audit sinks.
        """
        # 生成适合审计 / 日志下游消费的结构化报告负载，并内联参数摘要字符串
        self.validate()
        parameters = self.to_model_spec().to_parameters()
        summary: Tuple[str, ...] = tuple(f"{k}={v}" for k, v in parameters.items())
        return {
            "mechanism": self.mechanism.value if self.mechanism else None,
            "model": self.model.value,
            "parameters": parameters,
            "summary": ", ".join(summary),
            "description": self.description,
            "proof": self.proof,
            "meta": dict(self.meta),
        }
