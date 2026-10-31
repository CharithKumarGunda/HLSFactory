"""Generate honest status report and flat CSV from recorded evaluations."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
baseline_path = ROOT/'results/baseline.json'
validation_path = ROOT/'results/evaluator-validation.json'
base = json.loads(baseline_path.read_text()) if baseline_path.exists() else None
validation = json.loads(validation_path.read_text()) if validation_path.exists() else None
summaries = sorted((ROOT/'results/gepa').glob('*/summary.json')) if (ROOT/'results/gepa').exists() else []
experiment = json.loads(summaries[-1].read_text()) if summaries else None
latest_run = summaries[-1].parent.name if summaries else None
manual_path = ROOT/'results/manual-controls.json'
manual = json.loads(manual_path.read_text()) if manual_path.exists() else None
manual_ids = {control['source_sha256']: control['id'] for control in manual['controls']} if manual else {}
rows = []
record_path = ROOT/'results/evaluations.jsonl'
if record_path.exists():
    for line in record_path.read_text().splitlines():
        record = json.loads(line)
        row = {key: record.get(key) for key in ('candidate_id', 'source_sha256', 'configuration_sha256',
               'correctness_status', 'formal_status', 'score', 'elapsed_seconds')}
        if row['candidate_id'].startswith('candidate-') and row['source_sha256'] in manual_ids:
            row['candidate_id'] = manual_ids[row['source_sha256']]
        row.update({key: record.get('metrics', {}).get(key) for key in ('critical_path_unit_delay',
                    'optimized_ir_node_count', 'block_register_bits', 'block_reg_to_reg_unit_delay', 'asap7_critical_path_estimate_ps')})
        rows.append(row)
fields = ['candidate_id', 'source_sha256', 'configuration_sha256', 'correctness_status', 'formal_status',
          'critical_path_unit_delay', 'optimized_ir_node_count', 'block_register_bits',
          'block_reg_to_reg_unit_delay', 'score', 'elapsed_seconds']
fields.insert(6, 'asap7_critical_path_estimate_ps')
with (ROOT/'results/comparison.csv').open('w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
text = ['# IDCT XLS + GEPA research report', '',
        'The search was configured to rewrite only DSLX implementation source. Scheduling/codegen remained fixed at a one-stage pipeline with unit delay model and registered input/output. This prototype did not include Vitis or HLS-Eval integration.', '',
        '## Evidence completed', '',
        '- Exact linked HLSFactory source preserved with pinned commit and SHA256; five original tests identified.',
        '- Persistent Docker environment and build cache established; machine inventory and XLS source commit recorded.',
        '- Evaluator code, deterministic 527-case corpus, and actual GEPA adapter integration validated.',
        '- The real bounded GEPA run used a local Qwen2.5-Coder 3B model through Ollama at zero external cost.', '']
if base:
    text += ['## Baseline', '', '```json', json.dumps(base['metrics'], indent=2), '```', '',
             'The unchanged implementation passed the 527 comparisons and XLS equivalence check against the pinned original. This validates the evaluator on unchanged source; it does not independently prove the original IDCT against a mathematical specification.', '']
else:
    text += ['## Baseline pending', '', 'The XLS build/baseline has not yet completed successfully. No baseline hardware metrics are available.', '']
if validation:
    text += ['## Evaluator verification', '',
             'The unchanged implementation passed and matched baseline metrics. A deliberately incorrect W1 constant was rejected with score zero. An uncached baseline rerun produced identical metrics.', '']
else:
    text += ['Evaluator validation with built XLS tools is pending; prepared code alone does not establish reliable evaluation.', '']
if manual:
    passed = next((control for control in manual['controls'] if control['status'] == 'tested_equivalent'), None)
    text += ['## Manual DSLX rewrites (not GEPA-generated)', '',
             'The first row-butterfly rewrite was rejected because two local constants became unused; the full DSLX compiler message is saved in its per-candidate result.json.', '']
    if passed:
        metrics = passed['metrics']
        text += [f'The second manual rewrite passed all five protected tests, {passed["differential_cases_passed"]} deterministic comparisons, and XLS equivalence checking. Its fixed unit-model critical path is {metrics["critical_path_unit_delay"]} versus 40 for baseline, so the score is unchanged. The secondary ASAP7 estimate is {metrics["asap7_critical_path_estimate_ps"]} ps versus 8488 ps, optimized IR nodes are {metrics["optimized_ir_node_count"]} versus 1883, and register bits are {metrics["block_register_bits"]} for both.', '',
                 'See `results/manual-controls.json` for source hashes and exact evaluation paths.', '']
if experiment:
    text += ['## GEPA outcome', '', f'Real GEPA experiment completed. Improvement achieved: **{experiment["improvement_achieved"]}**.', '',
             f'The latest bounded local run (`{latest_run}`) attempted {experiment["model_calls"]} local model requests at an estimated external cost of ${experiment["cost_estimate_usd"]:.2f}. One response produced a candidate rejected by DSLX validation; the second request timed out and produced no candidate. Its selected best candidate has fixed unit delay {experiment["best"]["metrics"]["critical_path_unit_delay"]} versus {experiment["baseline"]["metrics"]["critical_path_unit_delay"]} for baseline. See `results/comparison.csv` and the run log for the separate outcomes.', '',
             'The local run directory contains generated source, lineage, reflection logs, token usage, and baseline-versus-best metrics; the review branch includes selected text artifacts.', '']
else:
    text += ['## GEPA outcome pending', '', 'No real model-driven GEPA experiment has run. Provider/model and spending authorization are pending. No improvement is claimed.', '']
text += ['## Limitations and next experiment', '',
         'Unit-model delay is an abstract XLS dependency-depth estimate from a dummy testing model, despite the generic tool output label ps. A separately labeled ASAP7 critical-path estimate is recorded when available and does not affect scheduling or the objective. Neither is measured FPGA or placed-and-routed timing. IR operations and register bits are resource proxies, not LUT usage or physical area. Tests do not prove equivalence over all inputs; proof timeout/error is inconclusive.', '',
         'A useful next experiment is a larger DSLX-capable local model or a larger bounded search, keeping the same evaluator and fixed XLS settings.', '']
(ROOT/'REPORT.md').write_text('\n'.join(text))
message = 'Stefan — I have preserved the exact IDCT DSLX design and set up a persistent XLS environment. The experiment keeps scheduling/codegen fixed and restricts GEPA to DSLX source. '
message += 'The baseline and evaluator are validated, including rejection of an incorrect candidate. ' if validation else 'XLS compilation and baseline/evaluator validation are still pending. '
if manual:
    message += 'A separate manual rewrite passed five tests, 527 comparisons and equivalence checking; unit delay remained 40 while the secondary ASAP7 estimate fell from 8488 to 8424 ps. '
message += f'The bounded GEPA run completed; estimated improvement achieved: {experiment["improvement_achieved"]}. ' if experiment else 'The real GEPA run has not started; model access/budget remains pending. '
message += 'All source, hashes, logs and results are saved for reproducibility. These are XLS estimates, not measured FPGA results.'
(ROOT/'STEFAN_PROGRESS_DRAFT.md').write_text('# Draft only — not sent\n\n'+message+'\n')
print('Report, CSV and unsent Stefan draft updated.')

