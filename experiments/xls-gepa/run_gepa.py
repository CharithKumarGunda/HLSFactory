"""Real GEPA source-artifact optimization; model calls require explicit config."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

from evaluate import ROOT, baseline, evaluate, split_tests, verified_reference

# Use preserved official source without changing the XLS Python environment.
sys.path.insert(0, str(ROOT/'vendor/gepa/src'))
import gepa
from gepa.core.adapter import EvaluationBatch
from gepa.utils.stop_condition import TimeoutStopCondition

PROMPT = '''You are optimizing the DSLX implementation of an 8x8 fixed-point IDCT for XLS.
The ONLY editable artifact is this DSLX implementation:
```dslx
<curr_param>
```
Evaluation feedback:
<side_info>
Rewrite the entire DSLX implementation and return it in exactly one fenced dslx code block.
Keep pub fn idct(f: s32[COEFF_PER_MCU]) -> s32[COEFF_PER_MCU], with COEFF_PER_MCU=64.
Preserve helper signatures used by protected tests. No tests, imports, procs, or attributes.
Preserve exact 32-bit signed arithmetic including modular overflow, arithmetic shifts,
rounding constants, and all input bit patterns. Mathematical real-valued equivalence is insufficient.
Scheduling, codegen, optimizer, unit delay model, correctness corpus, and scoring are fixed.
Minimize the optimized XLS IR unit-model critical path. Score is 1/(1+critical path).
Compiler errors or correctness mismatches score zero. Formal counterexamples reject.
Formal timeout is inconclusive; a tested candidate is not automatically formally proven.
Consider reducing dependency depth, constant multiplication structure, or redundant operations.
Do not change evaluators, settings, expected values, or scoring. Do not invent metric improvements.
'''

class XLSAdapter:
    propose_new_texts = None

    def evaluate(self, batch, candidate, capture_traces=False):
        result = evaluate(candidate['dslx'], label='gepa')
        return EvaluationBatch(outputs=[result for _ in batch], scores=[result['score'] for _ in batch],
                               trajectories=[result for _ in batch] if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        return {'dslx': [{'Inputs': 'Full protected IDCT correctness suite and fixed XLS settings',
                          'Generated Outputs': record.get('metrics', {}),
                          'Feedback': record['feedback']} for record in eval_batch.outputs]}

class BudgetedReflection:
    """Conservative reservation before each call; no automatic retries."""
    def __init__(self, config, directory):
        self.config = config
        self.directory = directory
        self.calls = 0
        self.reserved_usd = 0.0
        self.total_cost = 0.0

    def __call__(self, prompt):
        serialized = prompt if isinstance(prompt, str) else json.dumps(prompt)
        # UTF-8 byte count plus overhead is deliberately a loose input-token upper bound.
        input_bound = len(serialized.encode()) + 2048
        output_bound = self.config['max_output_tokens']
        reservation = (input_bound*self.config['input_usd_per_million'] +
                       output_bound*self.config['output_usd_per_million'])/1e6
        if self.calls >= self.config['max_model_calls'] or self.reserved_usd+reservation > self.config['spending_limit_usd']:
            raise RuntimeError('Model call refused: conservative approved budget/call limit exhausted')
        self.calls += 1
        self.reserved_usd += reservation  # Retain reservation on errors; never retry automatically.
        messages = [{'role': 'user', 'content': prompt}] if isinstance(prompt, str) else prompt
        (self.directory/f'reflection-{self.calls:03d}-prompt.json').write_text(json.dumps(messages, indent=2))
        if self.config.get('provider') == 'ollama':
            payload = json.dumps({'model': self.config['model'], 'messages': messages, 'stream': False,
                                  'options': {'num_predict': output_bound, 'temperature': 0.7}}).encode()
            request = urllib.request.Request(self.config.get('api_base', 'http://host.docker.internal:11434') + '/api/chat',
                                             data=payload, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=self.config.get('request_timeout_seconds', 900)) as response:
                raw = json.loads(response.read())
            content = raw.get('message', {}).get('content')
            finish_reason = raw.get('done_reason')
            usage = {'prompt_tokens': raw.get('prompt_eval_count', 0),
                     'completion_tokens': raw.get('eval_count', 0)}
        else:
            import litellm
            response = litellm.completion(model=self.config['model'], messages=messages,
                                          max_tokens=output_bound, timeout=120, num_retries=0)
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            usage = response.usage.model_dump() if response.usage is not None else {}
        if not content or finish_reason == 'length':
            raise RuntimeError('Empty or truncated model response; candidate not evaluated')
        (self.directory/f'reflection-{self.calls:03d}-response.txt').write_text(content)
        actual = (usage.get('prompt_tokens', input_bound)*self.config['input_usd_per_million'] +
                  usage.get('completion_tokens', output_bound)*self.config['output_usd_per_million'])/1e6
        self.total_cost += actual
        (self.directory/'model-usage.json').write_text(json.dumps({'calls': self.calls,
             'reserved_upper_bound_usd': self.reserved_usd, 'estimated_actual_usd': self.total_cost,
             'last_usage': usage, 'config': self.config}, indent=2))
        return content

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorization', required=True, help='Approved model and budget JSON; never secrets')
    args = parser.parse_args()
    config = json.loads(Path(args.authorization).read_text())
    local_free = config.get('provider') == 'ollama' and config.get('local_zero_cost') is True
    if config.get('authorized') is not True or (config.get('spending_limit_usd', 0) <= 0 and not local_free):
        raise SystemExit('Explicit model and spending authorization required')
    for key in ('model', 'input_usd_per_million', 'output_usd_per_million', 'max_output_tokens', 'max_model_calls'):
        if key not in config:
            raise SystemExit('Missing authorized model configuration: '+key)
    validation = ROOT/'results/evaluator-validation.json'
    if not validation.exists():
        raise SystemExit('Run evaluator validation before GEPA')
    base, _ = baseline()
    run_dir = ROOT/'results/gepa'/time.strftime('%Y%m%d-%H%M%S', time.gmtime())
    run_dir.mkdir(parents=True)
    (run_dir/'authorization.json').write_text(json.dumps(config, indent=2))
    source, _ = split_tests(verified_reference())
    reflector = BudgetedReflection(config, run_dir)
    result = gepa.optimize(seed_candidate={'dslx': source}, trainset=[{'benchmark': 'idct_chen'}],
                           valset=[{'benchmark': 'idct_chen'}], adapter=XLSAdapter(),
                           reflection_lm=reflector, reflection_prompt_template=PROMPT,
                           reflection_minibatch_size=1, max_metric_calls=12,
                           stop_callbacks=[TimeoutStopCondition(1800), lambda state: reflector.calls >= config['max_model_calls']],
                           skip_perfect_score=False, use_merge=False, seed=20260930,
                           run_dir=str(run_dir), cache_evaluation=False, display_progress_bar=False,
                           raise_on_exception=True)
    (run_dir/'gepa-result.json').write_text(json.dumps(result.to_dict(), indent=2))
    best = evaluate(result.best_candidate['dslx'], label='gepa-best')
    (run_dir/'best.x').write_text(result.best_candidate['dslx'])
    improved = best['correctness_status'] == 'tested_equivalent' and best['score'] > base['score']
    summary = {'experiment_completed': True, 'improvement_achieved': improved, 'baseline': base,
               'best': best, 'model_calls': reflector.calls, 'cost_estimate_usd': reflector.total_cost,
               'gepa_version': json.loads((ROOT/'results/gepa-version.json').read_text())}
    (run_dir/'summary.json').write_text(json.dumps(summary, indent=2))
    import subprocess
    subprocess.run(['python3', str(ROOT/'generate_report.py')], check=True)
    print(json.dumps({'run_dir': str(run_dir), 'improvement_achieved': improved,
                      'baseline_metrics': base['metrics'], 'best_metrics': best['metrics']}, indent=2))

if __name__ == '__main__':
    main()

