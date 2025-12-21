"""
Example 02: Privacy Accountant Basics.

Goal:
    Demonstrate how to track privacy budget consumption using PrivacyAccountant.

Extras:
    [core]

Usage:
    python examples/basic/02_accountant_basics.py
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
from dplib.core.privacy import PrivacyAccountant, BudgetExceededError

def main(argv=None):
    args = cli.parse_args("Accountant Basics", argv)
    
    # 1. Initialize Accountant
    # Global budget: epsilon=10.0, delta=1e-5
    accountant = PrivacyAccountant(total_epsilon=10.0, total_delta=1e-5, name="GlobalAccountant")
    
    # 2. Consume Budget
    # Simulate mechanisms consuming budget
    logs = []
    
    try:
        # Request 1: Small spend
        accountant.add_event(epsilon=1.0, delta=0.0, description="Query 1")
        logs.append("Query 1 successful")
        
        # Request 2: Another spend
        accountant.add_event(epsilon=5.0, delta=0.0, description="Query 2")
        logs.append("Query 2 successful")
        
        # Request 3: Large spend (might fail depending on remaining)
        # Remaining: 10 - 1 - 5 = 4.0
        # Asking for 5.0 -> Should fail
        accountant.add_event(epsilon=5.0, delta=0.0, description="Query 3 (Big)")
        logs.append("Query 3 successful")
        
    except BudgetExceededError as e:
        logs.append(f"Query 3 failed as expected: {e}")

    # 3. Check Status
    used_eps = accountant.spent.epsilon
    rem_eps = accountant.remaining.epsilon if accountant.remaining else None

    result = {
        "name": "basic/02_accountant_basics",
        "config": {
            "initial_epsilon": 10.0
        },
        "privacy": {
            "used_epsilon": used_eps,
            "remaining_epsilon": rem_eps,
            "history": [e.to_dict() for e in accountant.events]
        },
        "outputs": {
            "logs": logs
        },
        "metrics": {
            "queries_processed": len(accountant.events)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "02_accountant.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)