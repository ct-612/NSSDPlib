"""
Data validation helpers shared across datasets and analytics.

Responsibilities:
    * schema definitions with required/optional fields
    * missing value detection and coercion helpers
    * configurable strategies for handling validation errors
"""
# 说明：通用数据校验辅助工具。
# 职责：
# - Schema / SchemaField：描述字段名、Domain、是否必填、默认值等模式信息
# - SchemaValidator：按给定策略（RAISE / DROP / IMPUTE）对记录进行校验与缺失处理
# - DataValidationError：用于无法满足校验（尤其是无法插补）时的错误报告
# - detect_missing：统计必填字段在记录集中的缺失次数（None / 空字符串 / NaN）
# 约定：
# - 显式引入 from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError
# - Schema/SchemaValidator 里所有基本断言（必填、类型转换等）统一用 ensure/ensure_type
# - 只在数据域校验或映射时抛出 ParamValidationError，保持异常族一致
# - 保留 DataValidationError 作为数据层特例（例如 schema 矛盾、imputer 缺失）时再封装使用

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from .domain import BaseDomain, DomainError
from dplib.core.utils.param_validation import ensure, ensure_type, ParamValidationError


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
        # 字段映射：将字段序列转换为 {字段名: SchemaField} 映射，便于按名称快速查询
        return {field.name: field for field in self.fields}

    def __post_init__(self) -> None:
        # 初始化时对 fields 容器与每个字段/域做一次轻量类型校验，避免静态配置错误
        ensure_type(self.fields, (list, tuple), label="fields")
        for field in self.fields:
            ensure_type(field, (SchemaField,), label="field")
            ensure_type(field.domain, (BaseDomain,), label=f"{field.name}.domain")


class DataValidationError(ValueError):
    """Raised when validation cannot be satisfied (schema-level issues)."""
    # 校验无法满足（如无法插补）时抛出的（模式级异常）


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
        # 初始化校验器：绑定 Schema、错误处理策略与可选插补函数
        ensure(
            on_error in {ValidationStrategy.RAISE, ValidationStrategy.DROP, ValidationStrategy.IMPUTE},
            "unknown validation strategy",
            error=ParamValidationError,
        )
        ensure_type(schema, (Schema,), label="schema")
        self.schema = schema
        self.on_error = on_error
        self.imputer = imputer

    def validate_record(self, record: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        # 校验单条记录：按 Schema 检查缺失与 Domain 约束，根据策略决定抛错 / 丢弃 / 插补
        result: Dict[str, Any] = dict(record)
        for field in self.schema.fields:
            value = result.get(field.name, field.default)
            if value is None:
                # 处理缺失：若必填且不允许为空，按策略 RAISE/DROP/IMPUTE 处理
                if field.required and not field.allow_null:
                    if self.on_error == ValidationStrategy.RAISE:
                        raise ParamValidationError(f"field '{field.name}' missing")
                    if self.on_error == ValidationStrategy.DROP:
                        return None
                    value = self._impute(field)
                result[field.name] = value
                continue
            try:
                # 非缺失值交由域对象执行类型/范围等校验与规范化
                result[field.name] = field.domain.validate(value)
            except DomainError as exc:
                # 域校验失败：按策略处理
                if self.on_error == ValidationStrategy.RAISE:
                    raise ParamValidationError(str(exc)) from exc
                if self.on_error == ValidationStrategy.DROP:
                    return None
                # IMPUTE 策略下，对域校验失败的值进行插补
                result[field.name] = self._impute(field)
        return result

    def validate_records(self, records: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        # 批量校验多条记录，自动过滤掉策略为 DROP 时返回 None 的记录
        output: List[Dict[str, Any]] = []
        for record in records:
            validated = self.validate_record(record)
            if validated is not None:
                output.append(validated)
        return output

    def _impute(self, field: SchemaField) -> Any:
        # 插补优先级：自定义 imputer > 字段默认值 > 抛出 DataValidationError
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
