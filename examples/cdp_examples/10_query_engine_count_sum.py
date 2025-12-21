"""
Example 10: CDP Query Engine (Count & Sum).

Goal:
    Demonstrate using the high-level QueryEngine for basic aggregate queries
    (Count and Sum) with automatic accounting.

Extras:
    [cdp]

Usage:
    python examples/cdp_examples/10_query_engine_count_sum.py
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
from dplib.cdp.analytics.queries.query_engine import QueryEngine
from dplib.core.privacy import PrivacyAccountant

def main(argv=None):
    args = cli.parse_args("CDP Count/Sum", argv)
    generator = rng.make_rng(args.seed)
    
    # 1. Setup Accountant
    accountant = PrivacyAccountant(total_epsilon=10.0, name="QueryEngineAccountant")
    
    # 2. Setup Query Engine
    engine = QueryEngine(accountant=accountant)
    
    # 3. Generate Data
    n_users = 100 if args.quick else 1000
    # Numerical data for SUM (e.g., salaries 20k-100k)
    data = toy_data.build_numerical_dataset(
        n_users=n_users, low=20.0, high=100.0, rng=generator
    )
    
    # 4. Execute Queries
    # Count: No bounds needed usually, but some implementations might check sensitivity
    # Sum: Requires bounds to bound sensitivity
    
    count_eps = 0.5
    sum_eps = 1.0
    sum_bounds = (0.0, 100.0)
    
    count_res = engine.execute("count", data=data, epsilon=count_eps)
    sum_res = engine.execute("sum", data=data, epsilon=sum_eps, bounds=sum_bounds)
    
    true_sum = float(np.sum(data))
    true_count = len(data)
    
    result = {
        "name": "cdp_examples/10_query_engine_count_sum",
        "config": {
            "n_users": n_users,
            "count_eps": count_eps,
            "sum_eps": sum_eps,
            "sum_bounds": sum_bounds
        },
        "outputs": {
            "count": count_res,
            "sum": sum_res
        },
        "privacy": {
            "used_epsilon": accountant.spent.epsilon,
            "history_len": len(accountant.events)
        },
        "metrics": {
            "count_error": abs(count_res - true_count),
            "sum_error": abs(sum_res - true_sum),
            "sum_rel_error": abs(sum_res - true_sum) / true_sum if true_sum > 0 else 0
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "10_queries.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
