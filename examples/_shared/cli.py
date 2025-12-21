"""
Unified CLI argument parsing for examples.
"""
import argparse
import sys
from typing import Optional, List

def build_parser(description: str) -> argparse.ArgumentParser:
    """Build a standard ArgumentParser with common flags."""
    parser = argparse.ArgumentParser(description=description)
    
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Random seed for reproducibility (default: 0)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run in quick mode (smaller datasets, fewer iterations)"
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default="./_outputs",
        help="Directory to save output files (default: ./_outputs relative to execution)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json"],
        default="json",
        help="Output format (default: json)"
    )
    
    return parser

def parse_args(description: str, argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse arguments for an example script."""
    parser = build_parser(description)
    if argv is None:
        argv = sys.argv[1:]
    return parser.parse_args(argv)
