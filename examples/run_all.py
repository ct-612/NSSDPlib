"""
Master runner for all examples.
"""
import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Set

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from examples.registry import EXAMPLES

def main():
    parser = argparse.ArgumentParser(description="Run NSSDPlib examples.")
    parser.add_argument("--quick", action="store_true", help="Run examples in quick mode")
    parser.add_argument("--seed", type=int, default=0, help="Global random seed")
    parser.add_argument("--outdir", type=str, default="./_outputs", help="Output directory base")
    parser.add_argument("--include-tags", type=str, help="Comma-separated tags to include (e.g., 'p0,cdp')")
    parser.add_argument("--require-extras", type=str, help="Comma-separated extras required (e.g., 'ldp')")
    parser.add_argument("--exclude-experimental", action="store_true", default=True, help="Skip experimental examples")
    parser.add_argument("--include-experimental", action="store_false", dest="exclude_experimental", help="Include experimental examples")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent # Project root (assuming run_all is in examples/)
    # Fix: run_all.py is in examples/, so base_dir should be project root f:\VS Code-Workspace\NSSDPlib
    # __file__ = examples/run_all.py -> parent = examples -> parent = root
    
    include_tags = set(args.include_tags.split(",")) if args.include_tags else set()
    require_extras = set(args.require_extras.split(",")) if args.require_extras else set()
    
    passed = []
    failed = []
    skipped = []
    
    print(f"Running examples with seed={args.seed}, quick={args.quick}")
    print("-" * 60)

    for entry in EXAMPLES:
        path_str = entry["path"]
        full_path = Path(__file__).parent / path_str
        
        # Filters
        if args.exclude_experimental and entry["experimental"]:
            skipped.append((path_str, "Experimental"))
            continue
            
        if include_tags:
            entry_tags = set(entry["tags"])
            if not include_tags.intersection(entry_tags):
                skipped.append((path_str, "Tag mismatch"))
                continue
                
        if require_extras:
            entry_extras = set(entry["extras"])
            # Logic: If I ask for 'ldp', script must HAVE ldp in its extras? 
            # Or does it mean "run only if current env supports ldp"? 
            # Interpretation: "Run scripts that require these extras" or "Run scripts whose extras are covered by these".
            # Let's assume strict intersection for filtering: if I say --require-extras ldp, I only want ldp scripts.
            if not require_extras.intersection(entry_extras):
                 skipped.append((path_str, "Extra mismatch"))
                 continue
        
        if not full_path.exists():
            failed.append((path_str, "File not found"))
            print(f"[FAIL] {path_str} (File not found)")
            if args.fail_fast: break
            continue

        # Construct command
        cmd = [sys.executable, str(full_path), "--seed", str(args.seed), "--outdir", args.outdir]
        if args.quick:
            cmd.append("--quick")
            
        print(f"[RUN ] {path_str} ...", end="", flush=True)
        try:
            # Run in subprocess to isolate
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(" [PASS]")
                passed.append(path_str)
            else:
                print(" [FAIL]")
                print(f"  Exit Code: {result.returncode}")
                print("  Stderr:")
                print(result.stderr)
                failed.append((path_str, "Runtime Error"))
                if args.fail_fast: break
        except Exception as e:
            print(" [ERR ]")
            print(f"  Exception: {e}")
            failed.append((path_str, str(e)))
            if args.fail_fast: break

    print("-" * 60)
    print(f"Summary: {len(passed)} Passed, {len(failed)} Failed, {len(skipped)} Skipped")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
