# NSSDPlib Examples

This directory contains executable examples demonstrating the core features of `dplib`.

## Structure

- `basic/`: Fundamental concepts (Configuration, Mechanisms, Accounting).
- `cdp_examples/`: Centralized Differential Privacy (Trusted Server).
- `ldp_examples/`: Local Differential Privacy (User-side protection).
- `end_to_end/`: Complete application scenarios.
- `_shared/`: Utilities used by examples.

## Running Examples

### Prerequisites

Install the library with the necessary extras:

- **Minimal Core**: `pip install -e ".[core]"`
- **CDP Only**: `pip install -e ".[cdp]"`
- **CDP+ML**: `pip install -e ".[cdp,ml]"`
- **LDP Only**: `pip install -e ".[ldp]"`
- **Standard (no torch/tf)**: `pip install -e ".[standard]"`
- **Full (torch/tf backends)**: `pip install -e ".[full]"`

### Running a Single Example

Each script can be run directly. It is recommended to use the `--quick` flag for faster execution during testing.

```bash
# Basic Mechanism Example
python examples/basic/01_mechanism_sanity.py --quick

# LDP Frequency Estimation
python examples/ldp_examples/20_categorical_frequency_grr.py --quick --seed 42
```

### Running All Examples

Use the runner script to execute a batch of examples.

```bash
# Run all P0 (priority 0) examples in quick mode
python examples/run_all.py --quick --include-tags p0

# Run only LDP examples
python examples/run_all.py --quick --require-extras ldp
```

## Common CLI Arguments

All examples support the following arguments (via `examples._shared.cli`):

- `--seed <int>`: Set random seed (default: 0).
- `--quick`: Reduce dataset sizes/iterations for fast verification.
- `--outdir <path>`: Directory to save JSON outputs (default: `./_outputs`).
- `--format <json>`: Output format.

## Outputs

Scripts print a summary to `stdout` and save detailed structured data (Metrics, Config, Privacy Params) to JSON files in the specified `outdir`.
