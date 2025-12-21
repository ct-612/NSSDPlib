"""
Example 22: OLH (Optimised Local Hashing) Frequency.

Goal:
    Demonstrate OLH mechanism usage.
    Note: The library's OLHMechanism uses a fixed hash seed per instance.
    To use it for frequency estimation, we treat the hashed values as
    a new domain and use FrequencyAggregator on that domain, then map back
    (assuming no collisions or handling them).

    This example simplifies by using hash_range >= domain_size to avoid collisions,
    effectively acting as a randomized response on a permuted domain.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/22_olh_frequency.py
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
from dplib.ldp.mechanisms.discrete import OLHMechanism
from dplib.ldp.encoders import CategoricalEncoder
from dplib.ldp.aggregators import FrequencyAggregator
from dplib.ldp.ldp_utils import make_hash_family
from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP OLH", argv)
    generator = rng.make_rng(args.seed)
    
    n_users = 1000 if args.quick else 5000
    categories = ["Apple", "Banana", "Cherry", "Date"]
    weights = [0.4, 0.3, 0.2, 0.1]
    data = toy_data.build_categorical_dataset(n_users, categories, weights, rng=generator)
    
    # 1. Setup OLH
    # hash_range >= domain_size to ensure unique mapping for this demo
    domain_size = len(categories)
    hash_range = domain_size * 2 
    epsilon = 3.0
    
    encoder = CategoricalEncoder(categories=categories)
    
    # In a real deployment, hash_seed might vary or be fixed system-wide
    hash_seed = 42
    mech = OLHMechanism(
        epsilon=epsilon,
        domain_size=domain_size,
        hash_range=hash_range,
        hash_seed=hash_seed
    )
    
    # Pre-calculate the mapping V -> H to decode later
    # (Since we use a fixed seed, this mapping is static)
    # Build the same hash function using the public utility with the same seed.
    hash_fn = make_hash_family(1, hash_range, hash_seed)[0]
    
    val_to_hash = {}
    for i in range(domain_size):
        h = hash_fn(str(i))
        val_to_hash[i] = h
        
    # 2. Client Side
    reports = []
    for i, user_val in enumerate(data):
        # Value -> Index
        idx = encoder.encode(user_val)
        # Index -> Noisy Hash
        noisy_hash = mech.randomise(idx)
        
        report = LDPReport(
            user_id=str(i),
            mechanism_id="olh",
            epsilon=epsilon,
            encoded=noisy_hash,
            metadata={
                "domain_size": hash_range, # We aggregate over the HASH domain
                "prob_true": mech.p,
                "prob_false": mech.q
            }
        )
        reports.append(report)
        
    # 3. Aggregation (on Hash Domain)
    # We estimate frequency of each hash value in [0, hash_range)
    aggregator = FrequencyAggregator(num_categories=hash_range, mechanism="grr")
    hash_estimate = aggregator.aggregate(reports)
    hash_freqs = hash_estimate.point # Array of size hash_range
    
    # 4. Decode (Hash -> Value)
    # est_freq(v) = est_freq_hash(H(v))
    est_dist = np.zeros(domain_size)
    for v_idx, h_val in val_to_hash.items():
        if h_val < len(hash_freqs):
            est_dist[v_idx] = hash_freqs[h_val]
            
    # Normalize (since we mapped subset)
    total = est_dist.sum()
    if total > 0:
        est_dist /= total
        
    # Truth
    true_counts = np.array([data.count(c) for c in categories])
    true_dist = true_counts / n_users
    
    est_dict = {cat: float(est_dist[i]) for i, cat in enumerate(categories)}
    
    result = {
        "name": "ldp_examples/22_olh",
        "config": {
            "n_users": n_users,
            "hash_range": hash_range,
            "epsilon": epsilon
        },
        "outputs": {
            "estimated_distribution": est_dict
        },
        "metrics": {
            "l1_error": metrics.l1_error(est_dist, true_dist)
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "22_olh.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
