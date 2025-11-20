"""
Unit tests for data validation helpers and schema utilities.
"""
# 说明：数据校验工具（Schema / SchemaField / SchemaValidator / detect_missing）及相关异常的单元测试。
# 覆盖：
# - SchemaValidator 在缺失必填字段时按 RAISE / DROP / IMPUTE 策略的行为差异
# - detect_missing 对 None / 空字符串 等缺失值的计数统计
# - 域校验错误（DomainError）在记录校验过程中被包装为 ParamValidationError
# - 在 IMPUTE 策略下缺少插补来源（imputer/default）时触发 DataValidationError
# - 对非法 validation strategy（如未知字符串）在初始化阶段抛出 ParamValidationError

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
from dplib.core.utils import ParamValidationError


def test_schema_validator_raise_on_missing_required_field() -> None:
    # RAISE 策略下，缺失必填字段应抛出 ParamValidationError
    domain = ContinuousDomain(minimum=0.0, maximum=5.0)
    schema = Schema([SchemaField("value", domain, required=True)])
    validator = SchemaValidator(schema, on_error=ValidationStrategy.RAISE)
    with pytest.raises(ParamValidationError):
        validator.validate_record({})


def test_schema_validator_impute_strategy() -> None:
    # IMPUTE 策略下，缺失必填字段通过自定义 imputer 填补默认值
    domain = ContinuousDomain(minimum=0.0, maximum=10.0)
    schema = Schema([SchemaField("metric", domain, required=True)])

    def imputer(field: SchemaField) -> float:
        assert field.name == "metric"
        return 5.0

    validator = SchemaValidator(schema, on_error=ValidationStrategy.IMPUTE, imputer=imputer)
    validated = validator.validate_records([{}])
    assert validated[0]["metric"] == 5.0


def test_schema_validator_drop_strategy() -> None:
    # DROP 策略下，缺失必填字段的记录被丢弃，仅保留完整记录
    domain = ContinuousDomain(minimum=0.0, maximum=1.0)
    schema = Schema([SchemaField("score", domain, required=True)])
    validator = SchemaValidator(schema, on_error=ValidationStrategy.DROP)
    result = validator.validate_records([{}, {"score": 0.5}])
    assert len(result) == 1
    assert result[0]["score"] == 0.5


def test_detect_missing_counts_nulls() -> None:
    # detect_missing 对 None 与空字符串等视为缺失并按字段计数
    records = [{"a": 1, "b": None}, {"a": None, "b": ""}]
    counts = detect_missing(records, required=["a", "b"])
    assert counts["a"] == 1
    assert counts["b"] == 2


def test_domain_validation_error_wrapped_as_param_validation() -> None:
    # 域校验失败（值超出 ContinuousDomain 范围）应被包装为 ParamValidationError
    domain = ContinuousDomain(minimum=0.0, maximum=1.0)
    schema = Schema([SchemaField("score", domain, required=True)])
    validator = SchemaValidator(schema)
    with pytest.raises(ParamValidationError):
        validator.validate_record({"score": 5.0})


def test_imputer_missing_raises_data_validation_error() -> None:
    # IMPUTE 策略下，如无 imputer 且字段 default 为 None，应抛出 DataValidationError
    domain = ContinuousDomain(minimum=0.0, maximum=1.0)
    schema = Schema([SchemaField("score", domain, required=True, allow_null=False, default=None)])
    validator = SchemaValidator(schema, on_error=ValidationStrategy.IMPUTE, imputer=None)
    with pytest.raises(DataValidationError):
        validator.validate_record({})


def test_unknown_strategy_raises_param_validation_error() -> None:
    # 对未知 on_error 策略值，构造 SchemaValidator 时即抛 ParamValidationError
    domain = ContinuousDomain(minimum=0.0, maximum=1.0)
    schema = Schema([SchemaField("score", domain, required=True)])
    with pytest.raises(ParamValidationError):
        SchemaValidator(schema, on_error="invalid")
