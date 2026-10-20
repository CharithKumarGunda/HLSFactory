# XLS + GEPA IDCT research prototype

This experiment rewrites DSLX implementation source only. XLS scheduling and code generation are fixed. No Vitis support or HLS-Eval integration is included.

## Current state

The XLS tools, evaluator, and bounded local GEPA experiment are complete. See `STEFAN_REVIEW_GUIDE.md` for the review path, `REPORT.md` for results, and `PROJECT_STATUS.md` for exact versions and next steps. Two GEPA candidates failed DSLX validation, so no optimization improvement was achieved.

## Environment

The original run used Docker Desktop on Windows. The project folder was mounted at `/workspace` in a persistent container named `xls-gepa-work`. Its local image was `xls-build-docker:latest`; the XLS checkout was at `/home/xls-developer/xls` inside the container. That image and the compiled XLS binaries are not included in this review branch.

Do not delete the container or run cleanup: the build cache is in its writable layer. Keep Docker running and the computer awake during builds. All experiment source, logs and results are stored in this Windows directory.

Inspect the existing build before starting another:

```powershell
docker exec xls-gepa-work python3 /workspace/container-inspect.py
```

If the container is stopped, start this existing container with `docker start xls-gepa-work`; do not recreate it. For a fresh machine only, create a persistent container from the recorded image, bind mounting this project at `/workspace`, with `--entrypoint /bin/bash` and command `-lc 'sleep infinity'`. Never use `--rm`.

Exact creation command, only when `xls-gepa-work` does not already exist and the recorded local image is available:

```powershell
$projectDir = (Resolve-Path .).Path
docker run -d --name xls-gepa-work --mount "type=bind,source=$projectDir,target=/workspace" --entrypoint /bin/bash xls-build-docker:latest -lc 'sleep infinity'
```

For the first tool build in that container:

```powershell
docker exec xls-gepa-work python3 /workspace/container-experiment.py
```

This fixed workflow applies the recorded targeted repair, builds the seven required tools, then validates the evaluator. It does not call a model. If a `STOP_AFTER_BUILD` marker exists, validation exits without running; the marker was removed when this session resumed.

The fixed build command is in `logs/build-command.json` and `build_tools.py`. Builds use ten jobs and a 10000 MB memory budget (the initial attempt used six). Two specific CRLF failures were repaired; original files and repair provenance are preserved. No blanket line-ending conversion was performed.

## Source provenance

`reference/idct_chen.x` is the exact HLSFactory source requested by Stefan. `results/provenance.json` records its SHA256 and pinned HLSFactory/XLS commits. Its supplied `hlsfactory.toml` and upstream `PROVENANCE.json` are preserved. It implements 8x8 IDCT and contains five tests.

`setup.py` fetches the HLSFactory commit recorded for this experiment. The evaluator verifies the preserved source hash on every run.

## Fixed evaluation

`configs/evaluation.json` controls the single experiment. Baseline and all candidates use pipeline generator, one stage, `unit` delay model, registered inputs and outputs, SystemVerilog, and optimization level 3. Remaining defaults are held fixed by pinned XLS tools. The original run saved invocation and output files locally; this review branch contains the selected summary and validation artifacts.

After the build completes, run baseline and evaluator validation:

```powershell
docker exec xls-gepa-work python3 /workspace/validate_evaluator.py
```

Rerun baseline uncached:

```powershell
docker exec xls-gepa-work python3 /workspace/evaluate.py --baseline --force
```

Evaluate implementation source:

```powershell
docker exec xls-gepa-work python3 /workspace/evaluate.py /workspace/candidates/unchanged.x
```

The evaluator appends protected original tests to candidate implementations. It checks the signed DSLX top interface and lowered IR interface, runs all five tests, converts and optimizes, compares 527 deterministic inputs against original unoptimized IR, checks candidate raw-versus-optimized outputs, tries IR equivalence with a 60-second timeout, then generates RTL and estimates.

