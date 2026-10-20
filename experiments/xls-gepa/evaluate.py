"""Bounded, cached XLS evaluator. Only candidate implementation text is editable."""
import argparse
from collections import Counter
import hashlib
from functools import lru_cache
import json
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parent
XLS = Path('/home/xls-developer/xls')
CONFIG = json.loads((ROOT/'configs/evaluation.json').read_text())
REFERENCE = ROOT/'reference/idct_chen.x'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def split_tests(source):
    """Extract complete test functions; ignore braces inside comments/strings."""
    masked = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                    lambda m: ' ' * len(m.group()), source, flags=re.S)
    spans = []
    for match in re.finditer(r'#\[test\]\s*fn\s+\w+\s*\(', masked):
        start = masked.index('{', match.end())
        depth = 1
        end = start + 1
        while depth:
            if masked[end] == '{':
                depth += 1
            elif masked[end] == '}':
                depth -= 1
            end += 1
        spans.append((match.start(), end))
    implementation = source
    for start, end in reversed(spans):
        implementation = implementation[:start]+implementation[end:]
    tests = '\n\n'.join(source[start:end] for start, end in spans)
    return implementation, tests

def verified_reference():
    data = REFERENCE.read_bytes()
    expected = json.loads((ROOT/'results/provenance.json').read_text())['files_sha256']['idct_chen.x']
    if digest(data) != expected:
        raise RuntimeError('Protected reference source hash mismatch')
    return data.decode()

class CommandFailure(Exception):
    pass

def run(command, directory, label, timeout=None, required=True):
    command = [str(arg) for arg in command]
    start = time.monotonic()
    process = subprocess.Popen(command, cwd=XLS, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout or CONFIG['command_timeout_seconds'])
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    record = {'command': command, 'returncode': process.returncode, 'timeout': timed_out,
              'elapsed_seconds': time.monotonic()-start}
    (directory/f'{label}.stdout').write_bytes(stdout)
    (directory/f'{label}.stderr').write_bytes(stderr)
    (directory/f'{label}.command.json').write_text(json.dumps(record, indent=2))
    if required and (timed_out or process.returncode):
        raise CommandFailure(f'{label}: '+('timeout' if timed_out else stderr.decode(errors='replace')[-5000:]))
    return stdout.decode(errors='replace'), stderr.decode(errors='replace'), record

def tool(name):
    paths = {'interpreter': 'xls/dslx/interpreter_main',
             'convert': 'xls/dslx/ir_convert/ir_converter_main',
             'opt': 'xls/tools/opt_main', 'codegen': 'xls/tools/codegen_main',
             'eval': 'xls/tools/eval_ir_main', 'delay': 'xls/tools/delay_info_main',
             'formal': 'xls/dev_tools/check_ir_equivalence_main'}
    result = XLS/'bazel-bin'/paths[name]
    if not result.exists():
        raise RuntimeError(f'Missing built XLS tool: {result}')
    return result

def corpus():
    cases = []
    edges = [0, 1, -1, 127, -128, 1023, -1024, 32767, -32768,
             2147483647, -2147483648, 0x40000000, -0x40000000]
    for value in edges:
        cases.append([value]*64)
    cases.append([edges[i % len(edges)] for i in range(64)])
    cases.append([2147483647 if i%2 else -2147483648 for i in range(64)])
    for index in range(64):
        for value in (1, -1, 2147483647, -2147483648):
            values = [0]*64
            values[index] = value
            cases.append(values)
    rng = random.Random(CONFIG['random_seed'])
    for low, high in [(-1024, 1023), (-2147483648, 2147483647)]:
        for _ in range(CONFIG['random_cases_per_distribution']):
            cases.append([rng.randint(low, high) for _ in range(64)])
    text = '\n'.join('['+', '.join(f'bits[32]:0x{x & 0xffffffff:08x}' for x in case)+']' for case in cases)+'\n'
    return cases, text

def compile_source(path, directory):
    stdlib = XLS/'xls/dslx/stdlib'
    raw, _, _ = run([tool('convert'), '--top=idct', '--dslx_stdlib_path='+str(stdlib), path], directory, 'convert')
    raw_path = directory/'raw.ir'
    raw_path.write_text(raw)
    header = re.search(r'top fn (\w+)\((.*?)\) -> ([^\{]+)\{', raw, re.S)
    if not header:
        raise CommandFailure('No top function in converted IR')
    parameters = re.sub(r'\s+', '', re.sub(r'\bid=\d+\b', '', header[2]))
    if not re.fullmatch(r'\w+:bits\[32\]\[64\]', parameters) or re.sub(r'\s+', '', header[3]) != 'bits[32][64]':
        raise CommandFailure('Expected one bits[32][64] argument and bits[32][64] result; got '+header[0])
    optimized, _, _ = run([tool('opt'), '--opt_level='+str(CONFIG['opt_level']), '--delay_model='+CONFIG['delay_model'], raw_path], directory, 'opt')
    opt_path = directory/'optimized.ir'
    opt_path.write_text(optimized)
    return raw_path, opt_path

def outputs(text):
    return [line.strip() for line in text.splitlines() if line.strip().startswith('[')]

