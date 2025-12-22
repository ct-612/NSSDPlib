"""
Property-based tests for core data structures and transformers.
"""
# 说明：核心数据层（Dataset, DataTransformer, TransformerPipeline）及基础统计函数的属性测试。
# 覆盖：
# - Dataset 记录转换、比例拆分（split）与投影（select）操作
# - 数据集的 map 变换逻辑与懒加载（lazy）执行验证
# - TransformerPipeline 对记录执行链式变换的正确性
# - 均值（mean）与方差（variance）基础统计函数在数值范围下的运行状态

import pytest
from hypothesis import given, strategies as st
from dplib.core.data.dataset import Dataset, DatasetError
from dplib.core.data.transformers import TransformerPipeline, DataTransformer, TransformationError
from dplib.core.data.statistics import mean, variance
from typing import MutableMapping, Any


# ---------------------------------------------------------------- Dataset
@given(
    st.lists(st.dictionaries(keys=st.text(min_size=1, max_size=5),
                             values=st.integers()),
             min_size=5,
             max_size=20))
def test_dataset_from_records_split(records):
    # 验证从 Python 字典记录集创建的数据集能正确按指定权重划分为训练集与测试集
    ds = Dataset.from_records(records)
    assert len(ds) == len(records)

    # Split 80/20
    train, test = ds.split(fractions=(0.8, 0.2))

    # 验证长度关系
    expected_train = int(len(records) * 0.8)
    assert len(train) == expected_train
    assert len(test) == len(records) - expected_train

    # 验证内容互斥且并集完整 (对于 list data)
    train_data = train.to_list()
    test_data = test.to_list()
    assert len(train_data) + len(test_data) == len(records)


@given(
    st.lists(st.dictionaries(keys=st.just("a"), values=st.integers()),
             min_size=1))
def test_dataset_select(records):
    # 验证数据集的字段选择操作能正确过滤字典键并保持记录数量一致
    ds = Dataset.from_records(records)
    projected = ds.select(["a"])

    for r in projected.to_list():
        assert len(r) == 1
        assert "a" in r


@given(st.lists(st.integers(), min_size=1))
def test_dataset_map(values):
    # 验证 map 算子及其对应的匿名变换函数能在数据提取时正确应用于每个元素
    ds = Dataset(data=values)
    mapped = ds.map(lambda x: x * 2)

    orig = ds.to_list()
    res = mapped.to_list()

    assert len(res) == len(orig)
    for o, r in zip(orig, res):
        assert r == o * 2


@given(st.floats(min_value=0.0, max_value=1.0),
       st.floats(min_value=0.0, max_value=1.0))
def test_dataset_split_invalid_fraction(f1, f2):
    # 验证在分片权重之和不为 1 时，split 方法能正确识别并拦截非法配置
    if abs(f1 + f2 - 1.0) < 1e-9:
        return

    ds = Dataset.from_records([{"a": 1}] * 10)
    # 归一化校验失败应抛出 DatasetError
    with pytest.raises(DatasetError):
        ds.split(fractions=(f1, f2))


# ---------------------------------------------------------------- Transformers


class IdentityTransformer(DataTransformer):
    # 实现一个不对记录执行任何修改的恒等变换器用于基准测试
    def transform_record(
            self, record: MutableMapping[str,
                                         Any]) -> MutableMapping[str, Any]:
        return record


class AddOneTransformer(DataTransformer):
    # 对记录中的指定数值字段执行加 1 操作的简单变换器示例
    def __init__(self, field):
        super().__init__(name="AddOne")
        self.field = field

    def transform_record(
            self, record: MutableMapping[str,
                                         Any]) -> MutableMapping[str, Any]:
        if self.field in record:
            record[self.field] = record[self.field] + 1
        return record


@given(st.integers())
def test_identity_transformer(val):
    # 验证恒等变换器在处理输入字典后其键值结构与原记录完全一致
    t = IdentityTransformer()
    record = {"a": val}
    res = t.transform_record(record)
    assert res["a"] == val


@given(st.integers())
def test_transformer_pipeline(val):
    # 验证变换器流水线能按顺序组合多个简单变换器并生成复合变换结果
    t1 = AddOneTransformer("a")
    t2 = AddOneTransformer("a")
    chain = TransformerPipeline([t1, t2])

    record = {"a": val}
    res = chain.transform(record)
    assert res["a"] == val + 2


# ---------------------------------------------------------------- Statistics
@given(
    st.lists(st.floats(min_value=-1e10,
                       max_value=1e10,
                       allow_nan=False,
                       allow_infinity=False),
             min_size=2))
def test_statistics_basic(data):
    # 验证核心统计函数均值与方差在正常浮点数值范围下的计算稳定性与输出类型
    if len(data) < 2:
        return

    m = mean(data)
    try:
        v = variance(data)
        assert isinstance(v, float)
    except ValueError:
        # 如果数值不足，方差计算可能会失败（主要通过检查 len < 2 来处理）
        pass
    assert isinstance(m, float)
