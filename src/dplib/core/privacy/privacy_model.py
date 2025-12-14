"""
Privacy model and mechanism registry plus common conversion helpers.

The module centralises:
- Supported privacy models (central/local/RDP/zCDP/GDP/pure) and validation.
- Supported mechanism identifiers used throughout the library.
- Canonical mappings between mechanisms and the privacy models they natively
  deliver (e.g. Gaussian -> CDP/zCDP/RDP/GDP, GRR -> LDP).
- Lightweight conversion helpers across model families.
"""
# 说明：隐私模型与机制类型的注册表模块，集中管理支持的隐私模型/机制标识及其映射关系。
# 职责：
# - PrivacyModel：统一表示 CDP / PURE_DP / LDP / zCDP / RDP / GDP 等隐私模型，并支持字符串构造
# - MechanismType：统一表示拉普拉斯、高斯、指数、GRR、OUE 等机制标识，负责名称规范化
# - MECHANISM_DEFAULT_MODEL / MECHANISM_SUPPORTED_MODELS：声明各机制默认隐私模型及可支持的模型族
# - 一组跨模型族的转换函数（zCDP↔CDP，zCDP→RDP，RDP→CDP，GDP→zCDP/CDP，LDP→CDP）
# - ModelSpec：封装具体隐私模型参数，提供验证、元组导出与统一转换为 CDP 视图的能力
# - ensure_supported_model / registry_snapshot：用于外部工具或文档查询支持的模型/机制组合

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

from dplib.core.utils.param_validation import ensure_type, ParamValidationError
from dplib.core.utils.param_validation import ensure


class PrivacyModel(enum.Enum):
    """Supported privacy models."""
    # 枚举库中支持的隐私模型类型，统一内部表示与字符串 value

    CDP = "cdp"            # (ε, δ)-DP
    PURE_DP = "pure_dp"    # (ε, 0)-DP
    LDP = "ldp"            # local DP (ε)
    ZCDP = "zcdp"          # ρ-zCDP
    RDP = "rdp"            # (α, ε)-RDP
    GDP = "gdp"            # μ-GDP

    @classmethod
    def from_str(cls, name: str) -> "PrivacyModel":
        # 从字符串（大小写不敏感）构造隐私模型，未知名称时抛出参数验证错误
        try:
            return cls(name.lower())
        except Exception as exc:  # pragma: no cover - defensive
            raise ParamValidationError(f"unknown privacy model '{name}'") from exc


class MechanismType(enum.Enum):
    """Supported mechanism identifiers."""
    # 枚举库内常见 DP 机制的短名称，用于机制注册与配置接口

    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    GEOMETRIC = "geometric"
    STAIRCASE = "staircase"
    VECTOR = "vector"
    GRR = "grr"
    OUE = "oue"
    OLH = "olh"
    RAPPOR = "rappor"
    UNARY_RANDOMIZER = "unary_randomizer"
    LOCAL_LAPLACE = "local_laplace"
    LOCAL_GAUSSIAN = "local_gaussian"
    PIECEWISE = "piecewise"
    DUCHI = "duchi"

    @classmethod
    def from_str(cls, name: str) -> "MechanismType":
        # 从字符串构造机制类型，对空格和别名做轻量规范化处理
        try:
            normalized = name.lower().replace(" ", "_")
            if normalized in ("unary", "unary_encoding", "ue"):
                normalized = "unary_randomizer"
            if normalized in ("laplace_local",):
                normalized = "local_laplace"
            if normalized in ("gaussian_local",):
                normalized = "local_gaussian"
            return cls(normalized)
        except Exception as exc:  # pragma: no cover - defensive
            raise ParamValidationError(f"unknown mechanism '{name}'") from exc


