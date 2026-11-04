"""MOCK ONLY: Verify pinned GEPA API plumbing without XLS or a model call."""
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root/'vendor/gepa/src'))
import gepa
from gepa.core.adapter import EvaluationBatch

class MockAdapter:
    propose_new_texts = None

    def evaluate(self, batch, candidate, capture_traces=False):
        values = [{'mock': True, 'text': candidate['dslx']} for _ in batch]
        return EvaluationBatch(outputs=values, scores=[0.1 for _ in batch],
                               trajectories=values if capture_traces else None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        return {'dslx': [{'Feedback': 'MOCK feedback; no hardware evaluation'}]}

calls = []
def mock_reflector(prompt):
    calls.append(prompt)
    return '```dslx\npub fn mock(x: u32) -> u32 { x }\n```'

result = gepa.optimize(seed_candidate={'dslx': 'MOCK seed'}, trainset=[0], valset=[0],
                       adapter=MockAdapter(), reflection_lm=mock_reflector,
                       reflection_minibatch_size=1, max_metric_calls=4, skip_perfect_score=False,
                       display_progress_bar=False, use_merge=False, seed=20260930)
assert calls, 'GEPA did not invoke mock reflection'
(root/'results/gepa-mock-smoke.json').write_text(json.dumps({'mock': True,
    'xls_evaluated': False, 'real_model_calls': 0, 'reflection_calls': len(calls),
    'result': result.to_dict()}, indent=2))
print('MOCK API smoke passed. No XLS evaluation, no real model calls, no optimization claim.')

