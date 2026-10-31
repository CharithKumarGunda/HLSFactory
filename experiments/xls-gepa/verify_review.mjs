// Check the published experiment records without running XLS or a model.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const readJson = (path) => JSON.parse(readFileSync(new URL(path, import.meta.url), 'utf8'));
const readText = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const fail = (message) => { throw new Error(message); };
const check = (condition, message) => { if (!condition) fail(message); };

const provenance = readJson('./results/provenance.json');
const source = readFileSync(new URL('./reference/idct_chen.x', import.meta.url));
const sourceHash = createHash('sha256').update(source).digest('hex');
check(sourceHash === provenance.files_sha256['idct_chen.x'], 'Pinned IDCT source hash differs from provenance');
check((source.toString('utf8').match(/#\[test\]/g) ?? []).length === 5, 'Expected five original DSLX tests');

const configuration = readJson('./configs/evaluation.json');
const summary = readJson('./results/gepa/20261001-224747/summary.json');
const validation = readJson('./results/evaluator-validation.json');
const manual = readJson('./results/manual-controls.json');
const retry = readJson('./results/gepa/20261030-175936/summary.json');
const gepaVersion = readJson('./results/gepa-version.json');
check(summary.experiment_completed === true, 'GEPA run is not recorded as complete');
check(summary.improvement_achieved === false, 'Expected no improvement from the recorded run');
check(summary.model_calls === 2, 'Expected two model calls');
check(summary.cost_estimate_usd === 0, 'Expected zero external model cost');
check(summary.gepa_version.commit === gepaVersion.commit, 'GEPA commit differs from pinned version');
check(JSON.stringify(summary.baseline.version.config) === JSON.stringify(configuration), 'Baseline configuration differs from published config');
check(summary.baseline.version.versions.files_sha256['idct_chen.x'] === sourceHash, 'Baseline used a different source hash');
check(summary.baseline.metrics.critical_path_unit_delay === 40, 'Baseline unit delay differs from report');
check(summary.best.metrics.critical_path_unit_delay === 40, 'Best unit delay differs from baseline');
check(summary.best.score === summary.baseline.score, 'Best score differs from baseline');
check(validation.baseline_rerun_identical_metrics === true, 'Baseline rerun did not match');
check(validation.unchanged.correctness_status === 'tested_equivalent', 'Unchanged candidate did not pass validation');
check(validation.incorrect.correctness_status === 'rejected' && validation.incorrect.score === 0,
      'Deliberately incorrect candidate was not rejected');
check(manual.controls.length === 2, 'Expected exactly two manual controls');
for (const control of manual.controls) {
  const recorded = readJson(`./${control.result}`);
  check(recorded.source_sha256 === control.source_sha256, `Manual control hash differs: ${control.id}`);
  check(recorded.configuration_sha256 === manual.fixed_configuration_sha256,
        `Manual control configuration differs: ${control.id}`);
  check(recorded.correctness_status === control.status, `Manual control status differs: ${control.id}`);
}
const manualPassed = manual.controls.find((control) => control.status === 'tested_equivalent');
check(manualPassed.formal_status === 'proven_equivalent' && manualPassed.differential_cases_passed === 527,
      'The manual positive control did not pass the required checks');
check(manualPassed.metrics.critical_path_unit_delay === 40 && manualPassed.metrics.asap7_critical_path_estimate_ps === 8424 &&
      manualPassed.metrics.optimized_ir_node_count === 1820 && manualPassed.metrics.block_register_bits === 4096,
      'Manual positive-control metrics differ from the report');
check(retry.experiment_completed === true && retry.model_calls <= 2 && retry.cost_estimate_usd === 0,
      'Bounded local GEPA retry did not complete within its recorded limits');
check(retry.improvement_achieved === (retry.best.correctness_status === 'tested_equivalent' &&
      retry.best.score > retry.baseline.score), 'GEPA improvement claim disagrees with the score');

const csv = readText('./results/comparison.csv').trim().split(/\r?\n/);
const columns = csv.shift().split(',');
const records = csv.map((line) => Object.fromEntries(line.split(',').map((value, index) => [columns[index], value])));
const generated = records.filter((record) => record.candidate_id.startsWith('gepa-'));
check(generated.length === 3, 'Expected three evaluated GEPA candidates across the two runs');
check(generated.every((record) => record.correctness_status === 'rejected' && Number(record.score) === 0),
      'A GEPA candidate result differs from the reported rejection');
check(records.some((record) => record.candidate_id.startsWith('baseline-') &&
      Number(record.critical_path_unit_delay) === 40), 'Baseline comparison row is missing');
check(records.some((record) => record.candidate_id === manualPassed.id &&
      record.correctness_status === 'tested_equivalent'), 'Manual positive control is missing from comparison.csv');
check(records.some((record) => record.candidate_id === 'gepa-4390dca833c8' &&
      record.correctness_status === 'rejected'), 'Retry candidate is missing from comparison.csv');
const retryLog = readText('./results/gepa/20261030-175936/run_log.txt');
check(retryLog.includes('timed out') && retryLog.includes('did not propose a new candidate'),
      'Second retry request timeout is not documented in run log');

console.log('Review artifacts agree: pinned source, five tests, evaluator controls, manual result, and bounded GEPA runs.');
console.log('This checks saved records only; it does not rerun XLS or prove hardware performance.');