# 默认模型：各机制在典型/默认标定方式下自然满足的“首选”隐私模型
MECHANISM_DEFAULT_MODEL: Dict[MechanismType, PrivacyModel] = {
    MechanismType.LAPLACE: PrivacyModel.PURE_DP,
    MechanismType.GAUSSIAN: PrivacyModel.CDP,
    MechanismType.EXPONENTIAL: PrivacyModel.PURE_DP,
    MechanismType.GEOMETRIC: PrivacyModel.PURE_DP,
    MechanismType.STAIRCASE: PrivacyModel.PURE_DP,
    MechanismType.VECTOR: PrivacyModel.CDP,
    MechanismType.GRR: PrivacyModel.LDP,
    MechanismType.OUE: PrivacyModel.LDP,
    MechanismType.OLH: PrivacyModel.LDP,
    MechanismType.RAPPOR: PrivacyModel.LDP,
    MechanismType.UNARY_RANDOMIZER: PrivacyModel.LDP,
    MechanismType.LOCAL_LAPLACE: PrivacyModel.LDP,
    MechanismType.LOCAL_GAUSSIAN: PrivacyModel.LDP,
    MechanismType.PIECEWISE: PrivacyModel.LDP,
    MechanismType.DUCHI: PrivacyModel.LDP,
}

# 可支持模型族：各机制在更精细会计下可以支持的所有隐私模型族（用于能力检查）
MECHANISM_SUPPORTED_MODELS: Dict[MechanismType, Tuple[PrivacyModel, ...]] = {
    MechanismType.LAPLACE: (PrivacyModel.PURE_DP, PrivacyModel.CDP),
    MechanismType.GAUSSIAN: (PrivacyModel.CDP, PrivacyModel.ZCDP, PrivacyModel.RDP, PrivacyModel.GDP),
    MechanismType.EXPONENTIAL: (PrivacyModel.PURE_DP, PrivacyModel.CDP),
    MechanismType.GEOMETRIC: (PrivacyModel.PURE_DP, PrivacyModel.CDP),
    MechanismType.STAIRCASE: (PrivacyModel.PURE_DP, PrivacyModel.CDP),
    MechanismType.VECTOR: (PrivacyModel.CDP,),
    MechanismType.GRR: (PrivacyModel.LDP,),
    MechanismType.OUE: (PrivacyModel.LDP,),
    MechanismType.OLH: (PrivacyModel.LDP,),
    MechanismType.RAPPOR: (PrivacyModel.LDP,),
    MechanismType.UNARY_RANDOMIZER: (PrivacyModel.LDP,),
    MechanismType.LOCAL_LAPLACE: (PrivacyModel.LDP,),
    MechanismType.LOCAL_GAUSSIAN: (PrivacyModel.LDP,),
    MechanismType.PIECEWISE: (PrivacyModel.LDP,),
    MechanismType.DUCHI: (PrivacyModel.LDP,),
}


def mechanism_default_model(mechanism: MechanismType) -> PrivacyModel:
    """Return the canonical privacy model delivered by the mechanism."""
    # 查询给定机制的“默认”隐私模型，用于简化常见配置场景
    return MECHANISM_DEFAULT_MODEL[mechanism]


def mechanism_supports(mechanism: MechanismType, model: PrivacyModel) -> bool:
    """Check whether a mechanism can be analysed under a target model."""
    # 检查机制在声明的支持列表中是否包含目标隐私模型
    return model in MECHANISM_SUPPORTED_MODELS.get(mechanism, ())


def ensure_supported_model(mechanism: MechanismType, model: PrivacyModel) -> None:
    """Raise when a mechanism cannot emit the requested privacy model."""
    # 若机制不支持目标隐私模型，则给出包含支持列表的明确错误提示
    if not mechanism_supports(mechanism, model):
        supported = ", ".join(m.value for m in MECHANISM_SUPPORTED_MODELS.get(mechanism, ()))
        raise ParamValidationError(
            f"mechanism '{mechanism.value}' supports models [{supported}] but got '{model.value}'"
        )


def zcdp_to_cdp(rho: float, delta: float) -> float:
    """
    Convert ρ-zCDP to (ε, δ)-DP using standard bound:
        ε = ρ + 2 * sqrt(ρ * ln(1/δ))
    """
    # 使用标准上界将 ρ-zCDP 转换为 (ε, δ)-DP，并对参数范围做基本校验
    if rho < 0 or delta <= 0 or delta >= 1:
        raise ParamValidationError("rho must be >=0 and delta in (0,1)")
    return rho + 2.0 * math.sqrt(rho * math.log(1.0 / delta))


