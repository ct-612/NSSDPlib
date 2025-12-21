"""
Example 30: E2E LDP Frequency Estimation Application.

Goal:
    Demonstrate the high-level `FrequencyEstimationApplication` which wraps
    encoding, mechanism, and aggregation into a unified workflow.

Extras:
    [ldp]

Usage:
    python examples/end_to_end/30_ldp_app_frequency_estimation.py
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

def main(argv=None):
    args = cli.parse_args("E2E Frequency App", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 1000 if args.quick else 5000
    categories = ["Phone", "Tablet", "Laptop", "Desktop"]
    weights = [0.5, 0.2, 0.2, 0.1]
    data = toy_data.build_categorical_dataset(n_users, categories, weights, rng=generator)
    
    # 1. Configuration
    config = FrequencyEstimationClientConfig(
        epsilon=3.0,
        categories=categories,
        mechanism="grr"
    )
    app = FrequencyEstimationApplication(client_config=config)
    
    # 2. Build Client (runs on user device)
    client_fn = app.build_client()
    
    # 3. Build Aggregator (runs on server)
    aggregator = app.build_aggregator()
    
    # 4. Simulate collection
    reports = []
    for i, val in enumerate(data):
        # User client logic
        # client_fn takes (value, user_id)
        report = client_fn(val, str(i))
        reports.append(report)
        
    # 5. Server Aggregation
    estimate = aggregator.aggregate(reports)
    
    # 6. Analysis
    est_dist = estimate.point
    true_counts = np.array([data.count(c) for c in categories])
    true_dist = true_counts / n_users
    
    est_dict = {cat: float(est_dist[i]) for i, cat in enumerate(categories)}
    true_dict = {cat: float(true_dist[i]) for i, cat in enumerate(categories)}
    
    result = {
        "name": "e2e/30_frequency_app",
        "config": {
            "n_users": n_users,
            "epsilon": config.epsilon,
            "mechanism": config.mechanism
        },
        "outputs": {
            "estimate": est_dict
        },
        "metrics": {
            "l1_error": metrics.l1_error(est_dist, true_dist)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "30_frequency_app.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
