"""
Example 14: Privacy Reporting.

Goal:
    Demonstrate generating rich privacy reports (JSON/Markdown) from the
    CDPPrivacyAccountant history.

Extras:
    [cdp]

Usage:
    python examples/cdp_examples/14_reporting_privacy_utility.py
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
from dplib.cdp.composition import CDPPrivacyAccountant
from dplib.cdp.analytics.reporting import PrivacyReport

def main(argv=None):
    args = cli.parse_args("Privacy Reporting", argv)
    
    # 1. Setup Accountant
    # We use CDPPrivacyAccountant which supports advanced composition tracking
    accountant = CDPPrivacyAccountant(total_epsilon=5.0, total_delta=1e-5)
    
    # 2. Simulate Privacy Events
    # In a real app, QueryEngine or Mechanisms would trigger these.
    # Here we manually record them.
    
    # Event 1: Simple Count
    accountant.add_composed_event(
        [{"epsilon": 0.5, "delta": 0.0}],
        description="Daily Active Users Count",
        metadata={"timestamp": "2023-01-01T10:00:00"}
    )
    
    # Event 2: Histogram (Multiple bins, but processed as one mechanism call usually)
    accountant.add_composed_event(
        [{"epsilon": 1.0, "delta": 1e-6}],
        description="Category Histogram",
        metadata={"timestamp": "2023-01-01T12:00:00"}
    )
    
    # Event 3: Heavy Query (Warning level)
    accountant.add_composed_event(
        [{"epsilon": 2.5, "delta": 0.0}],
        description="Deep Learning Model Training Step",
        metadata={"timestamp": "2023-01-01T14:00:00"}
    )
    
    # 3. Generate Report
    # Thresholds define when to warn about budget usage (e.g., warn at 50%, critical at 80%)
    report = PrivacyReport.from_accountant(accountant)
    report.generate_annotations(thresholds={
        "epsilon_warning_ratio": 0.5,
        "epsilon_critical_ratio": 0.8
    })
    
    # 4. Export
    json_output = report.to_json()
    md_output = report.to_markdown()
    
    # Print Markdown summary to stdout
    print("\n--- Privacy Budget Timeline ---")
    print(md_output)
    print("-------------------------------\n")
    
    result = {
        "name": "cdp_examples/14_reporting",
        "config": {
            "total_epsilon": 5.0
        },
        "privacy": {
            "spent": accountant.spent,
            "annotations": [a.to_dict() for a in report.annotations]
        },
        "outputs": {
            "markdown_preview": md_output
        },
        "metrics": {
            "events_count": len(report.events)
        },
        "artifacts": {}
    }
    
    # Save artifacts
    out_dir = Path(args.outdir)
    io.write_json(json.loads(json_output), out_dir / "14_report.json")
    
    with open(out_dir / "14_report.md", "w", encoding="utf-8") as f:
        f.write(md_output)
        
    result["artifacts"]["json"] = str(out_dir / "14_report.json")
    result["artifacts"]["markdown"] = str(out_dir / "14_report.md")
    
    return result

if __name__ == "__main__":
    import json
    res = main()
    io.print_summary(res)
