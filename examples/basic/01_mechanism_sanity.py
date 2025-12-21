"""
Example 01: Mechanism Lifecycle Sanity Check.

Goal:
    Demonstrate the standard lifecycle of a CDP mechanism:
    Init -> Calibrate -> Randomise -> Serialize.

Extras:
    [cdp]

Usage:
    python examples/basic/01_mechanism_sanity.py
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
from dplib.cdp.mechanisms import LaplaceMechanism

def main(argv=None):
    args = cli.parse_args("Mechanism Sanity", argv)
    generator = rng.make_rng(args.seed)
    
    # 1. Initialize Mechanism
    epsilon = 1.0
    mech = LaplaceMechanism(epsilon=epsilon, rng=generator)
    
    # 2. Define Sensitivity (e.g., counting users, sensitivity=1)
    sensitivity = 1.0
    
    # 3. Calibrate
    # This calculates the noise scale based on epsilon and sensitivity
    mech.calibrate(sensitivity=sensitivity)
    
    # 4. Randomise (Add Noise)
    true_value = 100.0
    noisy_value = mech.randomise(true_value)
    
    # 5. Serialization Round-Trip
    # Ensure we can save and load the mechanism state
    data = mech.serialize()
    mech_restored = LaplaceMechanism.deserialize(data)
    
    # Check if restored mechanism works
    # Note: deserialize does NOT restore the RNG state, so we re-seed if we want exact same noise sequence,
    # but here we just check property consistency.
    
    result = {
        "name": "basic/01_mechanism_sanity",
        "config": {
            "epsilon": epsilon,
            "sensitivity": sensitivity
        },
        "outputs": {
            "true_value": true_value,
            "noisy_value": noisy_value,
            "scale": mech.scale, # Accessing internal scale
            "serialized": data
        },
        "metrics": {
            "noise_magnitude": float(abs(noisy_value - true_value)),
            "restored_epsilon": mech_restored.epsilon
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "01_mechanism.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
