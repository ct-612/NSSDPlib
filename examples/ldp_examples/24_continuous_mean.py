"""
Example 24: Continuous Mean Estimation.

Goal:
    Demonstrate aggregating continuous values using Local Laplace Mechanism.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/24_continuous_mean.py
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
from dplib.ldp.mechanisms.continuous import LocalLaplaceMechanism
from dplib.ldp.aggregators import MeanAggregator
from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP Continuous Mean", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 1000 if args.quick else 5000
    # True data: Gaussian centered at 50.0
    true_mean = 50.0
    true_std = 10.0
    data = generator.normal(true_mean, true_std, n_users)
    
    # 1. Setup
    epsilon = 1.0
    clip_range = (0.0, 100.0) # Domain knowledge
    
    # Calculate noise variance for debiasing
    # Local Laplace: scale = (max-min)/epsilon
    sensitivity = clip_range[1] - clip_range[0]
    scale = sensitivity / epsilon
    noise_variance = 2 * (scale ** 2)
    
    mech = LocalLaplaceMechanism(epsilon=epsilon, clip_range=clip_range)
    
    # 2. Client
    reports = []
    for i, val in enumerate(data):
        clipped_val = max(min(val, clip_range[1]), clip_range[0])
        noisy_val = mech.randomise(clipped_val)
        
        report = LDPReport(
            user_id=str(i),
            mechanism_id="local_laplace",
            epsilon=epsilon,
            encoded=noisy_val,
            metadata={
                "clip_range": clip_range,
                "noise_variance": noise_variance
            }
        )
        reports.append(report)
        
    # 3. Aggregator
    # MeanAggregator can subtract noise variance from observed variance if provided
    aggregator = MeanAggregator(clip_range=clip_range, noise_variance=noise_variance)
    estimate = aggregator.aggregate(reports)
    
    est_mean = estimate.point
    est_var = estimate.variance
    
    result = {
        "name": "ldp_examples/24_continuous_mean",
        "config": {
            "n_users": n_users,
            "epsilon": epsilon,
            "clip_range": clip_range
        },
        "outputs": {
            "estimated_mean": est_mean,
            "estimated_variance": est_var
        },
        "metrics": {
            "mean_error": abs(est_mean - true_mean),
            # Variance error might be high due to fourth moment of noise, but check basic range
            "variance_sanity": est_var # Just report it
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "24_mean.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
