"""
Unit tests for CDP ML backend registry helpers.
"""
# 说明：CDP ML 后端注册与探测逻辑的单元测试。
# 覆盖：
# - 后端探测接口返回的注册项
# - get_backend 的未知名称校验
# - 缺失依赖时抛出 BackendNotAvailable

from __future__ import annotations

import pytest

from dplib.cdp.ml.backends import detect_available_backends, get_backend
from dplib.cdp.ml.exceptions import BackendNotAvailable
from dplib.core.utils.param_validation import ParamValidationError


def test_detect_available_backends_returns_specs() -> None:
    # 验证后端探测返回注册项并包含预期键
    backends = detect_available_backends()
    assert "sklearn" in backends
    assert "torch" in backends
    assert "tensorflow" in backends
    assert backends["sklearn"].name == "sklearn"


def test_get_backend_unknown_raises() -> None:
    # 验证未知后端名称会触发参数校验错误
    with pytest.raises(ParamValidationError):
        get_backend("unknown-backend")


def test_get_backend_missing_dependency_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    # 验证缺失依赖时 get_backend 会抛出 BackendNotAvailable
    import dplib.cdp.ml.backends.registry as backend_registry

    original_find_spec = backend_registry.importlib.util.find_spec

    def fake_find_spec(name: str) -> object:
        if name == "sklearn":
            return None
        return original_find_spec(name)

    monkeypatch.setattr(backend_registry.importlib.util, "find_spec", fake_find_spec)
    with pytest.raises(BackendNotAvailable):
        get_backend("sklearn")


def test_get_backend_available_returns_spec() -> None:
    # 验证可用后端能正常返回规范对象
    spec = detect_available_backends()["sklearn"]
    if not spec.available:
        pytest.skip("sklearn not available")
    backend = get_backend("sklearn")
    assert backend.name == "sklearn"
    assert backend.available is True
