"""
Gaussian copula based DP synthetic data generator (MVP).

Responsibilities:
    * estimate DP marginals for continuous/discrete features
    * fit a DP-noised covariance matrix in latent Gaussian space
    * sample via multivariate normal and inverse-CDF reconstruction
"""
# 说明：基于高斯 Copula 的差分隐私合成数据生成器骨架，实现基础接口与简单近似算法。
# 职责：
# - 对连续和离散特征估计差分隐私边缘分布并构建潜在高斯空间表示
# - 在潜在高斯空间中拟合带噪协方差矩阵并进行多元正态采样
# - 通过正态 CDF 与经验边缘 CDF 的逆变换将样本映射回原始特征空间生成合成数据
from __future__ import annotations

import math
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np

from dplib.cdp.analytics.synthetic_data.base_generator import SyntheticDataGenerator
from dplib.core.data import Dataset, DatasetError
from dplib.core.data.domain import BaseDomain, ContinuousDomain, DiscreteDomain
from dplib.core.privacy import PrivacyModel
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.cdp.mechanisms.gaussian import GaussianMechanism
from dplib.cdp.mechanisms.laplace import LaplaceMechanism


class CopulaGenerator(SyntheticDataGenerator):
    """DP Gaussian copula generator."""
    # 基于高斯 Copula 的差分隐私合成生成器实现

    method = "copula"

    def __init__(
        self,
        domain: Mapping[str, BaseDomain],
        epsilon: float,
        *,
        delta: float = 0.0,
        privacy_model: PrivacyModel = PrivacyModel.CDP,
        accountant=None,
        budget_tracker=None,
        rng: Optional[np.random.Generator] = None,
        seed: Optional[int] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        copula_type: str = "gaussian",
        continuous_features: Optional[Sequence[str]] = None,
        discrete_features: Optional[Sequence[str]] = None,
        num_bins: int = 20,
        mechanism_cov: BaseMechanism | str = "gaussian",
        mechanism_marginal: BaseMechanism | str = "laplace",
    ):
        # 初始化 Copula 生成器配置，包括特征划分、Copula 类型、隐私机制以及 RNG 等依赖
        # 将公共域、隐私预算、会计器等参数交由父类管理以复用基础功能
        super().__init__(
            domain=domain,
            epsilon=epsilon,
            delta=delta,
            privacy_model=privacy_model,
            accountant=accountant,
            budget_tracker=budget_tracker,
            rng=rng,
            seed=seed,
            metadata=metadata,
        )
        self.copula_type = copula_type
        self.continuous_features = tuple(continuous_features or ())
        self.discrete_features = tuple(discrete_features or ())
        self.num_bins = num_bins
        self.mechanism_cov = mechanism_cov
        self.mechanism_marginal = mechanism_marginal

        self._cov: Optional[np.ndarray] = None
        self._cont_bins: Dict[str, np.ndarray] = {}
        self._cont_cdf: Dict[str, np.ndarray] = {}
        self._disc_probs: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

    # ------------------------------------------------------------------ fit/sample
    def _fit_internal(self, dataset: Dataset) -> None:
        """Estimate DP marginals and covariance."""
        # 估计连续特征的差分隐私边缘分布并在潜在高斯空间拟合协方差矩阵
        # 同时为离散特征计算类别概率，用于后续的独立采样生成
        if self.copula_type != "gaussian":
            raise NotImplementedError("only gaussian copula is supported in MVP")
        cont_fields = self._resolve_continuous_fields()
        disc_fields = self._resolve_discrete_fields(cont_fields)
        rng = self._require_rng()
        
        # 基于显式配置与域信息推断连续和离散特征集合

        cont_matrix = []
        for field in cont_fields:
            values = np.asarray(self._collect_field(dataset, field), dtype=float)
            bins = np.linspace(values.min(), values.max(), self.num_bins + 1) if len(values) else np.linspace(0.0, 1.0, self.num_bins + 1)
            counts, _ = np.histogram(values, bins=bins)
            mech = self._prepare_marginal_mechanism()
            mech.calibrate(sensitivity=1.0)
            # 对连续特征直方图计数加噪并累积为经验 CDF 近似边缘分布
            noisy = np.asarray(mech.randomise(counts), dtype=float)
            noisy = np.maximum(noisy, 0.0)
            cdf = np.cumsum(noisy)
            if cdf[-1] > 0:
                cdf = cdf / cdf[-1]
            else:
                cdf = np.linspace(0, 1, len(noisy))
            self._cont_bins[field] = bins
            self._cont_cdf[field] = cdf

            # 将原始值映射到经验 CDF 上的分位数再通过正态逆 CDF 投影到潜在高斯空间
            uniforms = self._to_uniform(values, bins, cdf)
            normals = self._norm_inv(uniforms)
            cont_matrix.append(normals)

        if cont_matrix:
            # 基于潜在高斯表示计算经验协方差并通过协方差机制注入噪声
            matrix = np.vstack(cont_matrix).T
            empirical_cov = np.cov(matrix, rowvar=False)
            cov_noise = self._prepare_cov_mechanism().randomise(empirical_cov)
            self._cov = np.asarray(cov_noise, dtype=float)
        else:
            # 若不存在连续特征则不构建协方差结构，后续采样退化为独立一维情形
            self._cov = None

        for field in disc_fields:
            # 对离散特征估计类别频率并归一化为概率，当前实现未对该部分添加噪声
            values = np.asarray(self._collect_field(dataset, field))
            unique, counts = np.unique(values, return_counts=True)
            probs = counts.astype(float)
            probs = np.maximum(probs, 0.0)
            total = probs.sum()
            probs = probs / total if total > 0 else np.ones_like(probs) / len(probs)
            self._disc_probs[field] = (unique, probs)

        # 拟合完成后记录本次训练过程消耗的隐私预算，交由上层会计器处理
        self._consume_budget(self.epsilon, self.delta)

    def _sample_internal(self, n: int) -> Dataset:
        rng = self._require_rng()
        records: Dict[str, np.ndarray] = {}
        # 基于已拟合的 Copula 结构在潜在高斯空间和类别概率上采样生成 n 条记录
        # 连续特征通过正态与经验 CDF 组合逆变换，离散特征通过多项式采样得到

        # continuous sampling
        # 使用拟合的协方差和边缘 CDF 对连续特征联合采样
        cont_fields = tuple(self._cont_bins.keys())
        if cont_fields:
            dim = len(cont_fields)
            cov = self._cov if self._cov is not None else np.eye(dim)
            # 在潜在高斯空间按协方差结构采样多元正态向量
            gaussian_samples = rng.multivariate_normal(mean=np.zeros(dim), cov=cov, size=n)
            for idx, field in enumerate(cont_fields):
                # 对每个连续特征做正态 CDF 和经验 CDF 的逆变换组合恢复原空间近似值
                uniforms = self._norm_cdf(gaussian_samples[:, idx])
                bins = self._cont_bins[field]
                cdf = self._cont_cdf[field]
                samples = self._inverse_cdf(uniforms, bins, cdf)
                records[field] = samples

        # discrete sampling
        # 使用预估类别概率对各离散特征独立采样
        for field, (values, probs) in self._disc_probs.items():
            records[field] = rng.choice(values, size=n, p=probs)

        return Dataset.from_arrays(records)

    # ------------------------------------------------------------------ helpers
    def _resolve_continuous_fields(self) -> Tuple[str, ...]:
        # 根据显式配置或域类型自动推断需要视为连续特征的字段集合
        if self.continuous_features:
            return tuple(self.continuous_features)
        inferred = []
        for name, dom in self.domain.items():
            if isinstance(dom, ContinuousDomain):
                inferred.append(name)
        return tuple(inferred)

    def _resolve_discrete_fields(self, cont_fields: Tuple[str, ...]) -> Tuple[str, ...]:
        # 通过排除连续特征字段并结合显式配置确定离散特征集合
        if self.discrete_features:
            return tuple(self.discrete_features)
        return tuple(field for field in self._domain_fields() if field not in cont_fields)

    def _collect_field(self, dataset: Dataset, field: str) -> Sequence[Any]:
        # 从 Dataset 中按字段名提取一列值，缺失时使用默认值占位保证长度一致
        values = []
        for record in dataset.to_list():
            if not isinstance(record, Mapping):
                raise DatasetError("copula generator expects mapping-based records")
            values.append(record.get(field, 0.0))
        return values

    def _prepare_cov_mechanism(self) -> BaseMechanism:
        # 构造用于协方差矩阵加噪的差分隐私机制，目前支持基于高斯机制的实现
        if isinstance(self.mechanism_cov, BaseMechanism):
            return self.mechanism_cov
        name = str(self.mechanism_cov).lower()
        if name == "gaussian":
            mech = GaussianMechanism(epsilon=self.epsilon, delta=max(self.delta, 1e-6), sensitivity=1.0, rng=self._require_rng())
            mech.calibrate()
            return mech
        raise ParamValidationError(f"unsupported covariance mechanism '{self.mechanism_cov}'")

    def _prepare_marginal_mechanism(self) -> BaseMechanism:
        # 构造用于连续特征边缘直方图加噪的机制，将全局 epsilon 按域字段数做简单分配
        if isinstance(self.mechanism_marginal, BaseMechanism):
            return self.mechanism_marginal
        name = str(self.mechanism_marginal).lower()
        if name == "laplace":
            return LaplaceMechanism(epsilon=self.epsilon / max(len(self._domain_fields()), 1), rng=self._require_rng())
        raise ParamValidationError(f"unsupported marginal mechanism '{self.mechanism_marginal}'")

    @staticmethod
    def _to_uniform(values: np.ndarray, bins: np.ndarray, cdf: np.ndarray) -> np.ndarray:
        # 根据值所在的直方图区间索引对应经验 CDF 分位数，实现到 [0, 1] 的归一化映射
        indices = np.searchsorted(bins[1:], values, side="right")
        indices = np.clip(indices, 0, len(cdf) - 1)
        return cdf[indices]

    @staticmethod
    def _norm_inv(u: np.ndarray) -> np.ndarray:
        # 使用 Winitzki 近似公式从均匀分布分位 u 计算标准正态分布的逆 CDF 值
        u = np.clip(u, 1e-6, 1 - 1e-6)
        x = 2 * u - 1
        a = 0.147  # approximation constant (Winitzki)
        sign = np.sign(x)
        ln_term = np.log(1 - x * x)
        first = 2 / (np.pi * a) + ln_term / 2
        inside = first * first - ln_term / a
        return sign * np.sqrt(np.sqrt(inside) - first) * math.sqrt(2.0)

    @staticmethod
    def _norm_cdf(x: np.ndarray) -> np.ndarray:
        # 利用误差函数 erf 计算标准正态分布的 CDF，将高斯样本映射到区间 [0, 1]
        return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))

    @staticmethod
    def _inverse_cdf(u: np.ndarray, bins: np.ndarray, cdf: np.ndarray) -> np.ndarray:
        # 根据经验 CDF 查找对应分位所在的直方图区间并取区间中点作为逆变换后的样本值
        indices = np.searchsorted(cdf, u, side="right")
        indices = np.clip(indices, 0, len(bins) - 2)
        left = bins[indices]
        right = bins[indices + 1]
        return (left + right) / 2.0

    def _config_extra(self) -> Dict[str, Any]:
        # 导出 Copula 生成器特有配置，方便序列化与恢复同构实例
        return {
            "copula_type": self.copula_type,
            "continuous_features": list(self.continuous_features),
            "discrete_features": list(self.discrete_features),
            "num_bins": self.num_bins,
            "mechanism_cov": self.mechanism_cov if isinstance(self.mechanism_cov, str) else self.mechanism_cov.__class__.__name__,
            "mechanism_marginal": self.mechanism_marginal if isinstance(self.mechanism_marginal, str) else self.mechanism_marginal.__class__.__name__,
        }
