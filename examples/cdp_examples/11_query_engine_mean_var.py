"""
Example 11: CDP Query Engine (Mean & Variance).

Goal:
    Demonstrate Mean and Variance queries, which involve composite mechanisms
    (combining Count and Sum internally).

Extras:
    [cdp]

Usage:
    python examples/cdp_examples/11_query_engine_mean_var.py
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
    args = cli.parse_args("CDP Mean/Var", argv)
    generator = rng.make_rng(args.seed)
    
    # 1. Setup Accountant
    accountant = PrivacyAccountant(total_epsilon=10.0, name="MeanVarAccountant")
    engine = QueryEngine(accountant=accountant)
    
    # 2. Data
    n_users = 200 if args.quick else 2000
    data = toy_data.build_numerical_dataset(
        n_users=n_users, low=0.0, high=10.0, rng=generator
    )
    
    # 3. Queries
    # Mean requires epsilon and bounds
    mean_eps = 1.0
    bounds = (0.0, 10.0)
    
    mean_res = engine.execute("mean", data=data, epsilon=mean_eps, bounds=bounds)
    
    # Variance requires epsilon and bounds
    var_eps = 1.0
    var_res = engine.execute("variance", data=data, epsilon=var_eps, bounds=bounds)
    
    true_mean = float(np.mean(data))
    true_var = float(np.var(data, ddof=1)) # Default ddof=1 for variance query usually
    
    result = {
        "name": "cdp_examples/11_query_engine_mean_var",
        "config": {
            "n_users": n_users,
            "bounds": bounds,
            "mean_eps": mean_eps,
            "var_eps": var_eps
        },
        "outputs": {
            "mean": mean_res,
            "variance": var_res
        },
        "privacy": {
            "used_epsilon": accountant.spent.epsilon,
            # Note: Mean splits epsilon into count/sum, Var splits into count/sum/squares
            # The accountant should show these aggregate events or sub-events depending on implementation
            "history": [e.description for e in accountant.events]
        },
        "metrics": {
            "mean_error": abs(mean_res - true_mean),
            "var_error": abs(var_res - true_var)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "11_mean_var.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
