"""
Data validation helpers shared across datasets and analytics.

Responsibilities:
    * schema definitions with required/optional fields
    * missing value detection and coercion helpers
    * configurable strategies for handling validation errors
"""
# 说明：通用数据校验辅助工具。
# 职责：
# - 提供数据校验工具：Schema/SchemaField 定义、缺失值检测、以及校验策略（抛错/丢弃/填补）
# - SchemaValidator 核心能力：逐记录校验，按域（Domain）做值校验与编码，按策略处理异常或空值

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from .domain import BaseDomain, DomainError


class ValidationStrategy:
    """Enumeration of simple validation strategies."""
    # 校验策略枚举：
    # - RAISE：遇到错误直接抛出异常
    # - DROP：丢弃当前记录
    # - IMPUTE：对字段进行填补（优先使用 imputer 回调，否则用默认值）

    RAISE = "raise"
    DROP = "drop"
    IMPUTE = "impute"


@dataclass
class SchemaField:
    """Describe a single field inside a schema."""
    # 单个字段的模式描述：
    # - name：字段名
    # - domain：字段所属域（负责值的校验/编码/解码）
    # - required：是否必填
    # - allow_null：是否允许 None
    # - default：默认值（IMPUTE 策略或缺失且允许填补时使用）

    name: str
    domain: BaseDomain
    required: bool = True
    allow_null: bool = False
    default: Any = None


@dataclass
class Schema:
    """Collection of schema fields keyed by name."""
    # 模式对象：由多个 SchemaField 组成

    fields: Sequence[SchemaField]

    def field_map(self) -> Dict[str, SchemaField]:
        # 字段映射：生成 name->SchemaField 的查找表（便于快速访问）
        return {field.name: field for field in self.fields}


class DataValidationError(ValueError):
    """Raised when validation cannot be satisfied."""
    # 校验无法满足（如缺少必填/域校验失败且策略为 RAISE/无法填补）时的统一异常


class SchemaValidator:
    """Validate records against a schema and optional strategy."""
    # 模式校验器：按 Schema 和 校验策略 对记录进行逐字段校验与标准化

    def __init__(
        self,
        schema: Schema,
        *,
        on_error: str = ValidationStrategy.RAISE,
        imputer: Optional[Callable[[SchemaField], Any]] = None,
    ):
        # on_error：选择校验失败时的处理策略
        # imputer：当策略为 IMPUTE 时用于产生填充值的回调（以字段为输入）
        if on_error not in {ValidationStrategy.RAISE, ValidationStrategy.DROP, ValidationStrategy.IMPUTE}:
            raise DataValidationError("unknown validation strategy")
        self.schema = schema
        self.on_error = on_error
        self.imputer = imputer

    def validate_record(self, record: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        # 校验并返回标准化后的记录字典；若策略为 DROP 且该记录不合规则返回 None
        result: Dict[str, Any] = dict(record)
        for field in self.schema.fields:
            value = result.get(field.name, field.default)
            if value is None:
                # 处理缺失：若必填且不允许为空，按策略 RAISE/DROP/IMPUTE 处理
                if field.required and not field.allow_null:
                    if self.on_error == ValidationStrategy.RAISE:
                        raise DataValidationError(f"field '{field.name}' missing")
                    if self.on_error == ValidationStrategy.DROP:
                        return None
                    value = self._impute(field)
                result[field.name] = value
                continue
            try:
                # 正常值：交由域对象做 validate（包含 contains 归属检查与 encode 编码）
                result[field.name] = field.domain.validate(value)
            except DomainError as exc:
                # 域校验失败：按策略处理
                if self.on_error == ValidationStrategy.RAISE:
                    raise DataValidationError(str(exc)) from exc
                if self.on_error == ValidationStrategy.DROP:
                    return None
                result[field.name] = self._impute(field)
        return result

    def validate_records(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        # 批量校验：过滤掉返回 None 的记录（当策略为 DROP 时）
        output: List[Dict[str, Any]] = []
        for record in records:
            validated = self.validate_record(record)
            if validated is not None:
                output.append(validated)
        return output

    def _impute(self, field: SchemaField) -> Any:
        # 生成填充值：
        # - 优先调用外部 imputer 回调
        # - 否则使用字段 default
        # - 若均不可用则抛出错误
        if self.imputer:
            return self.imputer(field)
        if field.default is not None:
            return field.default
        raise DataValidationError(f"cannot impute field '{field.name}'")


def detect_missing(records: Iterable[Mapping[str, Any]], *, required: Sequence[str]) -> Dict[str, int]:
    """Return counts of missing values per field."""
    # 缺失检测：对 required 列表中的缺失字段逐条记录计数
    # 规则：值为 None / 空字符串 "" / NaN 视为缺失
    counts = {field: 0 for field in required}
    for record in records:
        for field in required:
            if record.get(field) in (None, "", float("nan")):
                counts[field] += 1
    return counts