def cdp_to_zcdp(epsilon: float, delta: float) -> float:
    """
    Approximate conversion from (ε, δ)-DP to ρ-zCDP (loose upper bound):
        ρ = (ε + ln(1/δ))^2 / (2 ln(1/δ))
    """
    # 给出从 (ε, δ)-DP 到 ρ-zCDP 的宽松上界，用于保守估计
    if epsilon < 0 or delta <= 0 or delta >= 1:
        raise ParamValidationError("epsilon must be >=0 and delta in (0,1)")
    term = epsilon + math.log(1.0 / delta)
    return (term * term) / (2.0 * math.log(1.0 / delta))


def zcdp_to_rdp(rho: float, order: float) -> float:
    """Convert ρ-zCDP to (α, ε)-RDP via ε = α·ρ."""
    # 使用简单线性关系将 ρ-zCDP 转换为给定阶 alpha 的 RDP 参数
    if rho < 0:
        raise ParamValidationError("rho must be >=0")
    if order <= 1:
        raise ParamValidationError("rdp order must be > 1")
    return order * rho


def rdp_to_cdp(order: float, rdp_epsilon: float, delta: float) -> float:
    """
    Convert (α, ε)-RDP to (ε', δ)-DP using ε' = ε + ln(1/δ)/(α-1).
    """
    # 根据标准不等式将 RDP 保证换算为 (ε', δ)-DP，便于与 CDP 会计对齐
    if order <= 1:
        raise ParamValidationError("rdp order must be > 1")
    if rdp_epsilon < 0:
        raise ParamValidationError("rdp epsilon must be >=0")
    if delta <= 0 or delta >= 1:
        raise ParamValidationError("delta must be in (0,1)")
    return rdp_epsilon + math.log(1.0 / delta) / (order - 1.0)


def gdp_to_zcdp(mu: float) -> float:
    """Convert μ-GDP to ρ-zCDP using ρ = μ^2 / 2."""
    # 将 μ-GDP 转换为 ρ-zCDP，后者可进一步转换到 CDP 或 RDP 框架
    if mu <= 0:
        raise ParamValidationError("mu must be > 0")
    return 0.5 * mu * mu


def gdp_to_cdp(mu: float, delta: float) -> float:
    """
    Convert μ-GDP to (ε, δ)-DP via the zCDP bridge (ρ = μ^2/2).
    """
    # 通过“GDP → zCDP → CDP”桥接链路，得到等价的 (ε, δ)-DP 预算
    rho = gdp_to_zcdp(mu)
    return zcdp_to_cdp(rho, delta)


def ldp_to_cdp(epsilon: float) -> Tuple[float, float]:
    """Map local DP budget to its central counterpart with δ=0."""
    # 将局部 ε-LDP 映射为中心 DP 模型下的 (ε, 0)-DP
    if epsilon < 0:
        raise ParamValidationError("epsilon must be >=0")
    return float(epsilon), 0.0


