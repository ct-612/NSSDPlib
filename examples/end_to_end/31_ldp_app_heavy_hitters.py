"""
Example 31: E2E LDP Heavy Hitters Application.

Goal:
    Demonstrate finding frequent items (Heavy Hitters) without estimating full distribution.
    Uses HeavyHittersApplication (wrapper around FrequencyAggregator with top-k helpers).

Extras:
    [ldp]

Usage:
    python examples/end_to_end/31_ldp_app_heavy_hitters.py
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

from examples._shared import cli, io, rng, toy_data
from dplib.ldp.applications import HeavyHittersApplication
from dplib.ldp.applications.heavy_hitters import HeavyHittersClientConfig, extract_top_k

def main(argv=None):
    args = cli.parse_args("E2E Heavy Hitters", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 2000 if args.quick else 10000
    # Long tail distribution: Few heavy hitters, many rare items
    categories = ["Hit_A", "Hit_B", "Hit_C"] + [f"Rare_{i}" for i in range(50)]
    # Heavy hitters get 80% weight
    weights = [0.5, 0.2, 0.1] + [0.2/50]*50
    # Normalize weights
    weights = np.array(weights)
    weights /= weights.sum()
    
    data = toy_data.build_categorical_dataset(n_users, categories, list(weights), rng=generator)
    
    # 1. Config
    config = HeavyHittersClientConfig(
        epsilon=3.0,
        categories=categories,
        top_k=5
    )
    app = HeavyHittersApplication(client_config=config)
    
    # 2. Pipeline
    client_fn = app.build_client()
    aggregator = app.build_aggregator()
    
    reports = []
    for i, val in enumerate(data):
        reports.append(client_fn(val, str(i)))
        
    estimate = aggregator.aggregate(reports)
    
    # 3. Extract Top K
    top_k_list = extract_top_k(estimate, top_k=5)
    
    # Convert for JSON
    outputs = [{"category": str(k), "frequency": float(v)} for k, v in top_k_list]
    
    result = {
        "name": "e2e/31_heavy_hitters",
        "config": {
            "n_users": n_users,
            "epsilon": config.epsilon,
            "top_k": 5
        },
        "outputs": {
            "top_k": outputs
        },
        "metrics": {
            # Check if Hit_A is first
            "top_1_match": outputs[0]["category"] == "Hit_A" if outputs else False
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "31_heavy_hitters.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
