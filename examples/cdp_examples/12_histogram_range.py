"""
Example 12: CDP Histogram and Range Queries.

Goal:
    Demonstrate Histogram (categorical/binned) and Range queries.

Extras:
    [cdp]

Usage:
    python examples/cdp_examples/12_histogram_range.py
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
from dplib.cdp.analytics.queries.query_engine import QueryEngine
from dplib.core.privacy import PrivacyAccountant

def main(argv=None):
    args = cli.parse_args("CDP Histogram/Range", argv)
    generator = rng.make_rng(args.seed)
    
    accountant = PrivacyAccountant(total_epsilon=10.0)
    engine = QueryEngine(accountant=accountant)
    
    n_users = 100 if args.quick else 1000
    
    # --- Histogram ---
    # Categorical data: "Red", "Green", "Blue"
    categories = ["Red", "Green", "Blue"]
    data_cat = toy_data.build_categorical_dataset(n_users, categories, rng=generator)
    category_to_index = {cat: idx for idx, cat in enumerate(categories)}
    data_cat_indices = [category_to_index[val] for val in data_cat]
    
    hist_eps = 1.0
    hist_bins = list(range(len(categories) + 1))
    hist_counts, hist_edges = engine.execute(
        "histogram",
        data=data_cat_indices,
        bins=hist_bins,
        epsilon=hist_eps,
    )
    
    # Calculate truth
    true_counts = {c: data_cat.count(c) for c in categories}
    
    # --- Range Query ---
    # Numerical data
    data_num = toy_data.build_numerical_dataset(n_users, 0, 100, rng=generator)
    
    # Ranges: [0, 20], [20, 50], [50, 100]
    ranges = [(0, 20), (20, 50), (50, 100)]
    range_eps = 1.0
    # Range query usually answers "sum" or "count" over these ranges
    range_res = engine.execute(
        "range", 
        data=data_num, 
        ranges=ranges, 
        epsilon=range_eps, 
        bounds=(0, 100),
        metric="count"
    )
    
    # True ranges
    true_ranges = []
    for (low, high) in ranges:
        count = np.sum((data_num >= low) & (data_num < high)) # Simple half-open check
        true_ranges.append(int(count))
        
    result = {
        "name": "cdp_examples/12_histogram_range",
        "config": {
            "bins": categories,
            "ranges": ranges
        },
        "outputs": {
            "histogram": dict(zip(categories, hist_counts)),
            "histogram_bins": list(hist_edges),
            "range_counts": range_res if isinstance(range_res, list) else list(range_res)
        },
        "metrics": {
            # Simple error metric
            # Depending on return type, assume simple matching by index
        },
        "artifacts": {}
    }
    
    out_path = io.write_json(result, Path(args.outdir) / "12_hist_range.json")
    result["artifacts"]["json"] = str(out_path)
    
    return result

if __name__ == "__main__":
    res = main()
    io.print_summary(res)
