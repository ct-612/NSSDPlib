"""
Unit tests for CDP ML configuration containers.
"""
# 说明：CDP ML 配置容器的单元测试，覆盖序列化与校验逻辑。
# 覆盖：
# - MLConfig 的默认值补齐与序列化往返
# - TrainingConfig 与 DPConfig 的非法参数校验
# - AccountingConfig 与 ModelConfig 的错误提示

from __future__ import annotations

import pytest

from dplib.cdp.ml.config import AccountingConfig, DPConfig, MLConfig, ModelConfig, TrainingConfig
from dplib.core.utils.param_validation import ParamValidationError


def test_ml_config_round_trip_defaults() -> None:
    # 验证 MLConfig 的默认值补齐与往返序列化行为
    payload = {
        "model": {
            "model_type": "linear",
            "backend": "sklearn",
            "params": {"fit_intercept": True},
        }
    }
    config = MLConfig.from_dict(payload)
    config.validate()
    assert config.training.batch_size == TrainingConfig().batch_size
    round_trip = MLConfig.from_dict(config.to_dict())
    assert round_trip.model.model_type == "linear"
    assert round_trip.model.backend == "sklearn"


def test_training_config_validation_errors() -> None:
    # 验证训练配置的非法取值会触发参数校验错误
    with pytest.raises(ParamValidationError):
        TrainingConfig(epochs=0).validate()
    with pytest.raises(ParamValidationError):
        TrainingConfig(batch_size=0).validate()
    with pytest.raises(ParamValidationError):
        TrainingConfig(learning_rate=0.0).validate()


def test_dp_config_requires_fields_when_enabled() -> None:
    # 验证启用 DP 时必须提供噪声尺度与裁剪阈值
    with pytest.raises(ParamValidationError):
        DPConfig(enabled=True, noise_multiplier=None, max_grad_norm=1.0).validate()
    with pytest.raises(ParamValidationError):
        DPConfig(enabled=True, noise_multiplier=1.0, max_grad_norm=None).validate()


def test_accounting_config_validation_errors() -> None:
    # 验证会计配置中的非法取值会触发参数校验错误
    with pytest.raises(ParamValidationError):
        AccountingConfig(sample_rate=1.5).validate()
    with pytest.raises(ParamValidationError):
        AccountingConfig(target_delta=1.0).validate()


def test_model_config_missing_type() -> None:
    # 验证缺失 model_type 时会抛出参数校验错误
    with pytest.raises(ParamValidationError):
        ModelConfig.from_dict({})
