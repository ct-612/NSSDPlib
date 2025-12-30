"""
Privacy-preserving histogram utilities and rendering helpers.

Responsibilities
  - Compute histogram counts for provided bin edges.
  - Apply vectorised DP noise calibrated to contribution limits.
  - Render histogram plots for reporting and inspection.

Usage Context
  - Use when releasing noisy histogram counts for numeric data.
  - Designed for bin-based aggregation with bounded contributions.

Limitations
  - Requires calibrated mechanisms; defaults to a Laplace vector mechanism.
  - Rendering relies on matplotlib for PNG output.
"""
# 说明：提供差分隐私直方图查询与绘图辅助函数，统一计数与渲染输出。
# 职责：
# - 校验 epsilon、bins、max_contribution 并生成确定性直方图分箱
# - 使用 VectorMechanism 对计数向量一次性加噪并裁剪为非负
# - 输出带标签的 PNG 渲染结果，便于报表或可视化展示

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np

from dplib.core.data.statistics import histogram
from dplib.core.privacy.base_mechanism import BaseMechanism
from dplib.core.utils.param_validation import ParamValidationError, ensure, ensure_type
from dplib.cdp.mechanisms.vector import VectorMechanism


class PrivateHistogramQuery:
    """
    Release DP protected histogram counts.

    - Configuration
      - epsilon: Privacy budget used for the default vector mechanism.
      - bins: Sorted numeric bin edges used for deterministic counting.
      - mechanism: Optional calibrated mechanism to apply noise.
      - max_contribution: Per-entity contribution bound for sensitivity.

    - Behavior
      - Computes deterministic histogram counts for the configured bins.
      - Adds vector noise and clips the result to non-negative counts.

    - Usage Notes
      - Provide a calibrated vector mechanism to override defaults.
    """
    # 差分隐私直方图查询封装，集中处理分箱、计数与向量噪声注入

    def __init__(
        self,
        epsilon: float,
        bins: Sequence[float],
        *,
        mechanism: Optional[BaseMechanism] = None,
        max_contribution: int = 1,
    ):
        # 初始化直方图查询参数并构造或校验用于加噪的向量机制
        self.epsilon = self._validate_epsilon(epsilon)
        self.bins = self._validate_bins(bins)
        self.max_contribution = self._validate_contribution(max_contribution)
        self.mechanism = self._prepare_mechanism(mechanism)

    @staticmethod
    def _validate_epsilon(epsilon: float) -> float:
        # 将 epsilon 规范为正浮点数，避免无效预算进入机制校准
        try:
            numeric = float(epsilon)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ParamValidationError("epsilon must be a positive number for histogram queries") from exc
        ensure(numeric > 0, "epsilon must be a positive number for histogram queries", error=ParamValidationError)
        return numeric

    @staticmethod
    def _validate_bins(bins: Sequence[float]) -> Tuple[float, ...]:
        # 确保 bins 为有序数值序列并至少包含两个边界点
        ensure_type(bins, (list, tuple), label="bins")
        ensure(len(bins) >= 2, "bins must include at least two edges", error=ParamValidationError)
        try:
            numeric_bins = tuple(float(edge) for edge in bins)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
            raise ParamValidationError("bins must be numeric") from exc
        ensure(
            list(numeric_bins) == sorted(numeric_bins),
            "bins must be sorted ascending",
            error=ParamValidationError,
        )
        return numeric_bins

    @staticmethod
    def _validate_contribution(max_contribution: int) -> int:
        # 校验单个主体在直方图中的最大贡献次数用于设置敏感度
        ensure(max_contribution > 0, "max_contribution must be positive", error=ParamValidationError)
        return int(max_contribution)

    def _prepare_mechanism(self, mechanism: Optional[BaseMechanism]) -> BaseMechanism:
        # 若未提供外部机制则按 max_contribution 构造并校准默认向量机制
        if mechanism is None:
            mech = VectorMechanism(
                epsilon=self.epsilon,
                sensitivity=float(self.max_contribution),
                distribution="laplace",
                norm="l1",
            )
            mech.calibrate()
            return mech
        # 外部机制必须已完成校准，保证噪声尺度可用
        ensure_type(mechanism, (BaseMechanism,), label="mechanism")
        ensure(mechanism.calibrated, "provided mechanism must be calibrated before use", error=ParamValidationError)
        return mechanism

    def evaluate(self, values: Iterable[float]) -> Tuple[List[float], Tuple[float, ...]]:
        """Execute the DP histogram query and return noisy counts with bin edges."""
        # 先生成确定性计数，再对计数向量一次性加噪并裁剪为非负
        try:
            counts, bin_edges = histogram(values, bins=self.bins)
        except ValueError as exc:  # pragma: no cover - defensive
            raise ParamValidationError(str(exc)) from exc

        noisy = np.asarray(self.mechanism.randomise(np.asarray(counts, dtype=float)), dtype=float)
        clipped = np.maximum(noisy, 0.0)
        return clipped.tolist(), bin_edges


