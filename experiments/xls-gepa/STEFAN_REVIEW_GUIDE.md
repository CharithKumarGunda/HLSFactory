# XLS + GEPA IDCT experiment — reviewer guide

## Result

The 2026-10-30 manual rewrite is recorded separately from GEPA. The second manual rewrite passed all five protected tests, 527 differential inputs, and XLS equivalence against the pinned original. It kept the fixed unit-model delay at 40, reduced the secondary ASAP7 estimate from 8488 to 8424 ps, and reduced optimized IR nodes from 1883 to 1820. Its score did not improve because the fixed objective is unit-model delay. The first manual attempt failed DSLX's unused-binding check; the exact error is retained in its evaluation `result.json`.

The bounded local GEPA retry with a stricter DSLX prompt completed in `results/gepa/20261030-175936/`. Of two model requests, one produced a DSLX-invalid candidate and the second timed out before producing a candidate. The original remained best; no fixed-objective improvement was achieved.

A bounded, XLS-specific GEPA experiment ran on the pinned `idct_chen.x` design. The original passed its five DSLX tests. An unchanged candidate matched the original on 527 deterministic inputs and passed XLS equivalence checking against that same original. The evaluator rejected a deliberately incorrect implementation. GEPA made two calls to a local Qwen2.5-Coder 3B model at zero external cost; both proposed candidates failed DSLX validation, so the original remained the best candidate. No optimization improvement was achieved.

## How to review

1. Start with [REPORT.md](REPORT.md) for methods, metrics, results, and limits.
2. See [results/comparison.csv](results/comparison.csv) for the baseline, unchanged-source check, negative-control candidate, manual rewrites, and evaluated GEPA candidates.
   See `results/manual-controls.json` for the distinct manual controls and exact per-candidate evaluation paths.
3. Inspect both GEPA summaries (`20261001-224747` and `20261030-175936`) and the retry run log for candidate results and the timeout.
4. Read `reference/idct_chen.x`, [evaluate.py](evaluate.py), and [run_gepa.py](run_gepa.py) for the benchmark and experiment code.

## Metric caveats

The 40 unit-delay value is an abstract XLS delay-model estimate. The 8,488 ps ASAP7 number is a technology-model estimate. Neither is measured FPGA timing. IR node count and register bits are proxies, not LUT or physical-area reports.

## Reproduction

The full local setup, pinned versions, and rerun commands are in [README.md](README.md). Reproduction expects the persistent local Docker environment and its XLS build cache; this guide is a map to the experiment files, not a standalone Docker image.

