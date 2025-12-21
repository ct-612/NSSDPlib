"""
Example 32: E2E LDP Range Queries Application.

Goal:
    Demonstrate collecting numeric data to estimate Mean and Quantiles
    using the RangeQueriesApplication wrapper.

Extras:
    [ldp]

Usage:
    python examples/end_to_end/32_ldp_app_range_queries.py
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

from examples._shared import cli, io, rng
from dplib.ldp.applications import RangeQueriesApplication
from dplib.ldp.applications.range_queries import RangeQueriesClientConfig, RangeQueriesServerConfig

def main(argv=None):
    args = cli.parse_args("E2E Range Queries", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 1000 if args.quick else 5000
    # True data: Uniform [20, 80]
    data = generator.uniform(20.0, 80.0, n_users)
    
    # 1. Config
    clip_range = (0.0, 100.0)
    client_config = RangeQueriesClientConfig(
        epsilon=1.0,
        clip_range=clip_range
    )
    server_config = RangeQueriesServerConfig(
        estimate_mean=True,
        estimate_quantiles=[0.25, 0.5, 0.75] # Quartiles
    )
    
    app = RangeQueriesApplication(client_config, server_config)
    
    # 2. Pipeline
    client_fn = app.build_client()
    aggregator = app.build_aggregator()
    
    reports = []
    for i, val in enumerate(data):
        reports.append(client_fn(val, str(i)))
        
    estimate = aggregator.aggregate(reports)
    
    # Estimate point is dict with 'mean' and 'quantiles'
    est_mean = estimate.point.get("mean")
    est_quantiles = estimate.point.get("quantiles")
    
    true_mean = float(np.mean(data))
    true_quantiles = np.quantile(data, [0.25, 0.5, 0.75])
    
    result = {
        "name": "e2e/32_range_queries",
        "config": {
            "epsilon": client_config.epsilon,
            "clip_range": clip_range
        },
        "outputs": {
            "estimated_mean": est_mean,
            "estimated_quantiles": list(est_quantiles) if est_quantiles is not None else None
        },
        "metrics": {
            "mean_error": abs(est_mean - true_mean) if est_mean is not None else None,
            "median_error": abs(est_quantiles[1] - true_quantiles[1]) if est_quantiles is not None else None
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "32_range_queries.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
