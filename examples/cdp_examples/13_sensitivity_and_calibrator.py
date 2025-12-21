"""
Example 13: Sensitivity and Calibration.

Goal:
    Demonstrate explicit noise calibration (calculating scale/sigma) 
    given epsilon and sensitivity constraints.

Extras:
    [cdp]

Usage:
    python examples/cdp_examples/13_sensitivity_and_calibrator.py
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
from dplib.cdp.sensitivity import calibrate

def main(argv=None):
    args = cli.parse_args("Sensitivity/Calibration", argv)
    
    # 1. Scenarios using functional API
    
    # Scenario A: Laplace Mechanism, Sensitivity=1, Epsilon=0.5
    # We want to find the 'scale'
    # calibrate returns (param_name, value)
    name_a, scale_a = calibrate(
        mechanism="laplace",
        epsilon=0.5,
        sensitivity=1.0
    )
    
    # Scenario B: Gaussian Mechanism, Sensitivity=1, Epsilon=1.0, Delta=1e-5
    # We want to find 'sigma'
    name_b, sigma_b = calibrate(
        mechanism="gaussian",
        epsilon=1.0,
        delta=1e-5,
        sensitivity=1.0
    )
    
    # Scenario C: Inverse Calibration (What epsilon do I get for this noise?)
    # E.g., if I use Laplace scale=2.0 with sensitivity=1.0
    # epsilon = sensitivity / scale = 1 / 2 = 0.5
    # Manual calculation since library doesn't expose inverse
    target_scale = 2.0
    sens_c = 1.0
    epsilon_c = sens_c / target_scale
    
    result = {
        "name": "cdp_examples/13_sensitivity",
        "config": {},
        "outputs": {
            "scenario_a": {"param": name_a, "value": scale_a},
            "scenario_b": {"param": name_b, "value": sigma_b},
            "scenario_c_inverse": {"epsilon": epsilon_c}
        },
        "metrics": {},
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "13_calibration.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