The 527 cases include uniform edge patterns, signed extrema, alternating extrema, 256 signed impulse cases across all 64 positions, and 128 cases each from JPEG-scale and full-s32 random distributions. Seed is 20260930. No real-valued Python IDCT is used as an oracle; fixed-width original XLS IR determines expected outputs.

Formal counterexamples reject candidates. Timeout/error is inconclusive, not proof. Passing sampled tests establishes tested equivalence only. Correctness failures never earn a positive score. Each tool has a 180-second timeout, with no automatic candidate retries.

Cache keys include implementation, configuration, evaluator source, reference provenance and tool binary hashes. `--force` bypasses cache. `results/evaluations.jsonl` and per-candidate `result.json` capture status, metrics, score, runtime and failure feedback.

## Metrics and objective

The fixed objective minimizes optimized IR combinational critical path under XLS's `unit` delay model. Score is `1/(1+critical_path_unit_delay)` for validated candidates, zero on rejection. The tool prints its generic delay unit as `ps`; under the unit model this is an abstract dependency-depth estimate, not measured picoseconds of a device.

The preserved `reference/xls_docs/unit.textproto` defines most operations as latency 1, with parameters, literals, ports, registers and other listed free operations at 0. It is explicitly a dummy testing model and does not account for operation bitwidth or device technology. A separate ASAP7 characterized-model critical-path estimate is collected if supported by the built tool, labeled `asap7_critical_path_estimate_ps`. This secondary estimate does not change scheduling, codegen or the fixed unit-model objective; it is not FPGA timing or placed-and-routed timing.

Optimized IR node/operation counts are recorded as resource proxies. They are not LUT counts, gate area, or measured FPGA resources. Generated RTL is not a placed-and-routed design. A shorter unit-model path need not improve physical timing. No improvement is claimed without a valid candidate beating the baseline under these fixed estimates.

Codegen's block metrics also record register bits (`flop_count` in XLS) and register-to-register unit-model delay when supplied by the pinned tool. Full operation details were saved locally in `block_metrics.textproto`; the reported summary is included here.

## Real GEPA integration

The original run used official GEPA source at the commit in `results/gepa-version.json`. The vendored checkout is retained locally but is excluded from this review branch; fetch that exact commit before rerunning. `run_gepa.py` uses the supported `gepa.optimize()` API and an XLS adapter: the sole editable component is `dslx`. Reflection receives compiler, correctness and metric feedback. GEPA chooses/proposes candidates; candidates are not manually supplied as a completed GEPA experiment.

`smoke_gepa.py` is explicitly MOCK ONLY: no real model, no XLS evaluation, no optimization result. It checks actual GEPA API invocation only.

The completed bounded experiment used `qwen2.5-coder:3b` locally through a dedicated `xls-gepa-ollama` container. `configs/model-authorization.json` fixes external spending at zero and caps the run at two model calls. No API key is used. The local model and Docker volume remain cached for reruns.

Start the preserved Ollama container if needed, then rerun the experiment with:

```bash
python3 /workspace/run_gepa.py --authorization /workspace/configs/model-authorization.json
```

From Windows, `local-model-runner.ps1` performs the image/model availability checks and launches that command. It preserves both containers and their caches. The completed run is in `results/gepa/20261001-224747/`.

Run metadata, model usage, candidate lineage, reflection prompts/responses, best source and baseline-versus-best summary are saved under `results/gepa/<run-id>/`. Provider randomness means exact regenerated candidate text may vary even with the same seed. Preserved candidates can be reevaluated deterministically.

Official sources consulted: [GEPA adapter guide](https://gepa-ai.github.io/gepa/guides/adapters/), [GEPA optimize API](https://gepa-ai.github.io/gepa/api/core/optimize/), and the XLS source at the pinned commit. This review branch includes the unit delay model file; the full XLS source and toolchain remain external dependencies.

