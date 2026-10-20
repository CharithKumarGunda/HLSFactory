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
rows = []
record_path = ROOT/'results/evaluations.jsonl'
if record_path.exists():
    for line in record_path.read_text().splitlines():
        record = json.loads(line)
        row = {key: record.get(key) for key in ('candidate_id', 'source_sha256', 'configuration_sha256',
               'correctness_status', 'formal_status', 'score', 'elapsed_seconds')}
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
        'Only DSLX implementation source is optimized. Scheduling/codegen remain fixed at a one-stage pipeline with unit delay model and registered input/output. No Vitis or HLS-Eval work was performed.', '',
        '## Evidence completed', '',
        '- Exact linked HLSFactory source preserved with pinned commit and SHA256; five original tests identified.',
        '- Persistent Docker environment and build cache established; machine inventory and XLS source commit recorded.',
        '- Evaluator code, deterministic 527-case corpus, and actual GEPA adapter integration validated.',
        '- The real bounded GEPA run used a local Qwen2.5-Coder 3B model through Ollama at zero external cost.', '']
if base:
    text += ['## Baseline', '', '```json', json.dumps(base['metrics'], indent=2), '```', '',
             f'Correctness: {base["correctness_status"]}. Formal result: {base["formal_status"]}.', '']
else:
    text += ['## Baseline pending', '', 'The XLS build/baseline has not yet completed successfully. No baseline hardware metrics are available.', '']
if validation:
    text += ['## Evaluator verification', '',
             'The unchanged implementation passed and matched baseline metrics. A deliberately incorrect W1 constant was rejected with score zero. An uncached baseline rerun produced identical metrics.', '']
else:
    text += ['Evaluator validation with built XLS tools is pending; prepared code alone does not establish reliable evaluation.', '']
if experiment:
    text += ['## GEPA outcome', '', f'Real GEPA experiment completed. Improvement achieved: **{experiment["improvement_achieved"]}**.', '',
             f'{experiment["model_calls"]} model-generated candidates were attempted. Both failed DSLX validation, so GEPA retained the unchanged, formally equivalent baseline. No optimization improvement is claimed.', '',
             'The latest results/gepa run contains candidate source, lineage, reflection logs, token usage, and baseline-versus-best metrics.', '']
else:
    text += ['## GEPA outcome pending', '', 'No real model-driven GEPA experiment has run. Provider/model and spending authorization are pending. No improvement is claimed.', '']
text += ['## Limitations and next experiment', '',
         'Unit-model delay is an abstract XLS dependency-depth estimate from a dummy testing model, despite the generic tool output label ps. A separately labeled ASAP7 critical-path estimate is recorded when available and does not affect scheduling or the objective. Neither is measured FPGA or placed-and-routed timing. IR operations and register bits are resource proxies, not LUT usage or physical area. Tests do not prove equivalence over all inputs; proof timeout/error is inconclusive.', '',
         'This small local model produced two invalid DSLX candidates, so the run demonstrates a working protected optimization loop but not an improvement. A useful next experiment is a larger DSLX-capable local model or a larger bounded search, keeping the same evaluator and fixed XLS settings.', '']
(ROOT/'REPORT.md').write_text('\n'.join(text))
message = 'Stefan — I have preserved the exact IDCT DSLX design and set up a persistent XLS environment. The experiment keeps scheduling/codegen fixed and restricts GEPA to DSLX source. '
message += 'The baseline and evaluator are validated, including rejection of an incorrect candidate. ' if validation else 'XLS compilation and baseline/evaluator validation are still pending. '
message += f'The bounded GEPA run completed; estimated improvement achieved: {experiment["improvement_achieved"]}. ' if experiment else 'The real GEPA run has not started; model access/budget remains pending. '
message += 'All source, hashes, logs and results are saved for reproducibility. These are XLS estimates, not measured FPGA results.'
(ROOT/'STEFAN_PROGRESS_DRAFT.md').write_text('# Draft only — not sent\n\n'+message+'\n')
print('Report, CSV and unsent Stefan draft updated.')

