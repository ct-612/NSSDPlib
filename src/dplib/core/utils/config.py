"""
Runtime configuration utilities.

Centralises the library's tunable options and exposes helpers to read
from environment variables or update settings at runtime.
"""
# 说明：运行时配置管理工具，集中管理库内可调选项，并支持环境变量覆写与运行期更新。
# 职责：
# - RuntimeConfig：封装严格校验开关、默认数值类型、日志等级、敏感字段掩码、随机种子等配置项
# - load_from_env(...)：按统一前缀（如 DPLIB_）从环境变量加载并解析配置值
# - get_config()：获取全局 RuntimeConfig 单例，作为库级默认配置入口
# - configure(...)：通过关键字参数便捷更新全局配置并返回更新后的实例
# 约定：
# - 布尔类环境变量使用 {"1", "true", "yes"}（大小写不敏感）视为 True
# - RNG_SEED 环境变量会被解析为整数
# - 未知配置键在 update(...) 中会触发 AttributeError，避免静默吞错

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RuntimeConfig:
    strict_validation: bool = True
    default_dtype: str = "float64"
    log_level: str = field(default_factory=lambda: os.environ.get("DPLIB_LOG_LEVEL", "INFO"))
    mask_sensitive_fields: bool = True
    rng_seed: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs: Any) -> None:
        # 按关键字参数更新当前配置实例，未知字段名将显式报错
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"unknown config option '{key}'")
            setattr(self, key, value)

    def load_from_env(self, prefix: str = "DPLIB_") -> None:
        # 从带有指定前缀的环境变量中加载配置，并进行类型转换后写回实例字段
        for key in ("STRICT_VALIDATION", "DEFAULT_DTYPE", "LOG_LEVEL", "MASK_SENSITIVE_FIELDS", "RNG_SEED"):
            env_key = f"{prefix}{key}"
            if env_key not in os.environ:                 
                continue    # 未设置对应环境变量时保持当前配置值不变
            value = os.environ[env_key]
            if key == "STRICT_VALIDATION" or key == "MASK_SENSITIVE_FIELDS":               
                value = value.lower() in {"1", "true", "yes"}   # 将布尔开关类字符串标准化为 True/False
            elif key == "RNG_SEED":               
                value = int(value)  # 随机种子使用整数类型
            # 将环境变量写回到对应字段：
            setattr(self, key.lower() if key != "MASK_SENSITIVE_FIELDS" else "mask_sensitive_fields", value)
            # - 绝大多数字段采用 key.lower() 命名约定
            # - MASK_SENSITIVE_FIELDS 是特殊字段名，需要手动映射到属性 mask_sensitive_fields


# 全局配置单例，用作库内默认的运行时配置
_GLOBAL_CONFIG = RuntimeConfig()


def get_config() -> RuntimeConfig:
    # 返回全局 RuntimeConfig 实例，供调用方读取或在本进程内共享配置
    return _GLOBAL_CONFIG


def configure(**kwargs: Any) -> RuntimeConfig:
    # 以关键字参数更新全局配置，并返回更新后的实例（便于链式调用或调试）
    _GLOBAL_CONFIG.update(**kwargs)
    return _GLOBAL_CONFIG
