"""Run baseline twice, unchanged candidate, and a known-bad implementation."""
import json
from pathlib import Path
if (Path(__file__).resolve().parent/'STOP_AFTER_BUILD').exists():
    print('Evaluation paused by user; no baseline or candidate commands executed.')
    raise SystemExit(0)
from evaluate import ROOT, baseline, evaluate, split_tests, verified_reference
from evaluate import XLS

build_snapshot = ROOT/'configs/xls-build'
build_snapshot.mkdir(parents=True, exist_ok=True)
for name in ('.bazelrc', '.bazelversion', 'MODULE.bazel', 'MODULE.bazel.lock', 'bazel_downloader.cfg', 'fuzztest.bazelrc'):
    (build_snapshot/name).write_bytes((XLS/name).read_bytes())

original = verified_reference()
base, directory = baseline()
rerun, _ = baseline(force=True)
assert base['metrics'] == rerun['metrics'], 'Baseline metrics changed across rerun'
implementation, _ = split_tests(original)
(ROOT/'candidates/unchanged.x').write_text(implementation)
unchanged = evaluate(implementation, label='unchanged')
assert unchanged['correctness_status'] == 'tested_equivalent'
assert unchanged['metrics'] == base['metrics']
bad = implementation.replace('const W1 = s32:2841;', 'const W1 = s32:0;')
assert bad != implementation
(ROOT/'candidates/deliberately_incorrect.x').write_text(bad)
incorrect = evaluate(bad, label='deliberately_incorrect')
assert incorrect['correctness_status'] == 'rejected', 'Incorrect source was accepted'
assert incorrect['score'] == 0
summary = {'baseline_rerun_identical_metrics': True, 'unchanged': unchanged, 'incorrect': incorrect}
(ROOT/'results/evaluator-validation.json').write_text(json.dumps(summary, indent=2))
print(json.dumps({'baseline': base['metrics'], 'unchanged_status': unchanged['correctness_status'],
                  'incorrect_status': incorrect['correctness_status']}, indent=2))
import subprocess
subprocess.run(['python3', str(ROOT/'generate_report.py')], check=True)

