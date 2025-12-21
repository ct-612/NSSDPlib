"""
Example 23: RAPPOR with Bloom Filters.

Goal:
    Demonstrate using Bloom Filters for encoding and RAPPOR for perturbation.
    This setup allows collecting set-valued data or strings without a fixed dictionary,
    though decoding (finding heavy hitters) requires statistical inference (e.g. LASSO)
    which is outside the scope of the aggregator.
    
    We will verify that the estimated bit frequencies for a frequent item
    are higher than background noise.

Extras:
    [ldp]

Usage:
    python examples/ldp_examples/23_rappor_bloom.py
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

from examples._shared import cli, io, rng, metrics
from dplib.ldp.mechanisms.discrete import RAPPORMechanism
from dplib.ldp.encoders import BloomFilterEncoder
from dplib.ldp.aggregators import FrequencyAggregator
from dplib.ldp.types import LDPReport

def main(argv=None):
    args = cli.parse_args("LDP RAPPOR", argv)
    generator = rng.make_rng(args.seed)
    
    # 1. Setup
    n_users = 2000 if args.quick else 10000
    bloom_size = 128
    num_hashes = 2
    epsilon = 2.0
    
    encoder = BloomFilterEncoder(num_bits=bloom_size, num_hashes=num_hashes, seed=42)
    mechanism = RAPPORMechanism(epsilon=epsilon)
    
    # Target item "Apple" is frequent
    target_item = "Apple"
    target_bits = encoder.encode(target_item) # BitArray or list
    # Convert target bits to indices for checking later
    # BloomFilterEncoder output is usually bitarray-like or list of 0/1.
    # We'll assume list of ints for simplicity check.
    target_indices = [i for i, b in enumerate(target_bits) if b]
    
    # Generate Data: 50% users have "Apple", 50% have random noise (or "Banana")
    reports = []
    
    for i in range(n_users):
        if generator.random() < 0.5:
            val = target_item
        else:
            val = "Banana"
            
        encoded = encoder.encode(val)
        noisy = mechanism.randomise(encoded)
        
        report = LDPReport(
            user_id=str(i),
            mechanism_id="rappor",
            epsilon=epsilon,
            encoded=noisy,
            metadata={
                "p": mechanism.p,
                "q": mechanism.q
            }
        )
        reports.append(report)
        
    # 2. Aggregation
    # RAPPOR bits are aggregated independently
    # FrequencyAggregator handles bit vectors if they are uniform length
    aggregator = FrequencyAggregator(mechanism="rappor")
    
    # Aggregator returns an Estimate where .point is the vector of bit frequencies
    estimate = aggregator.aggregate(reports)
    bit_freqs = estimate.point
    
    # 3. Validation
    # Check if bits corresponding to "Apple" have frequency approx 0.5 (since 50% users have it)
    # Bits for "Banana" also 0.5 (since 50% have it).
    # Bits overlapping?
    
    apple_bits = [i for i, b in enumerate(encoder.encode("Apple")) if b]
    banana_bits = [i for i, b in enumerate(encoder.encode("Banana")) if b]
    
    # Expected frequency for Apple bits: ~0.5 (if no collision with Banana)
    # Background noise is removed by debiasing in aggregator.
    
    avg_apple_freq = float(np.mean([bit_freqs[i] for i in apple_bits]))
    
    # Compare with a bit that is likely 0 (not in Apple or Banana)
    # We scan for a bit index not in either
    used_indices = set(apple_bits) | set(banana_bits)
    unused_indices = [i for i in range(bloom_size) if i not in used_indices]
    
    avg_noise_freq = 0.0
    if unused_indices:
        avg_noise_freq = float(np.mean([bit_freqs[i] for i in unused_indices]))
        
    result = {
        "name": "ldp_examples/23_rappor",
        "config": {
            "n_users": n_users,
            "bloom_size": bloom_size,
            "epsilon": epsilon
        },
        "outputs": {
            "apple_bit_indices": apple_bits,
            "estimated_bit_frequencies_apple": [float(bit_freqs[i]) for i in apple_bits],
            "average_signal": avg_apple_freq,
            "average_noise": avg_noise_freq
        },
        "metrics": {
            # Signal should be roughly 0.5, Noise roughly 0.0
            "signal_strength": avg_apple_freq
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "23_rappor.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
