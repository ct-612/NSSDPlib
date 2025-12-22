"""
Example 35: E2E LDP Full Pipeline.

Goal:
    Demonstrate a complete LDP workflow:
    config -> client reports -> accounting -> aggregation -> evaluation.

Extras:
    [ldp]

Usage:
    python examples/end_to_end/35_ldp_full_pipeline.py
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
from dplib.ldp.applications import FrequencyEstimationApplication
from dplib.ldp.applications.frequency_estimation import FrequencyEstimationClientConfig
from dplib.ldp.composition.privacy_accountant import LDPPrivacyAccountant
from dplib.ldp.types import LocalPrivacyUsage


def main(argv=None):
    args = cli.parse_args("E2E LDP Full Pipeline", argv)
    generator = rng.make_rng(args.seed)

    # 1. Data setup
    n_users = 1000 if args.quick else 5000
    categories = ["A", "B", "C", "D"]
    weights = [0.4, 0.3, 0.2, 0.1]
    data = toy_data.build_categorical_dataset(n_users, categories, weights, rng=generator)

    # 2. Configure application pipeline
    config = FrequencyEstimationClientConfig(epsilon=3.0, categories=categories)
    app = FrequencyEstimationApplication(client_config=config)
    client = app.build_client()
    # Stabilize randomness for repeatable demo output
    if app._mechanism is not None:
        app._mechanism.reseed(args.seed)
    aggregator = app.build_aggregator()

    # 3. Track local privacy usage per user
    accountant = LDPPrivacyAccountant(per_user_epsilon_limit=5.0)

    # 4. Collect reports from clients
    reports = []
    for idx, value in enumerate(data):
        user_id = f"user_{idx}"
        report = client(value, user_id)
        reports.append(report)
        usage = LocalPrivacyUsage(
            user_id=user_id,
            epsilon=report.epsilon,
            round_id=1,
            metadata={"mechanism": report.mechanism_id},
        )
        accountant.add_usage(usage)

    # 5. Aggregate and evaluate
    estimate = aggregator.aggregate(reports)
    est_dist = np.asarray(estimate.point, dtype=float)

    true_counts = np.array([data.count(c) for c in categories])
    true_dist = true_counts / n_users
    est_dict = {cat: float(est_dist[i]) for i, cat in enumerate(categories)}
    true_dict = {cat: float(true_dist[i]) for i, cat in enumerate(categories)}

    # 6. Summarize budget usage
    summary = accountant.summarize()
    per_user_sample = list(summary.per_user_epsilon.items())[:3]

    # Package outputs + metrics for a quick JSON artifact
    result = {
        "name": "e2e/35_ldp_full_pipeline",
        "config": {
            "n_users": n_users,
            "epsilon": config.epsilon,
            "categories": categories,
        },
        "outputs": {
            "estimated_distribution": est_dict,
            "true_distribution": true_dict,
            "budget_summary": {
                "total_epsilon": summary.total_epsilon,
                "max_user_epsilon": summary.max_user_epsilon,
                "n_events": summary.n_events,
                "per_user_sample": per_user_sample,
            },
        },
        "metrics": {
            "l1_error": metrics.l1_error(est_dist, true_dist),
            "max_error": metrics.max_abs_error(est_dist, true_dist),
        },
        "artifacts": {},
    }

    # Persist results for inspection
    out_path = io.write_json(result, Path(args.outdir) / "35_ldp_full_pipeline.json")
    result["artifacts"]["json"] = str(out_path)

    return result


if __name__ == "__main__":
    res = main()
    io.print_summary(res)
