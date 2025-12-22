"""
Example 34: E2E CDP Pipeline.

Goal:
    Demonstrate a full CDP workflow:
    data -> QueryEngine -> PrivacyAccountant -> PrivacyReport.

Extras:
    [cdp]

Usage:
    python examples/end_to_end/34_cdp_pipeline.py
"""
import sys
from pathlib import Path
import numpy as np

project_root = Path(__file__).resolve().parents[2]
src_root = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from examples._shared import cli, io, rng, toy_data, metrics
from dplib.cdp.analytics.queries import QueryEngine
from dplib.cdp.analytics.reporting import PrivacyReport
from dplib.cdp.composition import CDPPrivacyAccountant
from dplib.core.privacy import PrivacyAccountant


def main(argv=None):
    args = cli.parse_args("E2E CDP Pipeline", argv)
    generator = rng.make_rng(args.seed)

    # 1. Data setup
    n_users = 1000 if args.quick else 5000
    bounds = (0.0, 100.0)
    data = toy_data.build_numerical_dataset(
        n_users=n_users, low=bounds[0], high=bounds[1], rng=generator
    )

    # 2. Accountant + QueryEngine
    accountant = PrivacyAccountant(total_epsilon=6.0, total_delta=1e-6, name="CDPPipeline")
    engine = QueryEngine(accountant=accountant)

    # 3. Query budget allocation
    count_eps = 0.5
    sum_eps = 0.5
    mean_eps = 1.0
    var_eps = 1.0
    hist_eps = 1.0
    range_eps = 1.0

    # 4. Execute queries
    count_res = engine.execute("count", data=data, epsilon=count_eps)
    sum_res = engine.execute("sum", data=data, epsilon=sum_eps, bounds=bounds)
    mean_res = engine.execute("mean", data=data, epsilon=mean_eps, bounds=bounds)
    var_res = engine.execute("variance", data=data, epsilon=var_eps, bounds=bounds)

    # 5. Histogram + range queries
    # Use numeric bin edges for histogram over the bounded domain
    hist_bins = [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
    hist_counts, hist_edges = engine.execute(
        "histogram", data=data, bins=hist_bins, epsilon=hist_eps
    )

    # Range queries use index slices over the dataset
    range_slices = [
        (0, n_users // 3),
        (n_users // 3, 2 * n_users // 3),
        (2 * n_users // 3, n_users),
    ]
    range_res = engine.execute(
        "range",
        data=data,
        ranges=range_slices,
        bounds=bounds,
        epsilon=range_eps,
        metric="sum",
    )

    # 6. Ground truth for evaluation
    true_count = float(n_users)
    true_sum = float(np.sum(data))
    true_mean = float(np.mean(data))
    true_var = float(np.var(data, ddof=1))
    true_hist, _ = np.histogram(data, bins=hist_bins)
    true_ranges = [float(np.sum(data[start:end])) for start, end in range_slices]

    # 7. Generate a privacy report snapshot
    # PrivacyReport expects a CDPPrivacyAccountant, so replay core events into it
    cdp_accountant = CDPPrivacyAccountant(total_epsilon=6.0, total_delta=1e-6)
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

    # Package outputs + metrics for a quick JSON artifact
    result = {
        "name": "e2e/34_cdp_pipeline",
        "config": {
            "n_users": n_users,
            "bounds": bounds,
            "hist_bins": hist_bins,
            "range_slices": range_slices,
            "epsilons": {
                "count": count_eps,
                "sum": sum_eps,
                "mean": mean_eps,
                "variance": var_eps,
                "histogram": hist_eps,
                "range": range_eps,
            },
        },
        "outputs": {
            "count": count_res,
            "sum": sum_res,
            "mean": mean_res,
            "variance": var_res,
            "histogram_counts": list(hist_counts),
            "histogram_edges": list(hist_edges),
            "range_sums": list(range_res),
            "privacy_report": report.to_json(),
        },
        "metrics": {
            "count_error": abs(count_res - true_count),
            "sum_error": abs(sum_res - true_sum),
            "mean_error": abs(mean_res - true_mean),
            "variance_error": abs(var_res - true_var),
            "hist_l1_error": metrics.l1_error(hist_counts, true_hist),
            "range_l1_error": metrics.l1_error(range_res, true_ranges),
        },
        "privacy": {
            "spent_epsilon": cdp_accountant.spent[0],
            "event_count": len(cdp_accountant.events),
        },
        "artifacts": {},
    }

    # Persist results for inspection
    out_path = io.write_json(result, Path(args.outdir) / "34_cdp_pipeline.json")
    result["artifacts"]["json"] = str(out_path)

    return result


if __name__ == "__main__":
    res = main()
    io.print_summary(res)