@dataclass(frozen=True)
class ModelSpec:
    """Explicit model parameters wrapper."""
    # 用于携带“模型类型 + 对应参数”的不可变配置体，方便在 API 与会计器之间传递

    model: PrivacyModel
    epsilon: Optional[float] = None
    delta: Optional[float] = None
    rho: Optional[float] = None
    alpha: Optional[float] = None   # RDP order
    mu: Optional[float] = None      # GDP parameter

    def validate(self) -> "ModelSpec":
        # 根据 model 类型，检查必须提供的参数及其数值范围（非法时由 ensure 抛错）
        ensure_type(self.model, PrivacyModel, label="model")

        if self.model in (PrivacyModel.LDP, PrivacyModel.PURE_DP):
            ensure_type(self.epsilon, (float, int), label="epsilon")
            ensure(self.epsilon >= 0, "epsilon must be >= 0")
        elif self.model == PrivacyModel.CDP:
            ensure_type(self.epsilon, (float, int), label="epsilon")
            ensure_type(self.delta, (float, int), label="delta")
            ensure(self.epsilon >= 0, "epsilon must be >= 0")
            ensure(0 < self.delta < 1, "delta must be in (0,1)")
        elif self.model == PrivacyModel.ZCDP:
            ensure_type(self.rho, (float, int), label="rho")
            ensure(self.rho >= 0, "rho must be >= 0")
        elif self.model == PrivacyModel.RDP:
            ensure_type(self.alpha, (float, int), label="alpha")
            ensure_type(self.epsilon, (float, int), label="epsilon")
            ensure(self.alpha > 1, "rdp order must be > 1")
            ensure(self.epsilon >= 0, "rdp epsilon must be >= 0")
        elif self.model == PrivacyModel.GDP:
            ensure_type(self.mu, (float, int), label="mu")
            ensure(self.mu > 0, "mu must be > 0")
        return self

    def to_tuple(self) -> Tuple:
        # 将模型及其参数导出为简洁元组表示，用于序列化或作为 dict 键
        if self.model in (PrivacyModel.LDP, PrivacyModel.PURE_DP):
            return (self.model.value, float(self.epsilon))
        if self.model == PrivacyModel.CDP:
            return (self.model.value, float(self.epsilon), float(self.delta))
        if self.model == PrivacyModel.ZCDP:
            return (self.model.value, float(self.rho))
        if self.model == PrivacyModel.RDP:
            return (self.model.value, float(self.alpha), float(self.epsilon))
        if self.model == PrivacyModel.GDP:
            return (self.model.value, float(self.mu))
        raise ParamValidationError("unsupported privacy model")

    def to_parameters(self) -> Dict[str, float]:
        """Return the numeric parameters attached to this spec."""
        # 以 {参数名: 数值} 的形式导出当前 spec 中实际存在的数值参数
        params = {
            "epsilon": self.epsilon,
            "delta": self.delta,
            "rho": self.rho,
            "alpha": self.alpha,
            "mu": self.mu,
        }
        return {key: float(value) for key, value in params.items() if value is not None}

    def as_cdp(self, *, delta: Optional[float] = None, rdp_order: Optional[float] = None) -> "ModelSpec":
        """
        Convert the current spec to (epsilon, delta)-DP representation where possible.
        - delta: optional target delta when converting from zCDP/RDP/GDP.
        - rdp_order: override RDP order; defaults to the spec's alpha.
        """
        # 尝试将当前模型统一表示为 CDP（如已是 CDP 则原样返回），无法转换时抛出错误
        self.validate()
        if self.model == PrivacyModel.CDP:
            return self
        if self.model in (PrivacyModel.LDP, PrivacyModel.PURE_DP):
            eps, dlt = ldp_to_cdp(float(self.epsilon))
            return ModelSpec(model=PrivacyModel.CDP, epsilon=eps, delta=dlt)
        if self.model == PrivacyModel.ZCDP:
            # zCDP 需要目标 delta，将其映射为 CDP
            target_delta = delta if delta is not None else (self.delta or 1e-6)
            eps = zcdp_to_cdp(float(self.rho), target_delta)
            return ModelSpec(model=PrivacyModel.CDP, epsilon=eps, delta=target_delta)
        if self.model == PrivacyModel.RDP:
            # RDP 转 CDP 时需要阶数 alpha；可由参数或 spec 本身提供
            order = rdp_order if rdp_order is not None else self.alpha
            if order is None:
                raise ParamValidationError("rdp order required for conversion to cdp")
            target_delta = delta if delta is not None else (self.delta or 1e-6)
            eps = rdp_to_cdp(float(order), float(self.epsilon), float(target_delta))
            return ModelSpec(model=PrivacyModel.CDP, epsilon=eps, delta=target_delta, alpha=float(order))
        if self.model == PrivacyModel.GDP:
            # GDP 通过 zCDP 桥接转换到 CDP
            target_delta = delta if delta is not None else (self.delta or 1e-6)
            eps = gdp_to_cdp(float(self.mu), float(target_delta))
            return ModelSpec(model=PrivacyModel.CDP, epsilon=eps, delta=target_delta)
        raise ParamValidationError("cannot convert model spec to cdp")


def registry_snapshot() -> Dict[str, Iterable[str]]:
    """
    Snapshot of supported identifiers for external tooling or documentation.
    """
    # 返回当前注册表中支持的隐私模型和机制标识快照，便于外部工具或文档生成使用
    return {
        "privacy_models": [m.value for m in PrivacyModel],
        "mechanisms": [m.value for m in MechanismType],
    }
