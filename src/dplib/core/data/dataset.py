"""
Dataset abstractions shared by analytics, mechanisms, and sensitivity tools.

Responsibilities:
    * wrap heterogeneous data sources (records, numpy arrays, iterables)
    * provide indexing, slicing, batching, and metadata inspection
    * expose simple loaders, in-memory caches, and mapping helpers
"""
# 说明：概述 Dataset 抽象的作用域与职责，适用于分析（analytics）、机制（mechanisms）及灵敏度工具（sensitivity tools）等上层组件的通用数据访问。
# 职责：
# - 将不同形态的数据源（记录字典、NumPy 数组、任意可迭代）统一封装为一致的 Dataset 接口，便于后续处理
# - Dataset 提供索引/切片/分批迭代能力，并且可读取数据集的元信息（名称、格式、描述、额外字段）
# - 支持惰性加载（Loader 回调）、可选的内存缓存策略，以及 map/select/split 等便捷数据变换工具

from __future__ import annotations

from dataclasses import dataclass
from typing import Any,Callable,Dict,Iterable,Iterator,List,Mapping,MutableSequence,Optional,Sequence,Tuple,Union


DataRecord = Union[Mapping[str, Any], Sequence[Any]]
# 数据记录的统一类型：映射（列名->值）或序列（位置含义约定）

Loader = Callable[[], Iterable[DataRecord]]
# 惰性加载器：返回可迭代数据记录的可调用对象


class DatasetError(RuntimeError):
    """Raised when dataset operations fail."""
    # 数据集相关操作失败时抛出的异常（格式不一致、缺少数据源等）


@dataclass
class DatasetMetadata:
    """Basic metadata container used by the dataset abstraction."""
    # 数据集元数据：名称、格式、描述与附加信息（不影响数据内容）

    name: str = "Dataset"
    format: str = "records"
    description: Optional[str] = None
    extras: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        # 便于序列化/日志输出的字典表示；extras 做防御性复制
        return {
            "name": self.name,
            "format": self.format,
            "description": self.description,
            "extras": dict(self.extras or {}),
        }


class Dataset:
    """In-memory dataset wrapper with convenience helpers."""
    # 数据集封装器：统一封装多种数据源（立即给定或惰性加载），提供索引/切片/分批/映射等工具

    def __init__(
        self,
        data: Union[Iterable[DataRecord], Loader],
        *,
        metadata: Optional[DatasetMetadata] = None,
        cache: bool = True,
    ):
        self._metadata = metadata or DatasetMetadata()
        self._cache_enabled = cache                      # 是否将加载结果缓存在内存中
        self._loader = data if callable(data) else None  # 可调用视为惰性加载器
        self._data: Optional[List[DataRecord]] = None
        if not callable(data):
            self._data = list(data)                      # 立即物化为列表，保证可多次遍历

    @property
    def metadata(self) -> DatasetMetadata:
        # 暴露元数据对象（调用方可自行读取/复制使用）
        return self._metadata

    def _ensure_materialized(self) -> MutableSequence[DataRecord]:
        # 确保数据已物化：若存在 loader 则调用；cache=True 时保存副本以复用
        if self._data is None:
            if not self._loader:
                raise DatasetError("dataset has no data source")
            loaded = list(self._loader())
            if self._cache_enabled:
                self._data = loaded
            return loaded
        return self._data

    def __len__(self) -> int:
        # 使 Dataset 可被 len() 调用，得到元素个数
        return len(self._ensure_materialized())

    def __getitem__(self, index: Union[int, slice]) -> Union[DataRecord, List[DataRecord]]:
        # 索引访问：支持下标/切片访问
        data = self._ensure_materialized()
        return data[index]

    def iter(self, *, batch_size: Optional[int] = None, drop_last: bool = False) -> Iterator[List[DataRecord]]:
        """
        Iterate over the dataset, optionally yielding batches.

        Args:
            batch_size: Number of records per batch (None -> single records).
            drop_last: Drop the final partial batch if True.
        """
        # 分批迭代器：batch_size=None/<=0 时逐条返回；否则按批次返回
        data = self._ensure_materialized()
        if batch_size is None or batch_size <= 0:
            for record in data:
                yield [record]
            return

        batch: List[DataRecord] = []
        for record in data:
            batch.append(record)
            if len(batch) == batch_size:
                yield batch
                batch = []
        if batch and not drop_last:
            yield batch  # 处理尾部非满批次

    def map(self, fn: Callable[[DataRecord], DataRecord]) -> "Dataset":
        """Return a new dataset where `fn` has been applied to every record."""
        # 映射变换：对每条记录应用 fn，返回新的 Dataset（惰性生成 + 强制缓存）
        data = (fn(record) for record in self._ensure_materialized())
        return Dataset(data, metadata=self.metadata, cache=True)

    def select(self, fields: Sequence[str]) -> "Dataset":
        """Project mapping-based records onto a subset of fields."""
        # 字段选择：仅支持映射型记录，按给定字段投影，缺失字段填 None

        def _project(record: DataRecord) -> DataRecord:
            if not isinstance(record, Mapping):
                raise DatasetError("select() currently supports mapping-based records only")
            return {field: record.get(field) for field in fields}

        return self.map(_project)

    def split(self, *, fractions: Tuple[float, float] = (0.8, 0.2)) -> Tuple["Dataset", "Dataset"]:
        """Split the dataset into train/test partitions by fraction."""
        # 按比例拆分训练/测试集；要求两者之和为 1.0
        if abs(sum(fractions) - 1.0) > 1e-9:
            raise DatasetError("fractions must sum to 1.0")
        data = self._ensure_materialized()
        split_idx = int(len(data) * fractions[0])
        return Dataset(data[:split_idx], metadata=self.metadata), Dataset(data[split_idx:], metadata=self.metadata)

    @classmethod
    def from_records(cls, records: Iterable[Mapping[str, Any]], *, metadata: Optional[DatasetMetadata] = None) -> "Dataset":
        """Create a dataset from a sequence of mapping-based records."""
        # 由“记录列表”构建数据集，默认 format="records"
        return cls(list(records), metadata=metadata or DatasetMetadata(format="records"))

    @classmethod
    def from_arrays(
        cls,
        arrays: Mapping[str, Sequence[Any]],
        *,
        metadata: Optional[DatasetMetadata] = None,
    ) -> "Dataset":
        """Create a dataset from columnar arrays."""
        # 由列式数组（列名->序列）构建数据集；要求所有列长度一致
        lengths = {len(values) for values in arrays.values()}
        if len(lengths) != 1:
            raise DatasetError("all columns must have the same length")
        size = lengths.pop()
        records = [{key: arrays[key][idx] for key in arrays} for idx in range(size)]
        return cls(records, metadata=metadata or DatasetMetadata(format="records"))

    def to_list(self) -> List[DataRecord]:
        """Materialize dataset contents into a list."""
        # 强制物化为列表（用于导出或与不支持惰性迭代的 API 交互）
        return list(self._ensure_materialized())
