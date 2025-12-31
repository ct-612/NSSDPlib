"""
Backend registry helpers for the CDP ML subsystem.

Responsibilities
  - Define backend capability and specification data structures.
  - Provide backend detection and lookup utilities.
  - Centralize optional dependency checks for ML backends.

Usage Context
  - Used by ML models and training logic to select backend implementations.

Limitations
  - Uses importlib.util.find_spec and does not validate runtime health.
"""
# 说明：CDP ML 后端注册与探测工具，集中管理后端能力与可用性检查。
# 职责：
# - BackendCapabilities/BackendSpec：描述后端能力与依赖信息
# - detect_available_backends/get_backend：提供统一的可用性检测与获取接口
# - 统一可选依赖缺失时的错误处理路径

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError

from ..exceptions import BackendNotAvailable

__all__ = [
    "BackendCapabilities",
    "BackendSpec",
    "detect_available_backends",
    "get_backend",
]


@dataclass(frozen=True)
class BackendCapabilities:
    """
    Capability metadata for an ML backend.

    - Configuration
      - supports_dp: Whether the backend can run DP training hooks.
      - supports_gpu: Whether the backend can use GPU acceleration.
      - supports_callbacks: Whether training callbacks are supported.
      - supports_partial_fit: Whether partial_fit style training is available.
      - metadata: Optional backend metadata entries.

    - Behavior
      - Carries capability flags for backend selection logic.

    - Usage Notes
      - Use with BackendSpec to describe backend features.
    """
    # 后端能力描述对象，用于标记 DP/GPU/回调等特性

    supports_dp: bool = False
    supports_gpu: bool = False
    supports_callbacks: bool = True
    supports_partial_fit: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Export capabilities to a JSON-friendly dictionary."""
        # 将后端能力信息导出为可序列化字典
        return {
            "supports_dp": self.supports_dp,
            "supports_gpu": self.supports_gpu,
            "supports_callbacks": self.supports_callbacks,
            "supports_partial_fit": self.supports_partial_fit,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BackendCapabilities":
        """Create capabilities from a dictionary payload."""
        # 从字典载荷还原后端能力描述
        return cls(
            supports_dp=bool(data.get("supports_dp", False)),
            supports_gpu=bool(data.get("supports_gpu", False)),
            supports_callbacks=bool(data.get("supports_callbacks", True)),
            supports_partial_fit=bool(data.get("supports_partial_fit", False)),
            metadata=data.get("metadata", {}),
        )


@dataclass(frozen=True)
class BackendSpec:
    """
    Specification for an ML backend implementation.

    - Configuration
      - name: Backend identifier used by selection logic.
      - module: Import module name for availability checks.
      - extras: Optional extras name for installation hints.
      - capabilities: BackendCapabilities describing feature support.
      - available: Whether the backend dependency is available.

    - Behavior
      - Provides immutable spec records and availability variants.

    - Usage Notes
      - Use as the return payload for backend detection routines.
    """
    # 后端规范描述对象，包含依赖模块与能力配置

    name: str
    module: str
    extras: Optional[str] = None
    capabilities: BackendCapabilities = field(default_factory=BackendCapabilities)
    available: bool = False

    def with_availability(self, available: bool) -> "BackendSpec":
        """Return a new spec with updated availability."""
        # 基于当前规范生成新的可用性标记
        return BackendSpec(
            name=self.name,
            module=self.module,
            extras=self.extras,
            capabilities=self.capabilities,
            available=available,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export the backend spec to a JSON-friendly dictionary."""
        # 将后端规范导出为可序列化字典
        return {
            "name": self.name,
            "module": self.module,
            "extras": self.extras,
            "capabilities": self.capabilities.to_dict(),
            "available": self.available,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BackendSpec":
        """Create a backend spec from a dictionary payload."""
        # 从字典载荷还原后端规范描述
        capabilities_value = data.get("capabilities", {})
        if isinstance(capabilities_value, BackendCapabilities):
            capabilities = capabilities_value
        else:
            capabilities = BackendCapabilities.from_dict(capabilities_value)
        return cls(
            name=data["name"],
            module=data["module"],
            extras=data.get("extras"),
            capabilities=capabilities,
            available=bool(data.get("available", False)),
        )


_BACKEND_SPECS: Dict[str, BackendSpec] = {
    "sklearn": BackendSpec(
        name="sklearn",
        module="sklearn",
        extras="ml",
        capabilities=BackendCapabilities(
            supports_dp=False,
            supports_gpu=False,
            supports_callbacks=True,
            supports_partial_fit=True,
        ),
    ),
    "torch": BackendSpec(
        name="torch",
        module="torch",
        extras="ml-torch",
        capabilities=BackendCapabilities(
            supports_dp=True,
            supports_gpu=True,
            supports_callbacks=True,
            supports_partial_fit=False,
        ),
    ),
    "tensorflow": BackendSpec(
        name="tensorflow",
        module="tensorflow",
        extras="ml-tf",
        capabilities=BackendCapabilities(
            supports_dp=True,
            supports_gpu=True,
            supports_callbacks=True,
            supports_partial_fit=False,
        ),
    ),
}


def detect_available_backends() -> Dict[str, BackendSpec]:
    """Detect installed ML backends using importlib specs."""
    # 使用 importlib.util.find_spec 探测已安装的后端依赖
    detected: Dict[str, BackendSpec] = {}
    for name, spec in _BACKEND_SPECS.items():
        available = importlib.util.find_spec(spec.module) is not None
        detected[name] = spec.with_availability(available)
    return detected


def get_backend(name: str) -> BackendSpec:
    """Return an available backend spec or raise an error."""
    # 获取指定名称的后端规范，若缺失则抛出明确的异常提示
    ensure_type(name, (str,), label="name")
    normalized = name.strip().lower()
    ensure(normalized != "", "backend name must be non-empty")
    if normalized not in _BACKEND_SPECS:
        raise ParamValidationError(f"unknown backend '{name}'")
    spec = detect_available_backends()[normalized]
    if not spec.available:
        raise BackendNotAvailable(spec.name, extras=spec.extras)
    return spec
