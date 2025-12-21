"""
Example 21: LDP Unary Encoding + OUE.

Goal:
    Demonstrate OUE (Optimised Unary Encoding) pipeline.
    This often provides better variance/utility than GRR for larger domains.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/21_unary_oue_frequency.py
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
from dplib.ldp.encoders import CategoricalEncoder, UnaryEncoder
from dplib.ldp.mechanisms.discrete import OUEMechanism
from dplib.ldp.aggregators import FrequencyAggregator
from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP OUE", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 500 if args.quick else 5000
    # Larger domain than GRR example to show OUE benefit
    categories = [f"Cat_{i}" for i in range(20)]
    weights = np.random.dirichlet(np.ones(len(categories)), size=1)[0]
    data = toy_data.build_categorical_dataset(n_users, categories, weights, rng=generator)
    
    # Encoder
    encoder = CategoricalEncoder(categories=categories)
    domain_size = len(categories)
    unary_encoder = UnaryEncoder(length=domain_size)
    
    # Mechanism
    epsilon = 2.0
    mechanism = OUEMechanism(epsilon=epsilon)
    
    # Collect Reports
    reports = []
    for i, user_val in enumerate(data):
        category_index = encoder.encode(user_val)
        encoded = unary_encoder.encode(category_index)
        noisy = mechanism.randomise(encoded)
        
        # Manually create report since we aren't using Application wrapper
        meta = mechanism.serialize()
        meta.update({"domain_size": domain_size}) # Help aggregator
        report = LDPReport(
            user_id=str(i),
            mechanism_id="oue",
            epsilon=epsilon,
            encoded=noisy,
            metadata=meta
        )
        reports.append(report)
        
    # Aggregate
    aggregator = FrequencyAggregator(num_categories=domain_size, mechanism="oue")
    estimate = aggregator.aggregate(reports)
    
    # Compare
    true_counts = np.array([data.count(c) for c in categories])
    true_dist = true_counts / n_users
    
    est_dist = estimate.point
    
    # Map back
    est_dict = {cat: float(est_dist[i]) for i, cat in enumerate(categories)}
    true_dict = {cat: float(true_dist[i]) for i, cat in enumerate(categories)}
    
    result = {
        "name": "ldp_examples/21_oue",
        "config": {
            "n_users": n_users,
            "epsilon": epsilon,
            "domain_size": domain_size
        },
        "outputs": {
            "estimated_distribution": est_dict
        },
        "metrics": {
            "l1_error": metrics.l1_error(est_dist, true_dist),
            "max_error": metrics.max_abs_error(est_dist, true_dist)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "21_oue.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
