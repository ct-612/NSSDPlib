"""
Unit tests for logging utilities.
"""
# 说明：日志配置与隐私脱敏过滤相关的单元测试。
# 覆盖：
# - configure_logging(...)：根据给定日志级别初始化 logging 系统
# - get_logger(...)：获取带 PrivacyFilter 的 logger 实例
# - 验证 user_id 等敏感字段在日志输出中被掩码，而普通消息内容仍然可见

import logging

from dplib.core.utils import configure_logging, get_logger


def test_configure_logging_sets_privacy_filter(caplog) -> None:
    # 验证日志配置后，敏感字段 user_id 会被 PrivacyFilter 掩码
    configure_logging(level="INFO")
    logger = get_logger("dplib.test")
    with caplog.at_level(logging.INFO):
        logger.info("message", extra={"user_id": "123"})
    # 日志中应包含消息文本，但不应出现原始 user_id
    assert "message" in caplog.text
    assert "123" not in caplog.text  # masked by filter
