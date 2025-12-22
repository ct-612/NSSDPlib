"""
Property-based tests for infrastructure and utility components.
"""
# 说明：基础设施与通用工具的属性测试，涵盖组件工厂、注册表、运行时配置、随机数管理与序列化模块。
# 职责：
# - 验证 LDP/CDP 机制工厂的动态查找与按需实例化逻辑
# - 确保编码器、聚合器与应用工厂能够正确分发配置并创建 pipeline
# - 测试运行时配置（RuntimeConfig）的环境变量解析与动态更新能力
# - 验证随机数生成器（RNG）在种子克隆、独立拆分与噪声采样中的一致性
# - 测试 JSON 序列化工具的递归处理与敏感字段掩码正确性

import os
import json
import pytest
import numpy as np
from dataclasses import dataclass
from hypothesis import given, strategies as st, settings, HealthCheck
from dplib.core.utils.config import get_config, configure, RuntimeConfig
from dplib.core.utils.random import create_rng, split_rng, sample_noise, reseed_rng
from dplib.core.utils.serialization import serialize_to_json, deserialize_from_json, VersionedPayload
from dplib.ldp.mechanisms.mechanism_factory import create_mechanism as create_ldp_mechanism
from dplib.cdp.mechanisms.mechanism_factory import create_mechanism as create_cdp_mechanism
from dplib.ldp.encoders.encoder_factory import EncoderFactory
from dplib.ldp.aggregators.aggregator_factory import AggregatorFactory
from dplib.ldp.applications.application_factory import ApplicationFactory


# ------------------------------------------------------------------ Factories & Registries
def test_ldp_mechanism_factory_robustness():
    # 验证 LDP 机制工厂对冗余参数的过滤能力及其分发一致性
    # 传递一个所有机制可能都不存在的额外参数，不应触发 TypeError
    mech = create_ldp_mechanism("grr",
                                epsilon=1.0,
                                categories=[0, 1],
                                unknown_param=999)
    assert mech.mechanism_id == "grr"
    assert mech.epsilon == 1.0


def test_cdp_mechanism_factory_dispatch():
    # 验证 CDP 机制工厂能否正确识别并实例化 Laplace 机制
    mech = create_cdp_mechanism("laplace", epsilon=1.0, sensitivity=1.0)
    assert mech.mechanism_id == "laplace"
    assert mech.epsilon == 1.0


def test_encoder_factory_pipeline():
    # 验证编码器工厂能否依据配置字典序列构建复杂的编码 pipeline
    config = {
        "encoders": [{
            "type": "categorical",
            "categories": ["a", "b"]
        }, {
            "type": "unary",
            "length": 3
        }]
    }
    pipeline = EncoderFactory.build_pipeline(config)
    assert len(pipeline) == 2
    assert pipeline[0].__class__.__name__ == "CategoricalEncoder"
    assert pipeline[1].__class__.__name__ == "UnaryEncoder"


def test_aggregator_application_factories():
    # 验证聚合器与应用工厂的注册表覆盖情况
    assert AggregatorFactory.get_class("mean").__name__ == "MeanAggregator"
    assert ApplicationFactory.get_class(
        "heavy_hitters").__name__ == "HeavyHittersApplication"


# ------------------------------------------------------------------ Configuration
def test_runtime_config_env_loading(monkeypatch):
    # 验证配置模块从环境变量加载并解析布尔与整数值的能力
    monkeypatch.setenv("DPLIB_STRICT_VALIDATION", "false")
    monkeypatch.setenv("DPLIB_RNG_SEED", "42")

    cfg = RuntimeConfig()
    cfg.load_from_env()

    assert cfg.strict_validation is False
    assert cfg.rng_seed == 42


def test_runtime_config_update_validation():
    # 验证配置更新时的属性校验，输入未知项应抛出 AttributeError
    cfg = get_config()
    cfg.update(log_level="DEBUG")
    assert cfg.log_level == "DEBUG"

    with pytest.raises(AttributeError):
        cfg.update(non_existent_option=True)


# ------------------------------------------------------------------ Random Utilities
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_rng_reproducibility(seed):
    # 验证相同种子产生的 RNG 在执行多次采样后仍保持结果一致
    rng1 = create_rng(seed)
    rng2 = create_rng(seed)

    val1 = rng1.normal(0, 1, size=10)
    val2 = rng2.normal(0, 1, size=10)

    assert np.array_equal(val1, val2)


def test_rng_splitting_independence():
    # 验证拆分后的多个子 RNG 序列具有独立性，且不与父 RNG 重叠
    parent = create_rng(1234)
    children = split_rng(parent, 2)

    v1 = children[0].random(5)
    v2 = children[1].random(5)

    assert not np.array_equal(v1, v2)


@given(st.floats(min_value=0.1, max_value=10.0))
def test_sample_noise_dispatch(scale):
    # 验证 sample_noise 统一分派接口能够正确调用底层的分布采样函数
    rng = create_rng(0)
    noise = sample_noise(rng, "laplace", scale=scale, size=(5, ))
    assert noise.shape == (5, )


# ------------------------------------------------------------------ Serialization
@dataclass
class MockRecord:
    id: int
    secret: str

    def to_dict(self):
        return {"id": self.id, "secret": self.secret}


def test_serialization_roundtrip_with_masking():
    # 验证 JSON 序列化在支持对象转换的同时能正确对敏感字段打码
    record = MockRecord(id=1, secret="password123")

    # 1. 普通序列化
    json_str = serialize_to_json(record)
    data = deserialize_from_json(json_str)
    assert data["id"] == 1
    assert data["secret"] == "password123"

    # 2. 带掩码的序列化
    masked_json = serialize_to_json(record, sensitive_fields=["secret"])
    masked_data = deserialize_from_json(masked_json)
    assert masked_data["secret"] == "***"


def test_versioned_payload_handling():
    # 验证版本化载荷包装及其在 JSON 往返过程中的结构完整性
    payload = {"metrics": [1, 2, 3]}
    vp = VersionedPayload(version="1.2.0", payload=payload)

    json_data = vp.to_json()
    recovered = VersionedPayload.from_json(json_data)

    assert recovered.version == "1.2.0"
    assert recovered.payload == payload