@lru_cache(maxsize=1)
def identity():
    # Include evaluator, fixed configuration, source versions and tool bytes in cache identity.
    versions = json.loads((ROOT/'results/provenance.json').read_text())
    hashes = {name: digest(tool(name).read_bytes()) for name in ('interpreter', 'convert', 'opt', 'codegen', 'eval', 'delay', 'formal')}
    value = {'config': CONFIG, 'versions': versions, 'tools_sha256': hashes,
             'evaluator_sha256': digest(Path(__file__).read_bytes())}
    return value, digest(json.dumps(value, sort_keys=True).encode())

def baseline(force=False):
    source = verified_reference()
    version, config_hash = identity()
    directory = ROOT/'results'/('baseline-'+config_hash[:16])
    directory.mkdir(parents=True, exist_ok=True)
    result_file = directory/'result.json'
    if result_file.exists() and not force:
        return json.loads(result_file.read_text()), directory
    cases, inputs = corpus()
    (directory/'inputs.txt').write_text(inputs)
    (directory/'corpus.json').write_text(json.dumps({'seed': CONFIG['random_seed'], 'cases': cases}))
    result = evaluate(source, label='baseline', baseline_dir=directory, force=True, is_baseline=True)
    if result['correctness_status'] != 'tested_equivalent':
        raise RuntimeError('Baseline evaluation failed: '+result['feedback'])
    (ROOT/'results/baseline.json').write_text(json.dumps(result, indent=2))
    return result, directory

