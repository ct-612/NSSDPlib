"""
Example 03: Composition Quickstart.

Goal:
    Demonstrate Basic Composition theorem application.
    (Summing epsilons for sequential queries).

Extras:
    [cdp]

Usage:
    python examples/basic/03_composition_quickstart.py
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
src_root = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from examples._shared import cli, io
from dplib.cdp.mechanisms import LaplaceMechanism
from dplib.core.privacy import PrivacyAccountant

def main(argv=None):
    args = cli.parse_args("Composition Quickstart", argv)
    
    # 1. Setup a Accountant
    total_epsilon = 2.0
    accountant = PrivacyAccountant(total_epsilon=total_epsilon)
    
    # 2. Sequential Composition
    # We run a sequence of queries. Basic composition says:
    # Total Cost = Sum(Cost_i)
    
    n_queries = 5
    eps_per_query = 0.3
    
    results = []
    
    print(f"Total Budget: {total_epsilon}")
    print(f"Planning {n_queries} queries at {eps_per_query} each.")
    
    for i in range(n_queries):
        # Check if we have budget
        rem = accountant.remaining.epsilon if accountant.remaining else 0
        if rem < eps_per_query:
            print(f"Query {i+1}: Insufficient budget! Stopping.")
            break
            
        # Create a mechanism for this query
        # Note: In a real system, the accountant would handle this check/spend
        mech = LaplaceMechanism(epsilon=eps_per_query)
        mech.calibrate(sensitivity=1.0)
        
        # Simulate query
        val = mech.randomise(10.0)
        results.append(val)
        
        # Manually track spend (or use PrivacyAccountant)
        accountant.add_event(epsilon=eps_per_query)
        rem_now = accountant.remaining.epsilon if accountant.remaining else 0
        print(f"Query {i+1}: Spent {eps_per_query:.1f}, Remaining: {rem_now:.1f}")
        
    result = {
        "name": "basic/03_composition",
        "config": {
            "total_epsilon": total_epsilon,
            "queries": n_queries,
            "epsilon_per_query": eps_per_query
        },
        "outputs": {
            "query_results": results
        },
        "privacy": {
            "used_epsilon": accountant.spent.epsilon,
            "remaining_epsilon": accountant.remaining.epsilon if accountant.remaining else None
        },
        "metrics": {
            "queries_completed": len(results)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "03_composition.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
