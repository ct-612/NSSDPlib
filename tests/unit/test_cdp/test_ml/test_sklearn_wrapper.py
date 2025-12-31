"""
Unit tests for the sklearn estimator wrapper.
"""
# 说明：sklearn 估计器包装类的单元测试。
# 覆盖：
# - fit/predict/score 的基本调用流程
# - class_weight 与 random_state 的参数写入
# - sklearn 缺失时的跳过行为

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("sklearn")

from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

from dplib.cdp.ml.backends.sklearn.estimator_wrappers import SklearnEstimatorWrapper


def test_wrapper_fit_predict_score() -> None:
    # 验证包装类能完成训练、预测与评分流程
    features, labels = make_classification(
        n_samples=64,
        n_features=4,
        n_informative=2,
        n_redundant=0,
        random_state=0,
    )
    estimator = LogisticRegression(max_iter=50)
    wrapper = SklearnEstimatorWrapper(
        estimator,
        class_weight="balanced",
        random_state=7,
    )
    wrapper.fit(features, labels, sample_weight=np.ones(len(labels)))
    preds = wrapper.predict(features)
    score = wrapper.score(features, labels, sample_weight=np.ones(len(labels)))
    assert preds.shape[0] == features.shape[0]
    assert isinstance(score, float)
    params = wrapper.estimator.get_params()
    assert params.get("class_weight") == "balanced"
    assert params.get("random_state") == 7
