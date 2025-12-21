"""
Example 26: LDP User-Level Aggregation.

Goal:
    Demonstrate aggregating multiple reports from the same user into a single
    estimate, then merging across users.
    Useful when users contribute data multiple times (e.g. daily usage) and we 
    want "average daily usage" per user, then "average of averages" across population.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/26_user_level_merge.py
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
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.aggregators import FrequencyAggregator, UserLevelAggregator
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP User-Level", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 100 if args.quick else 500
    reports_per_user = 10
    
    categories = ["A", "B", "C"]
    encoder = CategoricalEncoder(categories=categories)
    domain_size = len(categories)
    
    epsilon = 2.0
    mech = GRRMechanism(epsilon=epsilon, domain_size=domain_size)
    
    # Generate Data: Each user has a "true" preference, but reports noisy versions multiple times
    all_reports = []
    
    for u in range(n_users):
        user_id = f"user_{u}"
        # Randomly pick a true preference for this user
        true_pref = generator.choice(categories)
        encoded_pref = encoder.encode(true_pref)
        
        for r in range(reports_per_user):
            # Apply mechanism
            noisy = mech.randomise(encoded_pref)
            
            report = LDPReport(
                user_id=user_id,
                mechanism_id="grr",
                epsilon=epsilon,
                encoded=noisy,
                metadata={"domain_size": domain_size}
            )
            all_reports.append(report)
            
    # Aggregation
    
    # 1. Inner Aggregator: How to aggregate ONE user's reports?
    # FrequencyAggregator will compute the frequency distribution of the user's reports.
    # Since the user reports the same true value repeatedly (with noise), 
    # the inner aggregation gives a clearer picture of that user's true value.
    inner_agg = FrequencyAggregator(num_categories=domain_size, mechanism="grr")
    
    # 2. Outer Aggregator: Merge user estimates
    # "equal" weighting means each user contributes equally to the final result,
    # regardless of how many reports they sent (though here all sent 10).
    user_agg = UserLevelAggregator(
        inner_aggregator=inner_agg,
        weight_mode="equal"
    )
    
    estimate = user_agg.aggregate(all_reports)
    
    result = {
        "name": "ldp_examples/26_user_level",
        "config": {
            "n_users": n_users,
            "reports_per_user": reports_per_user,
            "epsilon": epsilon
        },
        "outputs": {
            "estimated_distribution": list(estimate.point)
        },
        "metrics": {
            "num_users_aggregated": estimate.metadata.get("num_users")
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "26_user_merge.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
