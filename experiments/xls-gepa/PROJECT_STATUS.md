# XLS + GEPA IDCT experiment

## Status: completed

- Persistent containers: `xls-gepa-work` and `xls-gepa-ollama`; caches and mounted workspace preserved.
- XLS tools built successfully from commit `0a7c502ccaaa650cb2da1929c536c4ab100eafda`.
- Exact HLSFactory IDCT source preserved from commit `2aba8756de8e2fab1d1095b2483cfa695bf3be10`; source SHA256 `1166b8a58483a166550de600e1d910c3b12c253682ba0fc5156ae17e637cbced`.
- Five original DSLX tests passed. The unchanged source matched the pinned original on 527 deterministic edge/random inputs and passed XLS equivalence checking against that same original.
- Evaluator validation passed: unchanged source reproduced the baseline; a deliberately incorrect constant was rejected with score zero.
- Fixed baseline estimates: unit-model critical path 40, ASAP7 critical-path estimate 8488 ps, 1883 optimized IR nodes, and 4096 register bits.
- Real GEPA run completed with pinned GEPA commit `3f160c295000dd31db3d438c3d17553c23cc5f81` and local `qwen2.5-coder:3b` through Ollama.
- Two model calls were made at $0 external cost. Both generated candidates failed DSLX validation. GEPA retained the valid unchanged baseline.
- Improvement achieved: **no**. This is a completed working loop, not evidence of optimization success.
- Run evidence: `results/gepa/20261001-224747/`; flat comparison: `results/comparison.csv`; report: `REPORT.md`.

## Reproduction

The normal baseline/evaluator and local GEPA commands are documented in `README.md`. Do not delete either container or Docker volume if the cached XLS tools and local model should be retained.

## Next useful experiment

Try a stronger DSLX-capable local model or a larger bounded search while keeping the evaluator and XLS configuration unchanged. No paid model access is required for the completed experiment.

