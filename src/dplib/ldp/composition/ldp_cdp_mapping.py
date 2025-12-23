"""
Default LDP-to-CDP mapping strategies for accounting bridges.

Responsibilities
  - Define recommended metadata keys for delta and mechanism parameters.
  - Provide default mapping from LocalPrivacyUsage to LDPToCDPEvent.
  - Normalize LDP context metadata for CDP audit logs.

Usage Context
  - Use when forwarding local DP usage into CDP accounting.
  - Intended for consistent metadata mapping across systems.

Limitations
  - Mapping relies on metadata keys provided by callers.
  - Does not infer mechanism parameters beyond provided metadata.
"""
# 说明：提供 LDP 到 CDP 的默认映射策略与辅助工具。
# 职责：
# - 明确 metadata 中 delta 与 mechanism 参数的推荐字段名
# - 提供 LocalPrivacyUsage 到 LDPToCDPEvent 的默认映射函数
# - 统一补齐 ldp_context 元数据便于混合审计

from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Sequence

from dplib.core.utils.param_validation import ParamValidationError
from dplib.ldp.types import LDPToCDPEvent, LocalPrivacyUsage
from .compose import ANONYMOUS_USER_KEY


RECOMMENDED_DELTA_KEY = "delta"
# 推荐字段名：metadata["delta"] 用于 CDP delta

RECOMMENDED_MECHANISM_KEY = "mechanism"
# 推荐字段名：metadata["mechanism"] 用于机制名称

RECOMMENDED_MECHANISM_PARAMS_KEY = "mechanism_params"
# 推荐字段名：metadata["mechanism_params"] 用于机制参数

FALLBACK_DELTA_KEYS = ("cdp_delta", "ldp_delta")
# 兼容字段名：delta 的替代字段

FALLBACK_MECHANISM_KEYS = ("mechanism_id", "mechanism_name")
# 兼容字段名：机制名称的替代字段

FALLBACK_MECHANISM_PARAMS_KEYS = ("parameters", "mechanism_parameters")
# 兼容字段名：机制参数的替代字段


LDPToCDPMapper = Callable[[LocalPrivacyUsage], LDPToCDPEvent]
# LDP usage 到 CDP 事件的映射策略类型别名


def _extract_first(metadata: Mapping[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    # 按顺序查找 metadata 中的字段并返回首个匹配值
    for key in keys:
        if key in metadata:
            return metadata[key]
    return default


def _coerce_non_negative_delta(value: Any) -> float:
    # 将输入转换为非负 delta 并用于映射策略校验
    try:
        delta = float(value)
    except (TypeError, ValueError) as exc:
        raise ParamValidationError("delta must be convertible to float") from exc
    if delta < 0:
        raise ParamValidationError("delta must be non-negative")
    return delta


def _normalize_parameters(parameters: Any) -> Dict[str, Any]:
    # 归一化机制参数为可序列化字典形式
    if parameters is None:
        return {}
    if isinstance(parameters, Mapping):
        return dict(parameters)
    return {"value": parameters}


def default_ldp_to_cdp_mapper(usage: LocalPrivacyUsage) -> LDPToCDPEvent:
    # 使用 metadata 中的推荐字段生成默认 LDP 到 CDP 映射
    metadata = dict(usage.metadata)
    delta_value = _extract_first(
        metadata,
        (RECOMMENDED_DELTA_KEY,) + FALLBACK_DELTA_KEYS,
        0.0,
    )
    delta = _coerce_non_negative_delta(delta_value)
    mechanism = _extract_first(
        metadata,
        (RECOMMENDED_MECHANISM_KEY,) + FALLBACK_MECHANISM_KEYS,
        None,
    )
    parameters = _extract_first(
        metadata,
        (RECOMMENDED_MECHANISM_PARAMS_KEY,) + FALLBACK_MECHANISM_PARAMS_KEYS,
        {},
    )
    return LDPToCDPEvent(
        epsilon=float(usage.epsilon),
        delta=delta,
        description=metadata.get("description") or "LDP-local-event",
        metadata=metadata,
        mechanism=mechanism,
        parameters=_normalize_parameters(parameters),
    )


def normalize_cdp_event(usage: LocalPrivacyUsage, event: LDPToCDPEvent) -> LDPToCDPEvent:
    # 将 user 与机制上下文合并进 metadata 并填充默认描述
    metadata = dict(event.metadata or {})
    context = metadata.get("ldp_context")
    if isinstance(context, Mapping):
        context = dict(context)
    else:
        context = {}
    user_key = ANONYMOUS_USER_KEY if usage.user_id is None else str(usage.user_id)
    context.setdefault("user_id", user_key)
    if usage.round_id is not None:
        context.setdefault("round_id", usage.round_id)
    context.setdefault("source", "ldp")
    if event.mechanism is not None:
        context.setdefault("mechanism", event.mechanism)
    parameters = _normalize_parameters(event.parameters)
    if parameters:
        context.setdefault("mechanism_params", dict(parameters))
    delta_value = event.delta if event.delta is not None else 0.0
    delta = _coerce_non_negative_delta(delta_value)
    context.setdefault("delta", delta)
    metadata["ldp_context"] = context
    return LDPToCDPEvent(
        epsilon=float(event.epsilon),
        delta=delta,
        description=event.description or "LDP-local-event",
        metadata=metadata,
        mechanism=event.mechanism,
        parameters=parameters,
    )


LDP_TO_CDP_MAPPERS: Dict[str, LDPToCDPMapper] = {
    "default": default_ldp_to_cdp_mapper,
}
# 内置映射策略集合，默认使用 default
