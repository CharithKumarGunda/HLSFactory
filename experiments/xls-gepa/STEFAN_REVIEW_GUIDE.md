# XLS + GEPA IDCT experiment — reviewer guide

## Result

A bounded, XLS-specific GEPA experiment ran on the pinned `idct_chen.x` design. The original passed its five DSLX tests. An unchanged candidate matched the original on 527 deterministic inputs and passed XLS equivalence checking against that same original. The evaluator rejected a deliberately incorrect implementation. GEPA made two calls to a local Qwen2.5-Coder 3B model at zero external cost; both proposed candidates failed DSLX validation, so the original remained the best candidate. No optimization improvement was achieved.

## How to review

1. Start with [REPORT.md](REPORT.md) for methods, metrics, results, and limits.
2. See [results/comparison.csv](results/comparison.csv) for the baseline, unchanged-source check, negative-control candidate, and two GEPA candidates.
3. Inspect `results/gepa/20261001-224747/summary.json`, `candidates.json`, and reflection responses for run details.
4. Read `reference/idct_chen.x`, [evaluate.py](evaluate.py), and [run_gepa.py](run_gepa.py) for the benchmark and experiment code.

## Metric caveats

The 40 unit-delay value is an abstract XLS delay-model estimate. The 8,488 ps ASAP7 number is a technology-model estimate. Neither is measured FPGA timing. IR node count and register bits are proxies, not LUT or physical-area reports.

## Reproduction

The full local setup, pinned versions, and rerun commands are in [README.md](README.md). Reproduction expects the persistent local Docker environment and its XLS build cache; this guide is a map to the experiment files, not a standalone Docker image.

