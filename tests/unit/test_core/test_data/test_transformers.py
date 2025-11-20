"""
Unit tests for data transformers and transformer pipelines.
"""
# 说明：DataTransformer 抽象基类及其具体变换（剪裁、归一化、离散化、独热编码）
#       与 TransformerPipeline（转换流水线）的单元测试。
# 覆盖：
# - ClippingTransformer：对数值字段进行上下界裁剪（clamp 到 [minimum, maximum]）
# - NormalizationTransformer：基于样本数据学习参数，并按策略对特征进行归一化（此处使用 min-max）
# - DiscretizerTransformer：根据给定边界 edges 将连续数值映射为桶索引
# - OneHotEncoder：将分类字段展开为 one-hot 列并移除原始字段
# - TransformerPipeline：顺序执行多步变换（normalization → clipping → 自定义 Passthrough）并验证组合效果

import pytest

from dplib.core.data import (
    ClippingTransformer,
    DataTransformer,
    DiscretizerTransformer,
    NormalizationTransformer,
    OneHotEncoder,
    TransformerPipeline,
)


class PassthroughTransformer(DataTransformer):
    """Helper transformer for verifying pipeline composition."""
    # 辅助型变换器：用于验证流水线（pipeline）组合是否按顺序执行
    # 行为：对输入记录不做任何数值变换，仅在键 "seen" 上累计出现次数

    def __init__(self):
        super().__init__(name="Passthrough")

    def transform_record(self, record):
        # 若记录中不存在 "seen" 键，则从 0 开始计数；否则在原值基础上 +1
        record["seen"] = record.get("seen", 0) + 1
        return record  # 原样透传记录，仅附带更新后的 "seen"


def test_clipping_transformer_bounds() -> None:
    # 检查裁剪转换器对超出上界的值进行截断，确保输出落在给定区间内
    clip = ClippingTransformer("value", minimum=0.0, maximum=10.0)
    record = {"value": 12.0}
    assert clip(record)["value"] == 10.0


def test_normalization_transformer_minmax() -> None:
    # 使用 min-max 策略对字段进行归一化，验证输出位于 [0, 1] 区间
    data = [{"x": 1.0}, {"x": 2.0}, {"x": 3.0}]
    transformer = NormalizationTransformer("x", strategy="minmax").fit(data)
    transformed = transformer({"x": 2.0})
    assert 0.0 <= transformed["x"] <= 1.0


def test_discretizer_transformer_assigns_bucket() -> None:
    # 验证离散化变换根据 edges 将连续分数映射到正确的桶索引
    discretizer = DiscretizerTransformer("score", edges=[0.0, 1.0, 2.0])
    record = discretizer({"score": 1.5})
    assert record["score"] == 1


def test_one_hot_encoder_expands_categories() -> None:
    # 检查 one-hot 编码展开分类字段并移除原字段，且对应类别位置为 1.0 / 0.0
    encoder = OneHotEncoder("city", ["ny", "sf"])
    transformed = encoder({"city": "ny"})
    assert transformed["city__ny"] == 1.0
    assert transformed["city__sf"] == 0.0
    assert "city" not in transformed


def test_transformer_pipeline_executes_in_sequence() -> None:
    # 构造 normalizer → clipper → Passthrough 的三步流水线，验证顺序执行与“seen次数”标记
    data = [{"value": 1.0}, {"value": 2.0}, {"value": 3.0}]
    normalizer = NormalizationTransformer("value", strategy="zscore").fit(data)
    clipper = ClippingTransformer("value", minimum=-0.5, maximum=0.5)
    pipeline = TransformerPipeline([normalizer, clipper, PassthroughTransformer()])
    result = pipeline.transform({"value": 4.0})
    # 输出值应被归一化后再被剪裁到给定范围，并且 PassthroughTransformer 被调用一次
    assert -0.5 <= result["value"] <= 0.5
    assert result["seen"] == 1
