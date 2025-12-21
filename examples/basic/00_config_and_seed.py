"""
Example 00: Configuration, Seeding, and Basic Data.

Goal:
    Demonstrate how to parse CLI arguments, set random seeds,
    and generate toy data using the shared utilities.

Extras:
    [core]

Usage:
    python examples/basic/00_config_and_seed.py --seed 123 --quick
"""
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path to ensure we can import examples._shared
# In a real install, examples would likely be outside the package, 
# but for this repo structure, we assume running from root or examples dir.
project_root = Path(__file__).resolve().parents[2]
src_root = project_root / "src"
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from examples._shared import cli, io, rng, toy_data

def main(argv=None):
    args = cli.parse_args("Basic Config Demo", argv)
    
    # 1. Setup Random Generator
    generator = rng.make_rng(args.seed)
    
    # 2. Configure sizes based on --quick flag
    n_users = 100 if args.quick else 1000
    
    # 3. Generate Data
    categories = ["A", "B", "C"]
    data_cat = toy_data.build_categorical_dataset(
        n_users=n_users, 
        categories=categories, 
        rng=generator
    )
    
    data_num = toy_data.build_numerical_dataset(
        n_users=n_users,
        low=0.0,
        high=100.0,
        rng=generator
    )
    
    # 4. Prepare Output
    result = {
        "name": "basic/00_config_and_seed",
        "config": {
            "seed": args.seed,
            "quick": args.quick,
            "n_users": n_users
        },
        "outputs": {
            "categorical_sample": data_cat[:5],
            "numerical_sample": data_num[:5].tolist()
        },
        "metrics": {
            "cat_count": len(data_cat),
            "num_mean": float(np.mean(data_num))
        },
        "artifacts": {}
    }
    
    # 5. Write to File
    out_path = io.write_json(result, Path(args.outdir) / "00_config.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
