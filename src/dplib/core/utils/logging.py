"""
Lightweight logging helpers with privacy-aware defaults.
"""
# 说明：轻量级日志工具，提供隐私友好的默认配置与统一的 logger 获取入口。
# 职责：
# - PrivacyFilter：根据运行时配置对日志记录中的敏感字段进行脱敏处理
# - configure_logging(...)：初始化 logging 基本配置并为根 logger 挂载隐私过滤器
# - get_logger(...)：按名称获取 logger，必要时自动完成日志系统初始化
# 约定：
# - 是否掩码敏感字段由 RuntimeConfig.mask_sensitive_fields 控制
# - 日志级别优先级：显式参数 level > 环境变量 DPLIB_LOG_LEVEL > 运行时配置的 log_level

from __future__ import annotations

import logging
import os
from typing import Optional

from .config import get_config


class PrivacyFilter(logging.Filter):
    """Filter that strips sensitive fields from log records if configured."""
    # 日志隐私过滤器：在启用掩码配置时，对约定字段名（如 user_id / pii / payload）进行统一脱敏处理

    def filter(self, record: logging.LogRecord) -> bool:
        # 从全局运行时配置读取当前是否需要对日志中的敏感字段进行掩码
        config = get_config()
        if not config.mask_sensitive_fields:
            return True
        # 对约定的敏感属性进行覆盖，保留字段结构但隐藏具体内容
        for attr in ("user_id", "pii", "payload"):
            if hasattr(record, attr):
                setattr(record, attr, "***")
        return True


def configure_logging(level: Optional[str] = None) -> None:
    # 初始化根 logger：确定最终日志级别、设置格式，并挂载 PrivacyFilter
    log_level = level or os.environ.get("DPLIB_LOG_LEVEL", get_config().log_level)
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(name)s %(asctime)s | %(message)s",
    )
    logging.getLogger().addFilter(PrivacyFilter())


def get_logger(name: str) -> logging.Logger:
    # 获取指定名称的 logger，若尚无 handler，则懒加载方式调用 configure_logging 进行初始化
    logger = logging.getLogger(name)
    if not logger.handlers:
        configure_logging()
    return logger