def _format_bin_labels(bins: Sequence[float]) -> List[str]:
    """Format bin edges into readable labels."""
    # 将箱边格式化为区间标签，最后一段右闭合以表达完整区间
    labels: List[str] = []
    last_idx = len(bins) - 2
    for idx in range(len(bins) - 1):
        left = bins[idx]
        right = bins[idx + 1]
        suffix = "]" if idx == last_idx else ")"
        labels.append(f"[{left:g}, {right:g}{suffix}")
    return labels


def _load_pyplot():
    """Load matplotlib pyplot with a non-interactive backend when needed."""
    # 延迟导入 pyplot 并确保非交互后端以适配无显示环境
    import sys
    import matplotlib

    if "matplotlib.pyplot" not in sys.modules:
        try:
            matplotlib.use("Agg")
        except Exception:
            pass
    import matplotlib.pyplot as plt

    return plt


def render_histogram_png(
    counts: Sequence[float],
    bins: Sequence[float],
    path: Union[str, Path],
    *,
    title: Optional[str] = None,
    color: str = "#4C78A8",
    dpi: int = 150,
    figsize: Tuple[float, float] = (8.0, 4.0),
    rotation: int = 45,
    fontsize: int = 7,
    tick_label_fontsize: Optional[int] = None,
    y_tick_step: Optional[float] = None,
    xlabel: Optional[str] = None,
    ylabel: str = "count",
) -> Path:
    """Render histogram counts with bin labels and save to a PNG file."""
    # 导入并使用 matplotlib 绘制柱状图，支持多种可选参数定制输出
    # 校验输入维度，确保计数与分箱数量一致
    bins_list = [float(edge) for edge in bins]
    if len(bins_list) < 2:
        raise ParamValidationError("bins must include at least two edges")
    counts_list = [float(value) for value in counts]
    if len(counts_list) != len(bins_list) - 1:
        raise ParamValidationError("counts length must match bins-1")

    # 生成标签并渲染柱状图，支持可选标题与坐标轴设置
    labels = _format_bin_labels(bins_list)
    x = list(range(len(counts_list)))
    plt = _load_pyplot()
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x, counts_list, color=color)
    ax.set_xticks(x)
    tick_size = fontsize if tick_label_fontsize is None else tick_label_fontsize
    ax.set_xticklabels(labels, rotation=rotation, ha="right", fontsize=tick_size)
    ax.tick_params(axis="y", labelsize=tick_size)
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if y_tick_step is not None:
        from matplotlib.ticker import MultipleLocator

        ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))
    # 输出路径由调用方控制，确保父目录存在
    fig.tight_layout()
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def render_histogram_compare_png(
    raw_counts: Sequence[float],
    dp_counts: Sequence[float],
    bins: Sequence[float],
    path: Union[str, Path],
    *,
    title: str = "Raw vs DP Histogram",
    labels: Tuple[str, str] = ("Raw", "DP"),
    colors: Tuple[str, str] = ("#4C78A8", "#F58518"),
    dpi: int = 150,
    figsize: Tuple[float, float] = (10.0, 4.0),
    rotation: int = 45,
    fontsize: int = 7,
    tick_label_fontsize: Optional[int] = None,
    y_tick_step: Optional[float] = None,
    ylabel: str = "count",
) -> Path:
    """Render a side-by-side comparison histogram and save to PNG."""
    # 导入并使用 matplotlib 绘制并排柱状图以对比原始与 DP 结果
    # 校验输入维度，确保原始和噪声计数与分箱一致
    bins_list = [float(edge) for edge in bins]
    if len(bins_list) < 2:
        raise ParamValidationError("bins must include at least two edges")
    raw_list = [float(value) for value in raw_counts]
    dp_list = [float(value) for value in dp_counts]
    if len(raw_list) != len(bins_list) - 1 or len(dp_list) != len(bins_list) - 1:
        raise ParamValidationError("counts length must match bins-1")

    # 使用并排柱状图对比原始与 DP 结果
    bin_labels = _format_bin_labels(bins_list)
    x = list(range(len(raw_list)))
    plt = _load_pyplot()
    fig, ax = plt.subplots(figsize=figsize)
    width = 0.4
    ax.bar([pos - width / 2 for pos in x], raw_list, width=width, color=colors[0], label=labels[0])
    ax.bar([pos + width / 2 for pos in x], dp_list, width=width, color=colors[1], label=labels[1])
    ax.set_xticks(x)
    tick_size = fontsize if tick_label_fontsize is None else tick_label_fontsize
    ax.set_xticklabels(bin_labels, rotation=rotation, ha="right", fontsize=tick_size)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.tick_params(axis="y", labelsize=tick_size)
    if y_tick_step is not None:
        from matplotlib.ticker import MultipleLocator

        ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))
    fig.tight_layout()
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path


