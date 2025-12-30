"""
Example 40: Dataset Smoke CDP (Adult).

Goal:
    Demonstrate a full CDP workflow on a real dataset:
    raw data -> cleaning -> domains/bounds -> dataset
    -> queries -> sensitivity -> mechanism calibration -> release
    -> accounting -> readable report.

Extras:
    [cdp]

Usage:
    python examples/end_to_end/40_dataset_smoke_cdp.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Dict, List, Optional

project_root = Path(__file__).resolve().parents[2]
src_root = project_root / "src"
if str(project_root) not in sys.path:
    # 允许在仓库外部直接运行示例脚本
    sys.path.insert(0, str(project_root))
if str(src_root) not in sys.path:
    # 确保可直接导入本地 src 包
    sys.path.insert(0, str(src_root))

from examples._shared import cli, io
from dplib.cdp.analytics.queries import QueryEngine, render_histogram_triptych_png
from dplib.cdp.analytics.reporting import PrivacyReport, UtilityReport
from dplib.cdp.composition import CDPPrivacyAccountant
from dplib.cdp.mechanisms import GaussianMechanism, VectorMechanism
from dplib.cdp.sensitivity import count_bounds, histogram_bounds, sum_bounds
from dplib.core.data import (
    ContinuousDomain,
    Dataset,
    DatasetMetadata,
)
from dplib.core.data.statistics import histogram as raw_histogram
from dplib.core.privacy import PrivacyAccountant


# 需要按数值解析的字段集合
NUMERIC_FIELDS = {
    "age",
    "fnlwgt",
    "education-num",
    "capital-gain",
    "capital-loss",
    "hours-per-week",
}


def _bucket_labels(edges: List[float]) -> List[str]:
    # 根据分桶边界生成可读标签
    labels: List[str] = []
    last_idx = len(edges) - 2
    for idx in range(len(edges) - 1):
        left = edges[idx]
        right = edges[idx + 1]
        suffix = "]" if idx == last_idx else ")"
        labels.append(f"[{left:g}, {right:g}{suffix}")
    return labels


def _ascii_histogram(labels: List[str], counts: List[float], *, width: int = 40) -> str:
    # 生成纯文本直方图，便于写入报告
    if not counts:
        return "(empty)"
    max_count = max(counts) or 1.0
    lines: List[str] = []
    for label, count in zip(labels, counts):
        bar_len = int(round((count / max_count) * width))
        bar = "#" * bar_len
        lines.append(f"{label:>12} | {bar} {count:.0f}")
    return "\n".join(lines)


def _relative_md_path(target: Path, base_dir: Path) -> str:
    try:
        return target.relative_to(base_dir).as_posix()
    except ValueError:
        return target.as_posix()


def _adult_feature_names(names_path: Path) -> List[str]:
    # 从 adult.names 解析字段名
    names: List[str] = []
    for raw in names_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("|"):
            continue
        if ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        if name:
            names.append(name)
    if len(names) != 14:
        raise ValueError(f"unexpected number of features: {len(names)}")
    return names


def _load_adult_records(
    data_path: Path,
    names_path: Path,
    *,
    limit: Optional[int] = None,
) -> List[Dict[str, object]]:
    # 读取 adult.data，只删除缺失值或格式错误的行
    columns = _adult_feature_names(names_path) + ["income"]
    records: List[Dict[str, object]] = []
    with data_path.open("r", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("|"):
                continue
            parts = [item.strip() for item in line.split(",")]
            if len(parts) != len(columns):
                continue
            if any(value == "?" for value in parts):
                continue
            record: Dict[str, object] = {}
            for name, value in zip(columns, parts):
                if name in NUMERIC_FIELDS:
                    record[name] = float(value)
                else:
                    record[name] = value
            record["income"] = str(record["income"]).strip().rstrip(".")
            records.append(record)
            if limit is not None and len(records) >= limit:
                break
    return records


def main(argv=None):
    args = cli.parse_args("Dataset Smoke CDP (Adult)", argv)
    limit = 3000 if args.quick else 10000

    # 数据路径与加载
    data_dir = project_root / "tests" / "test_data" / "adult"
    data_path = data_dir / "adult.data"
    names_path = data_dir / "adult.names"
    if not data_path.exists() or not names_path.exists():
        raise RuntimeError(f"adult dataset files not found under {data_dir}")
    records = _load_adult_records(
        data_path,
        names_path,
        limit=limit,
    )
    if not records:
        raise RuntimeError("adult dataset is empty after cleaning")

    # 定义数值域与直方图分桶
    age_domain = ContinuousDomain(minimum=17.0, maximum=90.0, name="age")
    age_min = float(age_domain.minimum)
    age_max = float(age_domain.maximum)
    edges: List[float] = [age_min]
    while edges[-1] < age_max:
        edges.append(edges[-1] + 2.0)
    bucket_edges = tuple(edges)

    dataset = Dataset.from_records(
        records,
        metadata=DatasetMetadata(
            name="adult_clean",
            description="adult data (cleaned only: drop missing or malformed rows)",
            extras={
                "age_bounds": (age_domain.minimum, age_domain.maximum),
                "age_edges": bucket_edges,
            },
        ),
    )
    data_records = dataset.to_list()

    # 输出清洗后的数据，便于对比
    outdir = Path(args.outdir)
    io.ensure_outdir(outdir)
    processed_path = outdir / "40_dataset_smoke_cdp_processed.csv"
    columns = list(data_records[0].keys())
    with processed_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in data_records:
            writer.writerow({key: row.get(key) for key in columns})

    labels = [row["income"] for row in data_records]
    ages = [row["age"] for row in data_records]

    # 预算配置与会计器
    epsilon_grid = [round(0.1 + idx * (0.4 / 9.0), 4) for idx in range(10)]
    count_epsilons = list(epsilon_grid)
    total_count_epsilons = list(epsilon_grid)
    sum_epsilons = list(epsilon_grid)
    hist_eps = 0.1
    total_delta = 1e-6
    utility_draws = 5000
    gaussian_runs = len(count_epsilons) + len(total_count_epsilons) + len(sum_epsilons)
    total_epsilon = sum(count_epsilons) + sum(total_count_epsilons) + sum(sum_epsilons) + hist_eps
    gaussian_delta = total_delta / max(gaussian_runs, 1)
    accountant = PrivacyAccountant(total_epsilon=total_epsilon, total_delta=total_delta, name="adult_cdp")
    engine = QueryEngine(accountant=accountant)

    # 敏感度与机制校准
    count_sensitivity = count_bounds().upper
    sum_sensitivity = sum_bounds(age_domain).upper
    hist_sensitivity = histogram_bounds().upper

    seed_base = int(args.seed) if args.seed is not None else 0
    # 非隐私基线结果（对比用）
    true_hi_count = float(sum(1 for value in labels if value == ">50K"))
    true_total_count = float(len(labels))
    true_age_sum = float(sum(ages))
    true_age_mean = true_age_sum / max(true_total_count, 1.0)
    hist_bins = list(bucket_edges)
    true_hist_counts, _ = raw_histogram(ages, bins=hist_bins)
    true_hist_counts = [float(x) for x in true_hist_counts]

    hist_mech = VectorMechanism(
        epsilon=hist_eps,
        sensitivity=hist_sensitivity,
        distribution="laplace",
        norm="l1",
        rng=seed_base + 14,
    ).calibrate()

    # DP count：收入>50K
    count_hi_results = []
    for idx, eps in enumerate(count_epsilons):
        hi_count_mech = GaussianMechanism(
            epsilon=eps,
            delta=gaussian_delta,
            sensitivity=count_sensitivity,
            rng=seed_base + 11 + idx,
        ).calibrate()
        dp_value = engine.execute(
            "count",
            data=labels,
            epsilon=eps,
            predicate=lambda value: value == ">50K",
            mechanism=hi_count_mech,
            accounting_metadata={"stage": "income_count", "epsilon": eps},
        )
        dp_value = min(max(dp_value, 0.0), float(len(labels)))
        noisy_values = [dp_value]
        for _ in range(max(utility_draws - 1, 0)):
            sample = float(hi_count_mech.randomise(true_hi_count))
            sample = min(max(sample, 0.0), float(len(labels)))
            noisy_values.append(sample)
        count_hi_results.append((eps, dp_value, noisy_values))
    dp_hi_count = count_hi_results[-1][1]

    # DP count：总样本数
    total_count_results = []
    for idx, eps in enumerate(total_count_epsilons):
        total_count_mech = GaussianMechanism(
            epsilon=eps,
            delta=gaussian_delta,
            sensitivity=count_sensitivity,
            rng=seed_base + 21 + idx,
        ).calibrate()
        dp_value = engine.execute(
            "count",
            data=ages,
            epsilon=eps,
            mechanism=total_count_mech,
            accounting_metadata={"stage": "total_count", "epsilon": eps},
        )
        noisy_values = [dp_value]
        for _ in range(max(utility_draws - 1, 0)):
            noisy_values.append(float(total_count_mech.randomise(true_total_count)))
        total_count_results.append((eps, dp_value, noisy_values))
    dp_total_count = total_count_results[-1][1]

    # DP sum：年龄求和
    sum_results = []
    for idx, eps in enumerate(sum_epsilons):
        sum_mech = GaussianMechanism(
            epsilon=eps,
            delta=gaussian_delta,
            sensitivity=sum_sensitivity,
            rng=seed_base + 31 + idx,
        ).calibrate()
        dp_value = engine.execute(
            "sum",
            data=ages,
            epsilon=eps,
            bounds=(age_domain.minimum, age_domain.maximum),
            mechanism=sum_mech,
            accounting_metadata={"stage": "age_sum", "epsilon": eps},
        )
        noisy_values = [dp_value]
        for _ in range(max(utility_draws - 1, 0)):
            noisy_values.append(float(sum_mech.randomise(true_age_sum)))
        sum_results.append((eps, dp_value, noisy_values))
    dp_age_sum = sum_results[-1][1]

    dp_hist_counts, dp_hist_edges = engine.execute(
        "histogram",
        data=ages,
        bins=hist_bins,
        epsilon=hist_eps,
        mechanism=hist_mech,
        accounting_metadata={"stage": "age_hist"},
    )

    # 后处理：裁剪范围/派生均值
    dp_hi_count = min(max(dp_hi_count, 0.0), float(len(labels)))
    safe_count = max(float(dp_total_count), 1.0)
    dp_age_mean = dp_age_sum / safe_count
    dp_age_mean = max(age_domain.minimum, min(age_domain.maximum, dp_age_mean))

    hist_total = float(sum(dp_hist_counts))
    hist_prob = [count / max(hist_total, 1e-12) for count in dp_hist_counts]

    # 组装效用样本并生成效用报告
    utility_samples = []
    for eps, dp_value, noisy_values in count_hi_results:
        utility_samples.append(
            {
                "query_id": "count_hi",
                "mechanism": "gaussian",
                "epsilon": eps,
                "delta": gaussian_delta,
                "true_value": true_hi_count,
                "noisy_values": noisy_values,
            }
        )
    for eps, dp_value, noisy_values in total_count_results:
        utility_samples.append(
            {
                "query_id": "count_total",
                "mechanism": "gaussian",
                "epsilon": eps,
                "delta": gaussian_delta,
                "true_value": true_total_count,
                "noisy_values": noisy_values,
            }
        )
    for eps, dp_value, noisy_values in sum_results:
        utility_samples.append(
            {
                "query_id": "age_sum",
                "mechanism": "gaussian",
                "epsilon": eps,
                "delta": gaussian_delta,
                "true_value": true_age_sum,
                "noisy_values": noisy_values,
            }
        )
    utility_samples.append(
        {
            "query_id": "age_histogram",
            "mechanism": "vector_laplace",
            "epsilon": hist_eps,
            "delta": 0.0,
            "true_value": true_hist_counts,
            "noisy_values": dp_hist_counts,
        }
    )
    utility_report = UtilityReport.from_samples(utility_samples, metadata={"dataset": "adult"})
    utility_json_path = outdir / "40_dataset_smoke_cdp_utility_report.json"
    utility_md_path = outdir / "40_dataset_smoke_cdp_utility_report.md"
    utility_curve_data_path = outdir / "40_dataset_smoke_cdp_utility_curves.json"
    utility_json_path.write_text(utility_report.to_json(), encoding="utf-8")
    query_ids = sorted({rec.query_id for rec in utility_report.records})
    metric_names = ["mse", "mae", "rmse", "bias", "variance"]
    curve_data = {"metrics": list(metric_names), "queries": {}}
    for query_id in query_ids:
        per_query = {"metrics": {}}
        for metric in metric_names:
            curves = utility_report.get_error_vs_epsilon(metric, query_id=query_id)
            per_query["metrics"][metric] = None if not curves else curves[0].to_dict()
        curve_data["queries"][query_id] = per_query
    utility_curve_data_path = io.write_json(curve_data, utility_curve_data_path)
    utility_metrics_png = outdir / "40_dataset_smoke_cdp_utility_metrics_vs_epsilon_norm.png"
    selected_queries = [query_id for query_id in ("count_hi", "count_total", "age_sum") if query_id in query_ids]
    if selected_queries:
        utility_report.render_metrics_vs_epsilon_grid_png(
            utility_metrics_png,
            query_ids=selected_queries,
            metrics=metric_names,
            normalize=True,
        )
    else:
        utility_metrics_png = None

    utility_report_md = [utility_report.to_markdown()]
    if utility_metrics_png is not None:
        utility_image = _relative_md_path(utility_metrics_png, utility_md_path.parent)
        utility_report_md.extend(
            [
                "",
                "## Utility Curves (PNG)",
                f"![utility_metrics]({utility_image})",
                "",
            ]
        )
    utility_md_path.write_text("\n".join(utility_report_md), encoding="utf-8")

    # 复用会计事件生成隐私报告
    total_budget = accountant.total_budget
    cdp_accountant = CDPPrivacyAccountant(
        total_epsilon=None if total_budget is None else total_budget.epsilon,
        total_delta=None if total_budget is None else total_budget.delta,
    )
    for event in accountant.events:
        payload = {
            "epsilon": event.epsilon,
            "delta": event.delta,
            "description": event.description,
            "metadata": dict(event.metadata),
        }
        cdp_accountant.add_composed_event(
            [payload],
            description=event.description,
            metadata=dict(event.metadata),
        )
    report = PrivacyReport.from_accountant(cdp_accountant)

    curves_png = outdir / "40_dataset_smoke_cdp_budget_curves.png"
    report.render_budget_curves_png(
        curves_png,
        title="Privacy Budget Curves",
        y_tick_step=None,
        tick_label_fontsize=8,
    )

    # 直方图输出（PNG）
    labels = _bucket_labels(list(bucket_edges))

    hist_all_png = outdir / "40_dataset_smoke_cdp_hist_all.png"
    render_histogram_triptych_png(
        true_hist_counts,
        dp_hist_counts,
        hist_bins,
        hist_all_png,
        rotation=45,
        fontsize=6,
        y_tick_step=20,
        ylabel="count_age",
    )

    # 汇总 Markdown 报告
    report_path = outdir / "40_dataset_smoke_cdp_report.md"
    report_dir = report_path.parent
    utility_image = None if utility_metrics_png is None else _relative_md_path(utility_metrics_png, report_dir)
    utility_curve_lines = ["## Utility Curves (PNG)"]
    if utility_metrics_png is not None:
        utility_curve_lines.append(f"- metrics_vs_epsilon_norm: {utility_metrics_png}")
        utility_curve_lines.append(f"![utility_metrics]({utility_image})")
    utility_curve_lines.append("")
    utility_curve_lines.append("## Utility Curves (Data)")
    utility_curve_lines.append(f"- path: {utility_curve_data_path}")
    utility_curve_lines.append("")

    hist_image = _relative_md_path(hist_all_png, report_dir)
    budget_image = _relative_md_path(curves_png, report_dir)

    report_md = [
        "# Dataset Smoke CDP Report",
        "",
        "## Dataset",
        f"- data_path: {data_path}",
        f"- names_path: {names_path}",
        f"- rows_used: {len(records)}",
        f"- processed_dataset: {processed_path}",
        "",
        "## Raw Query Outputs (Non-DP)",
        f"- hi_count: {true_hi_count:.4f}",
        f"- total_count: {true_total_count:.4f}",
        f"- age_sum: {true_age_sum:.4f}",
        f"- age_mean: {true_age_mean:.4f}",
        f"- hist_counts: {true_hist_counts}",
        f"- hist_edges: {hist_bins}",
        "",
        "## DP Query Outputs",
        f"- dp_hi_count: {dp_hi_count:.4f}",
        f"- dp_total_count: {dp_total_count:.4f}",
        f"- dp_age_sum: {dp_age_sum:.4f}",
        f"- dp_age_mean: {dp_age_mean:.4f}",
        f"- dp_hist_counts: {dp_hist_counts}",
        f"- dp_hist_edges: {list(dp_hist_edges)}",
        "",
        "## Sensitivity Analysis",
        f"- count (income>50K): Δ= {count_sensitivity:.4f}",
        f"- count (total): Δ= {count_sensitivity:.4f}",
        f"- sum (age): Δ= {sum_sensitivity:.4f}",
        f"- histogram (age bins): Δ= {hist_sensitivity:.4f} per bin",
        "",
        "## Histogram (PNG)",
        f"- path: {hist_all_png}",
        f"![histogram_triptych]({hist_image})",
        "",
        "## Utility Report",
        utility_report.to_markdown(),
        "",
    ]
    report_md.extend(utility_curve_lines)
    report_md.extend(
        [
            "## Budget Curves (PNG)",
            f"- path: {curves_png}",
            f"![budget_curves]({budget_image})",
            "",
            "## Privacy Timeline",
            report.to_markdown(),
            "",
        ]
    )
    report_path.write_text("\n".join(report_md), encoding="utf-8")

    # JSON 汇总输出（供自动化或回归检查）
    result = {
        "name": "e2e/40_dataset_smoke_cdp",
        "config": {
            "data_path": str(data_path),
            "names_path": str(names_path),
            "n_rows": len(records),
            "age_bounds": (age_domain.minimum, age_domain.maximum),
            "age_edges": bucket_edges,
            "epsilons": {
                "count_hi": count_epsilons,
                "count_total": total_count_epsilons,
                "sum": sum_epsilons,
                "histogram": hist_eps,
            },
        },
        "outputs": {
            "raw_hi_count": true_hi_count,
            "raw_total_count": true_total_count,
            "raw_age_sum": true_age_sum,
            "raw_age_mean": true_age_mean,
            "raw_hist_counts": true_hist_counts,
            "raw_hist_edges": hist_bins,
            "dp_hi_count": dp_hi_count,
            "dp_total_count": dp_total_count,
            "dp_age_sum": dp_age_sum,
            "dp_age_mean": dp_age_mean,
            "dp_hist_counts": dp_hist_counts,
            "dp_hist_edges": list(dp_hist_edges),
        },
        "metrics": {
            "hist_prob_sum": sum(hist_prob),
        },
        "privacy": {
            "event_count": len(accountant.events),
            "spent_epsilon": accountant.spent.epsilon,
            "spent_delta": accountant.spent.delta,
            "report": report.to_dict(),
        },
        "artifacts": {
            "report_markdown": str(report_path),
            "processed_dataset": str(processed_path),
            "histogram_png": str(hist_all_png),
            "budget_curves_png": str(curves_png),
            "utility_metric_curve_png": None if utility_metrics_png is None else str(utility_metrics_png),
            "utility_curve_data_json": str(utility_curve_data_path),
            "utility_report_json": str(utility_json_path),
            "utility_report_markdown": str(utility_md_path),
        },
    }

    out_path = io.write_json(result, outdir / "40_dataset_smoke_cdp.json")
    result["artifacts"]["json"] = str(out_path)
    return result


if __name__ == "__main__":
    res = main()
    io.print_summary(res)
