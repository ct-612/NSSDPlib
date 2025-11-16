"""
Unit tests for the Dataset container.
"""
# 说明：Dataset（记录序列数据容器）的基础功能单元测试。
# 覆盖：
# - 基本长度计算与索引访问行为
# - 批量迭代 iter(...) 及 drop_last 语义
# - map / select 变换管线与类型约束（仅支持映射型记录）
# - 数据集拆分 split(...)、物化 to_list() 与元数据传递
# - from_records / from_arrays 构造函数及输入长度一致性校验

import pytest

from dplib.core.data import Dataset, DatasetError, DatasetMetadata


def test_dataset_length_and_indexing() -> None:
    # 使用简单字典记录构造数据集
    data = [{"value": i} for i in range(5)]
    ds = Dataset(data, metadata=DatasetMetadata(name="mock"))
    # __len__ 应当返回底层记录数量
    assert len(ds) == 5
    # 支持基于整数索引的只读访问
    assert ds[2]["value"] == 2


def test_dataset_batch_iteration_and_drop_last() -> None:
    # 构造 5 条记录的数据集
    ds = Dataset([{"x": idx} for idx in range(5)])
    # 默认情况下，最后一个不满 batch 的批次也会被返回
    batches = list(ds.iter(batch_size=2))
    assert [len(batch) for batch in batches] == [2, 2, 1]
    # drop_last=True 时，丢弃尾部不完整批次
    batches_drop = list(ds.iter(batch_size=2, drop_last=True))
    assert [len(batch) for batch in batches_drop] == [2, 2]


def test_dataset_map_and_select() -> None:
    # 基于原始数据集构造
    ds = Dataset([{"x": 1}, {"x": 2}])
    # map 应返回新的 Dataset，逐条应用映射函数
    mapped = ds.map(lambda record: {"x": record["x"] * 2})
    assert mapped[0]["x"] == 2
    # select 按字段子集投影，保持记录结构
    selected = mapped.select(["x"])
    assert list(selected.to_list())[0]["x"] == 2


def test_dataset_select_requires_mapping_records() -> None:
    # 使用非 Mapping 类型记录（元组），不支持按键字段 select
    ds = Dataset([(1, 2, 3)])
    # 对非映射记录执行 select 应抛出 DatasetError
    with pytest.raises(DatasetError):
        ds.select(["a"])


def test_dataset_split_and_materialize() -> None:
    # 构造 10 条记录的数据集以测试 split
    ds = Dataset([{"x": i} for i in range(10)])
    # 按 0.6 / 0.4 比例划分训练集与测试集
    train, test = ds.split(fractions=(0.6, 0.4))
    # 验证拆分后两端大小
    assert len(train) == 6
    assert len(test) == 4
    # to_list() 应该物化所有记录，不改变数量
    assert len(train.to_list()) == 6


def test_dataset_from_records_and_arrays() -> None:
    # 通过 from_records 构建数据集，并携带元数据
    records = [{"x": 1}, {"x": 2}]
    ds = Dataset.from_records(records, metadata=DatasetMetadata(name="records"))
    assert ds.metadata.name == "records"
    # 通过 from_arrays 从列式数组构建数据集
    arrays_ds = Dataset.from_arrays({"x": [1, 2], "y": [3, 4]})
    # 每个索引位置应组合对应的列值
    assert arrays_ds[1]["y"] == 4


def test_dataset_from_arrays_requires_equal_length() -> None:
    # from_arrays 需要所有字段数组长度一致，否则应抛出 DatasetError
    with pytest.raises(DatasetError):
        Dataset.from_arrays({"x": [1, 2], "y": [1]})
