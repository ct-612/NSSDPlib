"""
Registry of available examples.
"""
from typing import Dict, List, TypedDict, Optional

class ExampleMetadata(TypedDict):
    path: str
    extras: List[str]
    tags: List[str]
    experimental: bool
    optional_deps: List[str]
    description: str

EXAMPLES: List[ExampleMetadata] = [
    # --- Basic ---
    {
        "path": "basic/00_config_and_seed.py",
        "extras": ["core"],
        "tags": ["basic", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Demonstrates configuration, seeding, and logging setup."
    },
    {
        "path": "basic/01_mechanism_sanity.py",
        "extras": ["core", "cdp"],
        "tags": ["basic", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Demonstrates basic mechanism lifecycle: calibration, noise, serialization."
    },
    {
        "path": "basic/02_accountant_basics.py",
        "extras": ["core"],
        "tags": ["basic", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Demonstrates privacy accounting and budget tracking."
    },
    {
        "path": "basic/03_composition_quickstart.py",
        "extras": ["core", "cdp"],
        "tags": ["basic", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Demonstrates basic and advanced composition of privacy budgets."
    },

    # --- CDP ---
    {
        "path": "cdp_examples/10_query_engine_count_sum.py",
        "extras": ["cdp"],
        "tags": ["cdp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Dataset, Domain, and basic Count/Sum queries with accounting."
    },
    {
        "path": "cdp_examples/11_query_engine_mean_var.py",
        "extras": ["cdp"],
        "tags": ["cdp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Mean and Variance queries demonstrating composite mechanisms."
    },
    {
        "path": "cdp_examples/12_histogram_range.py",
        "extras": ["cdp"],
        "tags": ["cdp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Histogram and Range queries."
    },
    {
        "path": "cdp_examples/13_sensitivity_and_calibrator.py",
        "extras": ["cdp"],
        "tags": ["cdp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Deep dive into sensitivity analysis and noise calibration."
    },
    {
        "path": "cdp_examples/14_reporting_privacy_utility.py",
        "extras": ["cdp"],
        "tags": ["cdp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Generate privacy reports (JSON/Markdown) from accountant history."
    },

    # --- LDP ---
    {
        "path": "ldp_examples/20_categorical_frequency_grr.py",
        "extras": ["ldp"],
        "tags": ["ldp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Categorical frequency estimation using Generalized Randomized Response (GRR)."
    },
    {
        "path": "ldp_examples/21_unary_oue_frequency.py",
        "extras": ["ldp"],
        "tags": ["ldp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Frequency estimation using Unary Encoding and OUE."
    },
    {
        "path": "ldp_examples/22_olh_frequency.py",
        "extras": ["ldp"],
        "tags": ["ldp"],
        "experimental": False,
        "optional_deps": [],
        "description": "Optimised Local Hashing (OLH) mechanism usage."
    },
    {
        "path": "ldp_examples/23_rappor_bloom.py",
        "extras": ["ldp"],
        "tags": ["ldp"],
        "experimental": False,
        "optional_deps": [],
        "description": "RAPPOR mechanism with Bloom Filter encoding."
    },
    {
        "path": "ldp_examples/24_continuous_mean.py",
        "extras": ["ldp"],
        "tags": ["ldp"],
        "experimental": False,
        "optional_deps": [],
        "description": "Continuous mean estimation using Local Laplace mechanism."
    },
    {
        "path": "ldp_examples/25_multiround_composition.py",
        "extras": ["ldp"],
        "tags": ["ldp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Simulates multi-round reporting and sequential composition."
    },
    {
        "path": "ldp_examples/26_user_level_merge.py",
        "extras": ["ldp"],
        "tags": ["ldp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "User-level aggregation (combining multiple reports from one user)."
    },

    # --- End-to-End ---
    {
        "path": "end_to_end/30_ldp_app_frequency_estimation.py",
        "extras": ["ldp"],
        "tags": ["e2e", "ldp", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "End-to-end frequency estimation application usage."
    },
    {
        "path": "end_to_end/31_ldp_app_heavy_hitters.py",
        "extras": ["ldp"],
        "tags": ["e2e", "ldp"],
        "experimental": False,
        "optional_deps": [],
        "description": "End-to-end heavy hitters application."
    },
    {
        "path": "end_to_end/32_ldp_app_range_queries.py",
        "extras": ["ldp"],
        "tags": ["e2e", "ldp"],
        "experimental": False,
        "optional_deps": [],
        "description": "End-to-end range queries (mean & quantiles) application."
    },
    {
        "path": "end_to_end/33_cross_module_accounting.py",
        "extras": ["all"],
        "tags": ["e2e", "p0"],
        "experimental": False,
        "optional_deps": [],
        "description": "Demonstrates bridging LDP budget summaries into core privacy accounting."
    },
]
