"""
Example 33: Cross-Module Accounting (LDP & CDP).

Goal:
    Demonstrate how to track LDP data collection events within a central
    Privacy Accountant. While LDP and CDP budgets are distinct (Local vs Central),
    organizations often need a unified log of all privacy-impacting activities.

Extras:
    [all]

Usage:
    python examples/end_to_end/33_cross_module_accounting.py
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
from dplib.core.privacy import PrivacyAccountant

def main(argv=None):
    args = cli.parse_args("Cross Module Accounting", argv)
    
    # 1. Central Accountant
    accountant = PrivacyAccountant(total_epsilon=10.0, name="MasterLedger")
    
    # 2. Activity 1: Central Query
    accountant.add_event(epsilon=1.0, description="Central Mean Query")
    
    # 3. Activity 2: LDP Data Collection
    # LDP protects users *before* data leaves their device.
    # From a "Central Budget" perspective, we typically don't "spend" central epsilon 
    # in the same way, because the server never sees raw data.
    # However, we record it for compliance/audit.
    
    local_epsilon = 3.0
    campaign_name = "User Preference Survey"
    
    # We record this with 0 central cost (usually), but log the local guarantee.
    # OR, if we are using the "Shuffle Model", we might calculate the
    # equivalent Central DP amplification and log THAT.
    
    # Here, we just log it as a metadata event.
    accountant.add_event(
        epsilon=0.0,
        delta=0.0,
        description=f"LDP Collection: {campaign_name}",
        metadata={
            "module": "ldp",
            "local_epsilon": local_epsilon,
            "mechanism": "GRR",
            "n_users_target": 10000
        }
    )
    
    result = {
        "name": "e2e/33_cross_accounting",
        "config": {
            "local_epsilon": local_epsilon
        },
        "privacy": {
            "history": [e.to_dict() for e in accountant.events]
        },
        "outputs": {
            "log_summary": "Recorded 1 Central Spend and 1 LDP Event."
        },
        "metrics": {},
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "33_accounting.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