def evaluate(source, label='candidate', baseline_dir=None, force=False, is_baseline=False):
    start = time.monotonic()
    original = verified_reference()
    implementation, protected_tests = split_tests(original)
    try:
        candidate_impl, candidate_tests = split_tests(source)
    except (IndexError, ValueError):
        candidate_impl, candidate_tests = source, ''
    version, config_hash = identity()
    if not is_baseline and baseline_dir is None:
        _, baseline_dir = baseline()
    source_hash = digest(candidate_impl.encode())
    directory = baseline_dir if is_baseline else ROOT/'results/evaluations'/f'{source_hash}-{config_hash[:16]}'
    directory.mkdir(parents=True, exist_ok=True)
    result_file = directory/'result.json'
    if result_file.exists() and not force:
        return json.loads(result_file.read_text())
    result = {'candidate_id': label+'-'+source_hash[:12], 'source_sha256': source_hash,
              'configuration_sha256': config_hash, 'correctness_status': 'not_checked',
              'formal_status': 'not_run', 'metrics': {}, 'score': 0.0, 'version': version,
              'artifact_directory': str(directory), 'is_baseline': is_baseline}
    candidate_path = directory/'candidate.x'
    candidate_path.write_text(candidate_impl)
    tests_path = directory/'protected_tests.x'
    tests_path.write_text(candidate_impl+'\n\n'+protected_tests)
    try:
        # Prevent replacement of the top's signed DSLX interface as well as the lowered IR interface.
        normalized = re.sub(r'//[^\n]*|/\*.*?\*/', '', candidate_impl, flags=re.S)
        signature = re.search(r'\bfn\s+idct\s*\((.*?)\)\s*->\s*([^\{]+)', normalized, re.S)
        if not signature or not re.search(r'\bpub\s+fn\s+idct\b', normalized) or re.sub(r'\s+', '', signature[1]) != 'f:s32[COEFF_PER_MCU]' or re.sub(r'\s+', '', signature[2]) != 's32[COEFF_PER_MCU]':
            raise CommandFailure('Preserve exact DSLX top signature: fn idct(f: s32[COEFF_PER_MCU]) -> s32[COEFF_PER_MCU]')
        if re.search(r'#\[|\b(import|proc)\b', normalized):
            raise CommandFailure('Only DSLX function implementation and constants may be supplied; no attributes, imports, or procs')
        if is_baseline:
            run([tool('interpreter'), '--dslx_stdlib_path='+str(XLS/'xls/dslx/stdlib'), REFERENCE],
                directory, 'original_tests')
        run([tool('interpreter'), '--dslx_stdlib_path='+str(XLS/'xls/dslx/stdlib'), tests_path], directory, 'unit_tests')
        raw, optimized = compile_source(candidate_path, directory)
        cases, inputs = corpus()
        input_path = baseline_dir/'inputs.txt'
        expected_path = baseline_dir/'expected.txt'
        raw_out, _, _ = run([tool('eval'), '--use_llvm_jit=false', '--input_file='+str(input_path), raw], directory, 'eval_raw')
        actual = outputs(raw_out)
        if len(actual) != len(cases):
            raise CommandFailure(f'Expected {len(cases)} outputs, received {len(actual)}')
        if is_baseline:
            expected_path.write_text('\n'.join(actual)+'\n')
        else:
            expected = expected_path.read_text().splitlines()
            for index, (want, got) in enumerate(zip(expected, actual)):
                if want != got:
                    result['counterexample'] = {'case_index': index, 'input': cases[index], 'expected': want, 'actual': got}
                    raise CommandFailure(f'Differential mismatch at case {index}: expected {want}, got {got}')
            if len(actual) != len(expected):
                raise CommandFailure('Differential output count mismatch')
        opt_out, _, _ = run([tool('eval'), '--use_llvm_jit=false', '--input_file='+str(input_path), optimized], directory, 'eval_optimized')
        if outputs(opt_out) != actual:
            raise CommandFailure('Optimization changed tested outputs')
        result['correctness_status'] = 'tested_equivalent'
        result['test_cases'] = len(cases)
        stdout, stderr, formal = run([tool('formal'), baseline_dir/'raw.ir', raw], directory, 'formal',
                                     timeout=CONFIG['formal_timeout_seconds'], required=False)
        if formal['timeout']:
            result['formal_status'] = 'inconclusive_timeout'
        elif formal['returncode'] == 0 and 'verified equivalent' in stdout.lower():
            result['formal_status'] = 'proven_equivalent'
        elif 'verified not equivalent' in (stdout+stderr).lower() or 'counterexample' in (stdout+stderr).lower():
            result['formal_status'] = 'proven_not_equivalent'
            raise CommandFailure('Formal checker found counterexample: '+(stdout+stderr)[-5000:])
        else:
            result['formal_status'] = 'inconclusive_error'
        command = [tool('codegen'), '--generator='+CONFIG['generator'],
                   '--pipeline_stages='+str(CONFIG['pipeline_stages']), '--delay_model='+CONFIG['delay_model'],
                   '--flop_inputs=true', '--flop_outputs=true', '--use_system_verilog=true',
                   '--module_name='+CONFIG['module_name'], '--output_verilog_path='+str(directory/'design.sv'),
                   '--output_schedule_path='+str(directory/'schedule.textproto'),
                   '--output_signature_path='+str(directory/'signature.textproto'),
                   '--block_metrics_path='+str(directory/'block_metrics.textproto'),
                   '--output_block_ir_path='+str(directory/'block.ir'), optimized]
        run(command, directory, 'codegen')
        delay_text, _, _ = run([tool('delay'), '--delay_model='+CONFIG['delay_model'], optimized], directory, 'delay')
        section = delay_text.split('# Critical path:')[-1].split('\n\n')[0]
        delays = [int(x) for x in re.findall(r'^\s*(\d+)ps\s+\(', section, re.M)]
        if not delays:
            raise CommandFailure('Could not parse critical-path estimate; inspect delay.stdout')
        ir = optimized.read_text()
        operations = Counter(re.findall(r'^\s*(?:ret\s+)?\S+:.*?=\s*(\w+)\(', ir, re.M))
        critical = max(delays)
        result['metrics'] = {'critical_path_unit_delay': critical,
                             'optimized_ir_node_count': sum(operations.values()),
                             'optimized_ir_operation_counts': dict(sorted(operations.items()))}
        # Secondary estimate does not affect fixed unit-model scheduling or scoring.
        secondary_text, secondary_error, secondary = run(
            [tool('delay'), '--delay_model='+CONFIG['secondary_delay_model'], optimized],
            directory, 'delay_asap7', required=False)
        if secondary['returncode'] == 0 and not secondary['timeout']:
            secondary_section = secondary_text.split('# Critical path:')[-1].split('\n\n')[0]
            secondary_delays = [int(x) for x in re.findall(r'^\s*(\d+)ps\s+\(', secondary_section, re.M)]
            if secondary_delays:
                result['metrics']['asap7_critical_path_estimate_ps'] = max(secondary_delays)
        else:
            result['secondary_estimate_status'] = 'unavailable: '+secondary_error[-1000:]
        block_metrics = (directory/'block_metrics.textproto').read_text()
        for field, key in [('flop_count', 'block_register_bits'),
                           ('max_reg_to_reg_delay_ps', 'block_reg_to_reg_unit_delay'),
                           ('max_input_to_reg_delay_ps', 'block_input_to_reg_unit_delay'),
                           ('max_reg_to_output_delay_ps', 'block_reg_to_output_unit_delay')]:
            match = re.search(r'^\s*'+field+r':\s*(\d+)', block_metrics, re.M)
            if match:
                result['metrics'][key] = int(match[1])
        result['score'] = 1.0/(1.0+critical)
        result['feedback'] = f'Passed five protected tests and {len(cases)} edge/random cases. Formal: {result["formal_status"]}. Unit-model critical path: {critical}. IR operation counts: {dict(operations)}. Lower critical path is the fixed objective; preserve full s32 overflow, signed shifts, and rounding.'
    except CommandFailure as error:
        result['correctness_status'] = 'rejected'
        result['feedback'] = str(error)
        result['score'] = 0.0
    result['elapsed_seconds'] = time.monotonic()-start
    result_file.write_text(json.dumps(result, indent=2))
    with (ROOT/'results/evaluations.jsonl').open('a') as stream:
        stream.write(json.dumps(result)+'\n')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', nargs='?')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.baseline:
        result, _ = baseline(force=args.force)
    elif args.source:
        result = evaluate(Path(args.source).read_text(), force=args.force)
    else:
        parser.error('Specify source or --baseline')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['correctness_status'] == 'tested_equivalent' else 1)

