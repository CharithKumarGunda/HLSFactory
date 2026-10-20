# IDCT XLS + GEPA research report

Only DSLX implementation source is optimized. Scheduling/codegen remain fixed at a one-stage pipeline with unit delay model and registered input/output. No Vitis or HLS-Eval work was performed.

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

Correctness: tested_equivalent. Formal result: proven_equivalent.

## Evaluator verification

The unchanged implementation passed and matched baseline metrics. A deliberately incorrect W1 constant was rejected with score zero. An uncached baseline rerun produced identical metrics.

## GEPA outcome

Real GEPA experiment completed. Improvement achieved: **False**.

Two model-generated candidates were attempted. Both failed DSLX validation, so GEPA retained the unchanged, formally equivalent baseline. No optimization improvement is claimed.

The latest results/gepa run contains candidate source, lineage, reflection logs, token usage, and baseline-versus-best metrics.

## Limitations and next experiment

Unit-model delay is an abstract XLS dependency-depth estimate from a dummy testing model, despite the generic tool output label ps. A separately labeled ASAP7 critical-path estimate is recorded when available and does not affect scheduling or the objective. Neither is measured FPGA or placed-and-routed timing. IR operations and register bits are resource proxies, not LUT usage or physical area. Tests do not prove equivalence over all inputs; proof timeout/error is inconclusive.

This small local model produced two invalid DSLX candidates, so the run demonstrates a working protected optimization loop but not an improvement. A useful next experiment is a larger DSLX-capable local model or a larger bounded search, keeping the same evaluator and fixed XLS settings.

