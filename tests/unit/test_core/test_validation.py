"""
Unit tests for schema validation utilities.
"""
# 说明：基于 Schema / SchemaField / SchemaValidator 的数据校验工具单元测试。
# 覆盖：
# - 连续数值域 ContinuousDomain 与必填字段 required 标记的组合使用
# - SchemaValidator 在 RAISE / IMPUTE / DROP 三种策略下对缺失字段的处理行为
# - 自定义 imputer 函数在 IMPUTE 策略下对缺失值的填补
# - detect_missing 对 None / 空字符串等缺失值的统计计数

import pytest

from dplib.core.data import (
    ContinuousDomain,
    DataValidationError,
    Schema,
    SchemaField,
    SchemaValidator,
    ValidationStrategy,
    detect_missing,
)


def test_schema_validator_raise_on_missing_required_field() -> None:
    # 校验策略为 RAISE 时，缺失必填字段应抛出 DataValidationError。
    domain = ContinuousDomain(minimum=0.0, maximum=5.0)
    schema = Schema([SchemaField("value", domain, required=True)])
    validator = SchemaValidator(schema, on_error=ValidationStrategy.RAISE)
    with pytest.raises(DataValidationError):
        validator.validate_record({})


def test_schema_validator_impute_strategy() -> None:
    # 在 IMPUTE 策略下，缺失必填字段通过自定义 imputer 填补默认值。
    domain = ContinuousDomain(minimum=0.0, maximum=10.0)
    schema = Schema([SchemaField("metric", domain, required=True)])

    def imputer(field: SchemaField) -> float:
        assert field.name == "metric"
        return 5.0

    validator = SchemaValidator(schema, on_error=ValidationStrategy.IMPUTE, imputer=imputer)
    validated = validator.validate_records([{}])
    assert validated[0]["metric"] == 5.0


def test_schema_validator_drop_strategy() -> None:
    # 在 DROP 策略下，缺失必填字段的记录会被直接丢弃。
    domain = ContinuousDomain(minimum=0.0, maximum=1.0)
    schema = Schema([SchemaField("score", domain, required=True)])
    validator = SchemaValidator(schema, on_error=ValidationStrategy.DROP)
    result = validator.validate_records([{}, {"score": 0.5}])
    assert len(result) == 1
    assert result[0]["score"] == 0.5


def test_detect_missing_counts_nulls() -> None:
    # detect_missing 统计 None / 空字符串 等缺失在必填字段中的出现次数。
    records = [{"a": 1, "b": None}, {"a": None, "b": ""}]
    counts = detect_missing(records, required=["a", "b"])
    assert counts["a"] == 1
    assert counts["b"] == 2
