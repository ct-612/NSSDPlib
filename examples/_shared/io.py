"""
Input/Output helpers for examples.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Union

def ensure_outdir(path: Union[str, Path]) -> Path:
    """Ensure the output directory exists."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

def write_json(data: Dict[str, Any], path: Union[str, Path]) -> Path:
    """Write data to a JSON file."""
    p = Path(path)
    ensure_outdir(p.parent)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    return p

def print_summary(result: Dict[str, Any]) -> None:
    """
    Print a summary of the example result to stdout.
    
    Expects result dict to have keys: 'name', 'config', 'metrics', 'artifacts'.
    """
    print("=" * 60)
    print(f"EXAMPLE: {result.get('name', 'Unknown')}")
    print("-" * 60)
    
    if "config" in result:
        print("Config:")
        for k, v in result["config"].items():
            print(f"  {k}: {v}")
    
    if "metrics" in result and result["metrics"]:
        print("-" * 60)
        print("Metrics:")
        for k, v in result["metrics"].items():
            print(f"  {k}: {v}")
            
    if "artifacts" in result and result["artifacts"]:
        print("-" * 60)
        print("Artifacts:")
        for k, v in result["artifacts"].items():
            print(f"  {k}: {v}")
            
    print("=" * 60)