def render_histogram_triptych_png(
    raw_counts: Sequence[float],
    dp_counts: Sequence[float],
    bins: Sequence[float],
    path: Union[str, Path],
    *,
    titles: Tuple[str, str, str] = ("Raw Histogram", "DP Histogram", "Raw vs DP"),
    labels: Tuple[str, str] = ("Raw", "DP"),
    colors: Tuple[str, str] = ("#4C78A8", "#F58518"),
    dpi: int = 150,
    figsize: Tuple[float, float] = (15.0, 4.0),
    rotation: int = 45,
    fontsize: int = 7,
    tick_label_fontsize: Optional[int] = None,
    y_tick_step: Optional[float] = None,
    ylabel: str = "count",
) -> Path:
    """Render raw, DP, and comparison histograms into a single PNG file."""
    # 将原始直方图、DP 直方图和对比直方图渲染到一张 PNG 文件中
    # 校验输入维度，确保原始与噪声计数与分箱一致
    bins_list = [float(edge) for edge in bins]
    if len(bins_list) < 2:
        raise ParamValidationError("bins must include at least two edges")
    raw_list = [float(value) for value in raw_counts]
    dp_list = [float(value) for value in dp_counts]
    if len(raw_list) != len(bins_list) - 1 or len(dp_list) != len(bins_list) - 1:
        raise ParamValidationError("counts length must match bins-1")

    # 生成标签并绘制三联图以便对比原始与 DP 结果
    bin_labels = _format_bin_labels(bins_list)
    x = list(range(len(raw_list)))
    plt = _load_pyplot()
    fig, axes = plt.subplots(1, 3, figsize=figsize, sharey=True)

    axes[0].bar(x, raw_list, color=colors[0])
    axes[0].set_title(titles[0])
    axes[0].set_xticks(x)
    tick_size = fontsize if tick_label_fontsize is None else tick_label_fontsize
    axes[0].set_xticklabels(bin_labels, rotation=rotation, ha="right", fontsize=tick_size)
    axes[0].set_ylabel(ylabel)
    axes[0].tick_params(axis="y", labelsize=tick_size)

    axes[1].bar(x, dp_list, color=colors[1])
    axes[1].set_title(titles[1])
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(bin_labels, rotation=rotation, ha="right", fontsize=tick_size)
    axes[1].tick_params(axis="y", labelsize=tick_size)

    width = 0.4
    axes[2].bar([pos - width / 2 for pos in x], raw_list, width=width, color=colors[0], label=labels[0])
    axes[2].bar([pos + width / 2 for pos in x], dp_list, width=width, color=colors[1], label=labels[1])
    axes[2].set_title(titles[2])
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(bin_labels, rotation=rotation, ha="right", fontsize=tick_size)
    axes[2].tick_params(axis="y", labelsize=tick_size)
    axes[2].legend()

    if y_tick_step is not None:
        from matplotlib.ticker import MultipleLocator

        # 统一三幅子图的 y 轴刻度间隔
        for ax in axes:
            ax.yaxis.set_major_locator(MultipleLocator(y_tick_step))

    # 输出路径由调用方控制，确保父目录存在
    fig.tight_layout()
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)
    return out_path
