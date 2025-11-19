"""
Unit tests for runtime configuration utilities.
"""
# 说明：RuntimeConfig（运行时配置）及全局配置访问辅助函数的单元测试。
# 覆盖：
# - configure(...)：通过关键字参数更新全局配置实例字段
# - RuntimeConfig.load_from_env(...)：从环境变量加载并覆写配置选项
# - get_config()：返回全局 RuntimeConfig 单例并保持状态一致性

import os

from dplib.core.utils import RuntimeConfig, configure, get_config


def test_configure_updates_values() -> None:
    # 验证 configure(...) 能正确更新全局配置的字段值
    cfg = configure(strict_validation=False, default_dtype="float32")
    assert cfg.strict_validation is False
    assert cfg.default_dtype == "float32"


def test_runtime_config_env_override(monkeypatch) -> None:
    # 验证 RuntimeConfig.load_from_env(...) 按环境变量覆写默认配置
    cfg = RuntimeConfig()
    monkeypatch.setenv("DPLIB_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DPLIB_STRICT_VALIDATION", "false")
    cfg.load_from_env()
    assert cfg.log_level == "DEBUG"
    assert cfg.strict_validation is False


def test_get_config_returns_singleton() -> None:
    # 验证 get_config() 每次返回的是同一全局实例（单例行为）
    cfg = get_config()
    cfg.strict_validation = True
    assert get_config().strict_validation is True
