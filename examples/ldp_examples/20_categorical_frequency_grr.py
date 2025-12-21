"""
Example 20: LDP Categorical Frequency (GRR).

Goal:
    Demonstrate low-level LDP pipeline:
    Categorical Encoding -> GRR Perturbation -> Aggregation.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/20_categorical_frequency_grr.py
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
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.mechanisms.discrete import GRRMechanism
from dplib.ldp.aggregators import FrequencyAggregator

from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP GRR", argv)
    generator = rng.make_rng(args.seed)
    
    # 1. Setup Data
    n_users = 1000 if args.quick else 10000
    categories = ["A", "B", "C", "D"]
    weights = [0.4, 0.3, 0.2, 0.1]
    data = toy_data.build_categorical_dataset(n_users, categories, weights, rng=generator)
    
    # 2. Client Side: Encode + Randomise
    epsilon = 2.0
    
    # Fit encoder to know domain
    encoder = CategoricalEncoder(categories=categories)
    domain_size = len(categories)
    
    mechanism = GRRMechanism(epsilon=epsilon, domain_size=domain_size)
    
    reports = []
    for i, user_val in enumerate(data):
        # Encode: Value -> Index (integer)
        encoded_val = encoder.encode(user_val)
        # Randomise: Index -> Noisy Index
        noisy_val = mechanism.randomise(encoded_val)
        
        # Wrap in LDPReport
        report = LDPReport(
            user_id=str(i),
            mechanism_id="grr",
            epsilon=epsilon,
            encoded=noisy_val,
            metadata={"domain_size": domain_size}
        )
        reports.append(report)
        
    # 3. Server Side: Aggregate
    aggregator = FrequencyAggregator(num_categories=domain_size, mechanism="grr")
    estimate = aggregator.aggregate(reports)
    
    # Normalize to probabilities
    est_dist = estimate.point
    
    # Compare with ground truth
    true_counts = np.array([data.count(c) for c in categories])
    true_dist = true_counts / n_users
    
    # Map back to labels for display
    est_dict = {cat: float(est_dist[i]) for i, cat in enumerate(categories)}
    true_dict = {cat: float(true_dist[i]) for i, cat in enumerate(categories)}
    
    result = {
        "name": "ldp_examples/20_grr",
        "config": {
            "n_users": n_users,
            "epsilon": epsilon
        },
        "outputs": {
            "estimated_distribution": est_dict,
            "true_distribution": true_dict
        },
        "metrics": {
            "l1_error": metrics.l1_error(est_dist, true_dist),
            "max_error": metrics.max_abs_error(est_dist, true_dist)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "20_grr.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
