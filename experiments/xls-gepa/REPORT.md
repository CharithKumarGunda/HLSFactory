# IDCT XLS + GEPA research report

The search was configured to rewrite only DSLX implementation source. Scheduling/codegen remained fixed at a one-stage pipeline with unit delay model and registered input/output. This prototype did not include Vitis or HLS-Eval integration.

## Evidence completed

- Exact linked HLSFactory source preserved with pinned commit and SHA256; five original tests identified.
- Persistent Docker environment and build cache established; machine inventory and XLS source commit recorded.
- Evaluator code, deterministic 527-case corpus, and actual GEPA adapter integration validated.
- The real bounded GEPA run used a local Qwen2.5-Coder 3B model through Ollama at zero external cost.

## Baseline

```json
{
  "critical_path_unit_delay": 40,
  "optimized_ir_node_count": 1883,
  "optimized_ir_operation_counts": {
    "add": 296,
    "array": 1,
    "array_index": 64,
    "bit_slice": 592,
    "concat": 184,
    "literal": 82,
    "sign_ext": 264,
    "sub": 224,
    "umul": 176
  },
  "asap7_critical_path_estimate_ps": 8488,
  "block_register_bits": 4096,
  "block_reg_to_reg_unit_delay": 40,
  "block_input_to_reg_unit_delay": 0,
  "block_reg_to_output_unit_delay": 0
}
```

The unchanged implementation passed the 527 comparisons and XLS equivalence check against the pinned original. This validates the evaluator on unchanged source; it does not independently prove the original IDCT against a mathematical specification.

## Evaluator verification

The unchanged implementation passed and matched baseline metrics. A deliberately incorrect W1 constant was rejected with score zero. An uncached baseline rerun produced identical metrics.

## Manual DSLX rewrites (not GEPA-generated)

The first row-butterfly rewrite was rejected because two local constants became unused; the full DSLX compiler message is saved in its per-candidate result.json.

The second manual rewrite passed all five protected tests, 527 deterministic comparisons, and XLS equivalence checking. Its fixed unit-model critical path is 40 versus 40 for baseline, so the score is unchanged. The secondary ASAP7 estimate is 8424 ps versus 8488 ps, optimized IR nodes are 1820 versus 1883, and register bits are 4096 for both.

See `results/manual-controls.json` for source hashes and exact evaluation paths.

## GEPA outcome

Real GEPA experiment completed. Improvement achieved: **False**.

The latest bounded local run (`20261030-175936`) attempted 2 local model requests at an estimated external cost of $0.00. One response produced a candidate rejected by DSLX validation; the second request timed out and produced no candidate. Its selected best candidate has fixed unit delay 40 versus 40 for baseline. See `results/comparison.csv` and the run log for the separate outcomes.

The local run directory contains generated source, lineage, reflection logs, token usage, and baseline-versus-best metrics; the review branch includes selected text artifacts.

## Limitations and next experiment

Unit-model delay is an abstract XLS dependency-depth estimate from a dummy testing model, despite the generic tool output label ps. A separately labeled ASAP7 critical-path estimate is recorded when available and does not affect scheduling or the objective. Neither is measured FPGA or placed-and-routed timing. IR operations and register bits are resource proxies, not LUT usage or physical area. Tests do not prove equivalence over all inputs; proof timeout/error is inconclusive.

A useful next experiment is a larger DSLX-capable local model or a larger bounded search, keeping the same evaluator and fixed XLS settings.

