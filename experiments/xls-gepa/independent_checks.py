"""Syntax/corpus checks and actual GEPA API mock smoke; no builds/model calls."""
import ast
import subprocess
from pathlib import Path
from evaluate import ROOT, corpus, split_tests, verified_reference

for file in ROOT.glob('*.py'):
    ast.parse(file.read_text(), filename=str(file))
implementation, tests = split_tests(verified_reference())
assert tests.count('#[test]') == 5
assert '#[test]' not in implementation
cases, text = corpus()
assert len(cases) == 527
assert corpus() == (cases, text)
(ROOT/'candidates/unchanged.x').write_text(implementation)
(ROOT/'candidates/deliberately_incorrect.x').write_text(implementation.replace('const W1 = s32:2841;', 'const W1 = s32:0;'))
print('Python syntax, protected test extraction, and deterministic 527-case corpus passed.')
subprocess.run(['python3', str(ROOT/'inspect_xls.py')], check=True)
subprocess.run(['python3', str(ROOT/'smoke_gepa.py')], check=True)
subprocess.run(['python3', str(ROOT/'generate_report.py')], check=True)
from evaluate import XLS, run
converter = XLS/'bazel-bin/xls/dslx/ir_convert/ir_converter_main'
preflight = ROOT/'results/preflight'
if converter.is_file() and not (preflight/'original.ir').exists():
    preflight.mkdir(parents=True, exist_ok=True)
    ir, _, _ = run([converter, '--top=idct', '--dslx_stdlib_path='+str(XLS/'xls/dslx/stdlib'),
                    ROOT/'reference/idct_chen.x'], preflight, 'original_conversion')
    (preflight/'original.ir').write_text(ir)
    print('Original IDCT source converted successfully using the built XLS converter.')

